from pathlib import Path

import pytest

from assassyn.frontend import *  # type: ignore
from assassyn.test import run_test  # type: ignore
from assassyn.codegen.verilog.design import generate_design  # type: ignore


def _emit_design(sys_builder: SysBuilder, tmp_path: Path) -> str:
    """Generate design.py for the provided system and return its contents."""

    out_dir = tmp_path / "select1hot"
    out_dir.mkdir(parents=True, exist_ok=True)
    design_path = out_dir / "design.py"
    generate_design(str(design_path), sys_builder)
    return design_path.read_text(encoding="utf-8")

class Driver(Module):

    def __init__(self):
            super().__init__(ports={},no_arbiter=True,)


    @module.combinational
    def build(self):
        cond = RegArray(Int(5), 1, initializer=[0])
        values = RegArray(Int(32), 5, initializer = [1, 2, 4, 8, 16])

        gt = Int(5)(1) << cond[0]
        mux = gt.select1hot(values[0], values[1], values[2], values[3], values[4])

        log("onehot select 0b{:b} from [1,2,4,8,16]: {}", gt, mux)
        (cond & self)[0] <= (cond[0] + Int(5)(1)) % Int(5)(5)

def top():
    driver = Driver()
    driver.build()

def check(raw: str):
    for i in raw.splitlines():
        if 'onehot select' in i:
            a = i.split()[-4]
            b = i.split()[-1]
            assert int(a, 2) == int(b)

def test_select1hot():
    run_test('select1hot', top, check)


def test_select1hot_two_value_case_emits_assignment(tmp_path):
    sys_builder = SysBuilder("select1hot_assign")

    with sys_builder:

        class Harness(Module):  # type: ignore[misc]

            def __init__(self):
                super().__init__(
                    ports={
                        "sink": Port(UInt(8)),
                    },
                    no_arbiter=True,
                )

            @module.combinational
            def build(self):
                cond = UInt(2)(1)
                v0 = UInt(8)(3)
                v1 = UInt(8)(7)
                result = cond.select1hot(v0, v1)
                self.sink.push(result)

        Harness().build()

    text = _emit_design(sys_builder, tmp_path)
    select_lines = [
        line.strip()
        for line in text.splitlines()
        if "select1hot" in line or "Mux(" in line
    ]

    assert any(" = " in line for line in select_lines), (
        "expected select1hot helper to assign to destination; "
        f"captured lines: {select_lines}"
    )

if __name__ == '__main__':
    test_select1hot()
