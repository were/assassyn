"""Metadata structures for tracking information during Verilog code generation.

This module provides dataclasses to hold metadata collected during the code generation
pass that needs to be referenced in later compilation phases (e.g., during top-level
harness generation).
"""

from dataclasses import dataclass


@dataclass
class PostDesignGeneration:
    """Metadata collected during module code generation.
    
    This class holds information about a module that is discovered during the code
    generation pass and needs to be referenced later (e.g., during top-level harness
    generation).
    
    Attributes:
        has_finish: Whether the module contains a FINISH intrinsic. This flag is
            set to True when codegen_intrinsic encounters a FINISH operation, allowing
            top-level generation to determine which modules need their finish signals
            collected without walking the module body again.
    """
    has_finish: bool = False
    # Future extensions:
    # has_wait_until: bool = False
    # has_async_calls: bool = False
    # array_usage: Optional[List[Array]] = None
