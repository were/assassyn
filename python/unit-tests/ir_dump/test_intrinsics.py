"""Tests for intrinsic IR nodes: Intrinsic, PureIntrinsic."""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from assassyn.frontend import (
    Module, SysBuilder, UInt, Port, log, module,
    wait_until, finish, assume
)
from assassyn.test import dump_ir


def test_intrinsics_dump():
    """Test intrinsic operations IR dump logging."""
    def builder(sys):
        class IntrinsicsTestModule(Module):
            def __init__(self):
                super().__init__(ports={
                    'cond': Port(UInt(1))
                })
            
            @module.combinational
            def build(self):
                cond = self.cond.pop()
                
                # Test intrinsic operations
                wait_result = wait_until(cond)
                finish_result = finish()
                assert_result = assume(cond)
                
                log("Intrinsics test")
        
        IntrinsicsTestModule().build()
    
    def checker(sys_repr):
        # Verify intrinsics appear
        assert "intrinsic.wait_until" in sys_repr
        assert "intrinsic.finish" in sys_repr
        assert "intrinsic.assert" in sys_repr
    
    dump_ir("intrinsics_test", builder, checker)


if __name__ == '__main__':
    test_intrinsics_dump()
    print("\n=== Intrinsics Tests Completed Successfully ===")
