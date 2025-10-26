"""Test that FIFO pop readiness is driven by metadata, not expression walking."""

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from assassyn.frontend import Module, SysBuilder, UInt, Port, module
from assassyn.codegen.verilog.design import generate_design


def test_fifo_pop_metadata_top_and_module_ports(tmp_path):
    sysb = SysBuilder("fifo_pop_md")
    with sysb:
        class Popper(Module):
            def __init__(self):
                super().__init__(ports={
                    'in0': Port(UInt(8)),
                })

            @module.combinational
            def build(self):
                _ = self.in0.pop()

        Popper().build()

    out_dir = tmp_path / "gen"
    os.makedirs(out_dir, exist_ok=True)
    design_path = out_dir / "design.py"
    generate_design(str(design_path), sysb)

    text = design_path.read_text(encoding="utf-8")

    # Module should declare pop_ready for in0
    assert "in0_pop_ready = Output(Bits(1))" in text

    # Top should wire fifo_<Mod>_in0_pop_ready to inst_<Mod>.in0_pop_ready
    import re
    assert re.search(r"fifo_\w+_in0_pop_ready\.assign\(inst_\w+\.in0_pop_ready\)", text)


