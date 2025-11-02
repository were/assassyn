
"""Testbench generation for Verilog simulation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence, Union
from textwrap import dedent

from ...utils.enforce_type import enforce_type


@dataclass(frozen=True)
class TestbenchTemplateConfig:
    """Structured parameters required to render the Cocotb testbench."""

    sim_threshold: int
    log_lines: Sequence[str]
    extra_sources: Sequence[str]
    output_dir: Union[str, Path] = Path("./sv/hw")


TEMPLATE = dedent(
    """
    import os
    import glob
    from pathlib import Path

    import cocotb
    from cocotb.triggers import Timer
    from cocotb.runner import get_runner


    @cocotb.test()
    async def test_tb(dut):

        dut.clk.value = 1
        dut.rst.value = 1
        await Timer(500, units="ns")
        dut.clk.value = 0
        dut.rst.value = 0
        await Timer(500, units="ns")
        for cycle in range({threshold}):
            dut.clk.value = 1
            await Timer(500, units="ns")
            dut.clk.value = 0
            await Timer(500, units="ns")
            {log_block}
            if dut.global_finish.value == 1:
                break


    def runner():
        sim = 'verilator'
        path = Path('{output_dir}')
        with open(path / 'filelist.f', 'r') as f:
            srcs = [path / i.strip() for i in f.readlines()]
        sram_blackbox_files = glob.glob('sram_blackbox_*.sv')
        srcs = srcs + sram_blackbox_files
        srcs = srcs + ['fifo.sv', 'trigger_counter.sv'{extras}]
        runner = get_runner(sim)
        runner.build(sources=srcs, hdl_toplevel='Top', always=True)
        runner.test(hdl_toplevel='Top', test_module='tb')


    if __name__ == "__main__":
        runner()
    """
).strip()


@enforce_type
def generate_testbench(fname: Union[str, Path], config: TestbenchTemplateConfig) -> None:
    """Generate a testbench file for the given system."""

    log_block = "\n        ".join(config.log_lines)
    extra_sources = "".join(f", '{name}'" for name in config.extra_sources)
    output_dir = Path(config.output_dir)

    rendered = TEMPLATE.format(
        threshold=config.sim_threshold,
        log_block=log_block,
        extras=extra_sources,
        output_dir=output_dir.as_posix(),
    )

    Path(fname).write_text(rendered + "\n", encoding="utf-8")
