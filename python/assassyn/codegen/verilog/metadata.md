# Verilog Code Generation Metadata

This module provides metadata structures for tracking information collected during Verilog code generation that needs to be referenced in later compilation phases.

## Summary

The metadata module defines dataclasses that hold information about modules discovered during the code generation pass. This metadata is populated incrementally as expressions are processed and later consumed during top-level harness generation, eliminating the need for redundant analysis passes.

## Exposed Interfaces

### `PostDesignGeneration`

```python
@dataclass
class PostDesignGeneration:
    """Metadata collected during module code generation."""
```

**Explanation**

This dataclass holds information about a module that is discovered during the code generation pass and needs to be referenced later (e.g., during top-level harness generation). It provides a type-safe, extensible way to track module properties without requiring additional traversals of the IR.

**Fields:**

- `has_finish: bool = False` - Indicates whether the module contains a FINISH intrinsic. This is set to `True` when `codegen_intrinsic` encounters a FINISH operation, allowing top-level generation to determine which modules need their finish signals collected without walking the module body again.
- `pushes: List[FIFOPush]` - List of FIFOPush expressions found in this module. This list is populated by `codegen_fifo_push` when processing FIFO push operations during expression generation, avoiding redundant expression walking during top-level harness generation.
- `calls: List[AsyncCall]` - List of AsyncCall expressions found in this module. This list is populated by `codegen_async_call` when processing async call operations during expression generation, avoiding redundant expression walking during module port generation and top-level harness generation.
- `pops: List[FIFOPop]` - List of FIFOPop expressions found in this module. This list is populated by `codegen_fifo_pop` when processing FIFO pop operations during expression generation, allowing both module and top-level generators to determine where `*_pop_ready` handshakes are required without walking the IR.

**When Metadata is Populated:**

1. **Initialization**: An empty `PostDesignGeneration` instance is created for each module at the start of `visit_module` in [design.py](/python/assassyn/codegen/verilog/design.md)
2. **Population**: Metadata fields are populated during expression generation:
   - The `has_finish` flag is set to `True` in [intrinsics.py](/python/assassyn/codegen/verilog/_expr/intrinsics.md) when a FINISH intrinsic is encountered
   - The `pushes` list is populated in [array.py](/python/assassyn/codegen/verilog/_expr/array.md) when processing FIFOPush operations
   - The `calls` list is populated in [call.py](/python/assassyn/codegen/verilog/_expr/call.md) when processing AsyncCall operations
   - The `pops` list is populated in [array.py](/python/assassyn/codegen/verilog/_expr/array.md) when processing FIFOPop operations

**How Metadata is Consumed:**

The metadata is stored in `CIRCTDumper.module_metadata`, a dictionary mapping `Module` objects to their `PostDesignGeneration` metadata. This metadata is consumed in multiple places:

- **Top-level harness generation** ([top.py](/python/assassyn/codegen/verilog/top.md)): Uses `pushes` and `calls` lists to determine module interconnections without walking module bodies again
- **Module port generation** ([design.py](/python/assassyn/codegen/verilog/design.md)): Uses `pushes`, `calls`, and `pops` during module generation to determine required ports, including whether to emit `<port>_pop_ready` outputs
- **Global finish signal collection**: Uses `has_finish` flag to determine which modules need finish signals collected
- **Performance Benefit**: Eliminates redundant expression walking, converting O(n) traversals into O(1) metadata lookups

**Future Extensions:**

The `PostDesignGeneration` structure can be extended to track additional module properties:

- `has_wait_until: bool` - Modules containing WAIT_UNTIL intrinsics
- `has_async_calls: bool` - Modules that make asynchronous calls
- `array_usage: List[Array]` - Which arrays are accessed by the module
- `external_dependencies: List[ExternalSV]` - External modules used
- `port_counts: Dict[str, int]` - Number of input/output ports for optimization

**Project-specific Knowledge Required:**

- Understanding of [CIRCTDumper state management](/python/assassyn/codegen/verilog/design.md)
- Knowledge of [intrinsic code generation](/python/assassyn/codegen/verilog/_expr/intrinsics.md)
- Reference to [top-level harness generation](/python/assassyn/codegen/verilog/top.md)
- Understanding of [visitor pattern](/python/assassyn/ir/visitor.md)

## Design Rationale

**Why Track at Intrinsic Detection Point:**

By setting metadata flags immediately when intrinsics are encountered (rather than in a post-processing pass), we ensure the metadata is always consistent with the generated code. This approach leverages the existing visitor pattern without adding new traversal logic.

**Why Initialize in visit_module:**

Creating an empty metadata entry for each module at the start of `visit_module` ensures that:

1. All modules have metadata entries, even if they contain no special intrinsics
2. No null checks are needed when setting flags in expression handlers
3. The metadata lifetime matches the module processing lifetime

**Why Use Dataclass:**

Dataclasses provide:

- Type safety with clear field definitions
- Easy extensibility for future metadata fields
- Readable initialization with default values
- Integration with Python's type checking tools

