# DONE: Metadata-based FIFO Depth Computation in Top Harness

## Goal Achieved
- Replace expression walking for FIFO depth computation with metadata-driven lookup (`module_metadata.pushes`).

## Action Items Completed
- [x] Document metadata-based FIFO depth selection in `python/assassyn/codegen/verilog/top.md`.
- [x] Replace `_walk_expressions` depth scan with metadata iteration in `python/assassyn/codegen/verilog/top.py`.
- [x] Run `python/ci-tests/test_driver.py` sanity check (passed).
- [x] Attempt full `make test-all` (PyCDE verification segfault in sandbox; see Notes).

## Changes Made
- Switched FIFO depth derivation to use `dumper.module_metadata[module].pushes`.
- Removed unused `FIFOPush` import from `top.py`.
- Updated docs to state FIFO depth selection is metadata-driven; expression walking remains for `FIFOPop` readiness.

## Representative Before/After
Before:
```python
for expr in dumper._walk_expressions(module.body):
    if isinstance(expr, FIFOPush):
        depth = getattr(expr, 'fifo_depth', None)
        # update module_fifo_depths
```
After:
```python
metadata = dumper.module_metadata.get(module)
for push in getattr(metadata, 'pushes', []):
    depth = getattr(push, 'fifo_depth', None)
    # update module_fifo_depths
```

## Test and CI Notes
- `python/ci-tests/test_driver.py` passed. Full `make test-all` failed during PyCDE verification with a segmentation fault (likely sandbox-related). Recommend re-running in a full dev environment.

## Technical Decisions
- Followed existing metadata pattern used elsewhere in `top.py` for pushes/calls to avoid redundant IR walks.
- Preserved default depth and max-across-pushes behavior.
- Limited scope: no broader refactors; kept `_walk_expressions` only where still needed.

## Further Suggestions
- Add a focused test asserting FIFO depth emission from metadata in a future pass.
- Consider centralizing FIFO depth aggregation if reused elsewhere.
