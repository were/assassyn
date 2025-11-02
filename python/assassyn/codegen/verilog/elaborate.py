# pylint: disable=too-many-locals
"""Elaborate Assassyn IR to Verilog."""

from __future__ import annotations

import os
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from textwrap import dedent
from typing import Iterable, Sequence

from .design import generate_design
from .testbench import TestbenchTemplateConfig, generate_testbench
from .utils import extract_sram_params
from ...builder import SysBuilder
from ...ir.memory.sram import SRAM
from ...utils import create_dir, repo_path
from ...utils.enforce_type import enforce_type
from ..simulator.external import collect_external_intrinsics


@dataclass(frozen=True)
class AliasResource:
    """Alias module emitted by CIRCT that should mirror a core helper."""

    source: str
    alias: str


@dataclass(frozen=True)
class CopyAction:
    """Concrete file copy to be materialised."""

    source: Path
    destination: Path

    def ensure_parent(self) -> None:
        """Ensure the destination directory exists before copying."""
        self.destination.parent.mkdir(parents=True, exist_ok=True)


@dataclass
class ResourceCopyPlan:
    """Deterministic plan describing the resources to materialise."""

    destination: Path
    core_helpers: Sequence[str] = field(default_factory=tuple)
    alias_resources: Sequence[AliasResource] = field(default_factory=tuple)
    external_sources: Sequence[Path] = field(default_factory=tuple)

    def core_actions(self, resource_root: Path) -> Iterable[CopyAction]:
        """Yield copy actions for built-in helper files."""
        for helper in self.core_helpers:
            yield CopyAction(resource_root / helper, self.destination / helper)

    def alias_actions(self, resource_root: Path) -> Iterable[tuple[AliasResource, CopyAction]]:
        """Yield alias copy actions paired with their metadata."""
        for alias in self.alias_resources:
            source = resource_root / alias.source
            destination = self.destination / f"{alias.alias}.sv"
            yield alias, CopyAction(source, destination)

    def external_actions(self) -> Iterable[CopyAction]:
        """Yield copy actions for external SystemVerilog sources."""
        for src_path in self.external_sources:
            yield CopyAction(src_path, self.destination / src_path.name)


CORE_HELPERS: tuple[str, ...] = ("fifo.sv", "trigger_counter.sv")


@enforce_type
def _collect_external_sources(sys: SysBuilder) -> set[Path]:
    """Gather SystemVerilog source files referenced by external intrinsics."""
    sources: set[Path] = set()
    repo_root = Path(repo_path())
    for intrinsic in collect_external_intrinsics(sys):
        source = intrinsic.external_class.metadata().get('source')
        if source:
            src_path = Path(source)
            if not src_path.is_absolute():
                src_path = repo_root / source
            sources.add(src_path)
    return sources


@enforce_type
def _resolve_alias_resources(
    top_sv_path: Path,
    files_to_copy: Sequence[str],
) -> list[AliasResource]:
    """Infer CIRCT-generated aliases that need duplicate resource files."""
    if not top_sv_path.exists():
        return []

    alias_resource_files: list[AliasResource] = []
    top_content = top_sv_path.read_text(encoding='utf-8')
    for resource_file in files_to_copy:
        base_module = Path(resource_file).stem
        pattern = rf"\b{base_module}_(\d+)\b"
        matches = sorted(set(re.findall(pattern, top_content)))
        for suffix in matches:
            alias_module = f"{base_module}_{suffix}"
            alias_resource_files.append(AliasResource(resource_file, alias_module))
    return alias_resource_files


@enforce_type
def _prepare_resource_plan(
    output_dir: Path,
    sys: SysBuilder,
    log_lines: Sequence[str],
    sim_threshold: int,
) -> tuple[ResourceCopyPlan, TestbenchTemplateConfig]:
    """Build the resource copy plan and matching testbench configuration."""

    external_sources = tuple(sorted(
        _collect_external_sources(sys),
        key=lambda path_entry: path_entry.as_posix(),
    ))

    top_sv_path = output_dir / "sv" / "hw" / "Top.sv"
    alias_resources = _resolve_alias_resources(top_sv_path, CORE_HELPERS)

    additional_files = sorted({
        *(src.name for src in external_sources),
        *(f"{alias.alias}.sv" for alias in alias_resources),
    })

    copy_plan = ResourceCopyPlan(
        destination=output_dir,
        core_helpers=CORE_HELPERS,
        alias_resources=alias_resources,
        external_sources=external_sources,
    )

    testbench_config = TestbenchTemplateConfig(
        sim_threshold=sim_threshold,
        log_lines=log_lines,
        extra_sources=additional_files,
    )

    return copy_plan, testbench_config


def _copy_core_resources(resource_root: Path, plan: ResourceCopyPlan) -> None:
    """Copy standard SV helper files used by the testbench."""
    for action in plan.core_actions(resource_root):
        if not action.source.is_file():
            print(f"Warning: Resource file not found: {action.source}")
            continue
        action.ensure_parent()
        shutil.copy(action.source, action.destination)


