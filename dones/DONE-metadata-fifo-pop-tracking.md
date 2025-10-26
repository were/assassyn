# DONE: Metadata-based FIFOPop Tracking and Top/Module Refactor

## Goal Achieved
- Use `module_metadata.pops` to detect FIFO pops instead of expression walking.

## Action Items Completed
- [x] Update docs: `metadata.md`, `top.md`, `module.md` to document `pops`.
- [x] Add `pops` field to `PostDesignGeneration` and collect in `codegen_fifo_pop`.
- [x] Refactor `module.py` to emit `<port>_pop_ready` using `pops`.
- [x] Refactor `top.py` wiring for `*_pop_ready` using `pops`.
- [x] Add unit test `python/unit-tests/codegen/test_fifo_pop_metadata.py`.
- [x] Run `python/ci-tests/test_driver.py` sanity check.

## Changes Made
- `python/assassyn/codegen/verilog/metadata.py`: Add `PopList` typing and `pops` field.
- `python/assassyn/codegen/verilog/_expr/array.py`: Append to `module_metadata[...].pops` in `codegen_fifo_pop`.
- `python/assassyn/codegen/verilog/design.py`: Pass `pops` to `generate_module_ports`.
- `python/assassyn/codegen/verilog/module.py`: Compute pop presence from `pops` (removed expression walking and `FIFOPop` import).
- `python/assassyn/codegen/verilog/top.py`: Use `metadata.pops` to wire `fifo_<mod>_<port>_pop_ready`.
- Docs updated accordingly.

## Representative Before/After
Before (module ports):
```python
has_pop = any(isinstance(e, FIFOPop) and e.fifo == i for e in dumper._walk_expressions(node.body))
```
After:
```python
popped_fifos = {p.fifo for p in pops}
has_pop = i in popped_fifos
```

Before (top wiring):
```python
if any(isinstance(e, FIFOPop) and e.fifo == port for e in dumper._walk_expressions(module.body)):
    # connect pop_ready
```
After:
```python
popped_fifos = {p.fifo for p in (metadata.pops if metadata else [])}
if port in popped_fifos:
    # connect pop_ready
```

## Test and CI Notes
- New unit test validates presence of module `in0_pop_ready` and top-level wiring via regex.
- `python/ci-tests/test_driver.py` passed; full `make test-all` not run here due to sandbox.

## Technical Decisions
- Mirror existing metadata pattern for pushes/calls to keep O(1) lookups and consistency.
- Keep low invasion: no broader refactors, only replaced expression walks tied to `FIFOPop` detection.

## Further Suggestions
- Consider recording `array_reads` metadata similarly to avoid IR walks in `system.py` for array read port mapping.
- Add a focused integration test ensuring `*_pop_ready` gating interacts correctly with TriggerCounter in complex graphs.
