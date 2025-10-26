# DONE: Metadata-based Push/Call Tracking

## Goal Achieved

Successfully moved collection of FIFOPush and AsyncCall expressions from expression walking during top-level harness generation to metadata collection during expression generation, following the established pattern used for FINISH intrinsics.

## Action Items Completed

- [x] Add pushes and calls fields to PostDesignGeneration dataclass in metadata.py
- [x] Update codegen_async_call in _expr/call.py to append calls to module metadata
- [x] Update codegen_fifo_push in _expr/array.py to append pushes to module metadata
- [x] Replace expression walking in top.py line 384-385 with metadata lookup
- [x] Replace expression walking in design.py line 304-305 with metadata lookup
- [x] Remove unused AsyncCall import from top.py
- [x] Run python/ci-tests/test_driver.py as sanity check
- [x] Stage and commit all changes following git-message.md standard
- [x] Create dones/DONE-metadata-push-call-tracking.md with summary

## Changes Made

### Improvements

1. **Enhanced metadata.py**: Added `pushes` and `calls` fields to `PostDesignGeneration` dataclass with proper typing using TYPE_CHECKING to avoid circular imports

2. **Modified expression handlers**: Updated `codegen_async_call` in `_expr/call.py` and `codegen_fifo_push` in `_expr/array.py` to collect expressions in module metadata during generation

3. **Optimized top.py**: Replaced redundant expression walking at line 384-385 with O(1) metadata lookup, eliminating `_walk_expressions` calls on module bodies

4. **Optimized design.py**: Replaced redundant expression walking at line 304-305 with O(1) metadata lookup for module port generation

5. **Cleanup**: Removed unused `AsyncCall` import from top.py

## Technical Decisions

1. **Consistent metadata pattern**: This refactoring follows the exact same pattern as `has_finish` metadata collection, ensuring architectural consistency and maintainability

2. **TYPE_CHECKING import**: Used `from typing import TYPE_CHECKING` to avoid circular imports since we import AsyncCall and FIFOPush types in the dataclass field annotations

3. **Safety checks**: Added null checks (`if dumper.current_module`) in expression handlers to gracefully handle edge cases where current_module might not be set

4. **Default values**: Used `field(default_factory=list)` for the new fields to ensure each module gets its own list instance

5. **Performance improvement**: Changed from O(n) expression walking to O(1) metadata lookup, where n is the number of expressions in the module body

## Further Improvements

The metadata structure is now extensible for future module properties:
- `has_wait_until: bool` - Modules containing WAIT_UNTIL intrinsics  
- `array_usage: List[Array]` - Which arrays are accessed by the module
- `external_dependencies: List[ExternalSV]` - External modules used
- `port_counts: Dict[str, int]` - Number of input/output ports for optimization