def _copy_alias_resources(resource_root: Path, plan: ResourceCopyPlan) -> None:
    """Materialize alias modules emitted by CIRCT to keep resource names in sync."""
    for alias, action in plan.alias_actions(resource_root):
        if action.destination.exists():
            continue
        if not action.source.is_file():
            print(f"Warning: Cannot create alias for missing resource: {action.source}")
            continue

        content = action.source.read_text(encoding='utf-8')
        base_module = Path(alias.source).stem
        alias_content = content.replace(f"module {base_module}", f"module {alias.alias}", 1)
        action.ensure_parent()
        action.destination.write_text(alias_content, encoding='utf-8')
        print(f"Copied {action.source} to {action.destination}")


def _copy_external_sources(plan: ResourceCopyPlan) -> None:
    """Copy user-provided SystemVerilog sources into the elaboration output."""
    for action in plan.external_actions():
        if not action.source.is_file():
            print(f"Warning: External resource file not found: {action.source}")
            continue
        action.ensure_parent()
        shutil.copy(action.source, action.destination)
        print(f"Copied {action.source} to {action.destination}")


@enforce_type
def generate_sram_blackbox_files(
    sys: SysBuilder,
    path: Path,
    resource_base: str | Path | None = None,
) -> None:
    """Generate separate Verilog files for SRAM memory blackboxes."""

    output_dir = Path(path)
    output_dir.mkdir(parents=True, exist_ok=True)
    init_root = Path(resource_base) if resource_base is not None else None

    sram_modules = sorted(
        (module for module in sys.downstreams if isinstance(module, SRAM)),
        key=lambda module: module.name,
    )

    for sram in sram_modules:
        params = extract_sram_params(sram)
        sram_info = params.info
        array_name = params.array_name
        data_width = params.data_width
        addr_width = params.addr_width

        init_file = sram_info.init_file
        init_path = None
        if init_file:
            init_path = Path(init_file)
            if init_root is not None and not init_path.is_absolute():
                init_path = init_root / init_path

        header = dedent(
            f"""
            `ifdef SYNTHESIS
            (* blackbox *)
            `endif
            module sram_blackbox_{array_name} #(
                parameter DATA_WIDTH = {data_width},
                parameter ADDR_WIDTH = {addr_width}
            )(
                input clk,
                input [ADDR_WIDTH-1:0] address,
                input [DATA_WIDTH-1:0] wd,
                input banksel,
                input read,
                input write,
                output reg [DATA_WIDTH-1:0] dataout,
                input rst_n
            );

                localparam DEPTH = 1 << ADDR_WIDTH;
                reg [DATA_WIDTH-1:0] mem [DEPTH-1:0];
            """
        ).strip()

        body_lines = [header]
        if init_path is not None:
            body_lines.append(
                dedent(
                    f"""
                        initial begin
                            $readmemh("{init_path.as_posix()}", mem);
                        end

                        always @ (posedge clk) begin
                    """
                ).rstrip()
            )
        else:
            body_lines.append(
                dedent(
                    """
                        always @ (posedge clk) begin
                            if (!rst_n) begin
                                mem[address] <= {DATA_WIDTH{1'b0}};
                            end
                    """
                ).rstrip()
            )

        body_lines.append(
            dedent(
                """
                            if (write & banksel) begin
                                mem[address] <= wd;
                            end
                        end

                        assign dataout = (read & banksel) ? mem[address] : {DATA_WIDTH{1'b0}};

                    endmodule
                """
            ).strip()
        )

        blackbox_source = "\n".join(body_lines) + "\n"
        output_path = output_dir / f"sram_blackbox_{array_name}.sv"
        output_path.write_text(blackbox_source, encoding="utf-8")


def elaborate(sys: SysBuilder, **kwargs) -> str:  # pylint: disable=too-many-locals,too-many-branches
    """Elaborate the system into Verilog.

    Args:
        sys: The system to elaborate
        **kwargs: Configuration options including:
            - verilog: The simulator to use ("Verilator", "VCS", or None)
            - resource_base: Path to resources
            - override_dump: Whether to override existing files
            - sim_threshold: Simulation threshold
            - idle_threshold: Idle threshold
            - random: Whether to randomize execution
            - fifo_depth: Default FIFO depth

    Returns:
        Path to the generated Verilog files
    """

    path = kwargs.get('path', os.getcwd())
    path = Path(path) / "verilog"

    create_dir(path)

    logs = generate_design(path / "design.py", sys)

    copy_plan, testbench_config = _prepare_resource_plan(
        path,
        sys,
        logs,
        kwargs['sim_threshold'],
    )
    generate_testbench(path / "tb.py", testbench_config)

    default_home = Path(os.getenv('ASSASSYN_HOME', os.getcwd()))
    resource_path = default_home / "python/assassyn/codegen/verilog"
    generate_sram_blackbox_files(sys, path, kwargs.get('resource_base'))
    _copy_core_resources(resource_path, copy_plan)
    _copy_alias_resources(resource_path, copy_plan)
    _copy_external_sources(copy_plan)

    return path
