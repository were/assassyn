"""Call operation code generation for Verilog.

This module contains functions to generate Verilog code for call operations,
including AsyncCall and Bind.
"""

from typing import Optional

from ....ir.expr import AsyncCall
from ....ir.expr.call import Bind


def codegen_async_call(dumper, expr: AsyncCall) -> Optional[str]:
    """Generate code for async call operations."""
    dumper.expose('trigger', expr)
    # Track calls in module metadata to avoid redundant expression walking
    dumper.module_metadata[dumper.current_module].calls.append(expr)


def codegen_bind(_dumper, _expr: Bind) -> Optional[str]:
    """Generate code for bind operations.

    Bind operations don't generate any code, they just represent bindings.
    """
