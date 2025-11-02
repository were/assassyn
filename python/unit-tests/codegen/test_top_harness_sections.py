"""Unit coverage for the refactored top-level harness helpers."""

from types import SimpleNamespace

import pytest

from assassyn.codegen.verilog.top import (  # type: ignore
    TopHarnessBuilder,
    _declare_fifo_wires,
    _emit_sram_blackboxes,
    _emit_trigger_counters,
)


def _make_builder() -> TopHarnessBuilder:
    builder = TopHarnessBuilder()
    builder.line("# preamble")
    return builder


def test_emit_sram_blackboxes_declares_wires():
    dumper = SimpleNamespace(
        memory_defs={(16, 8, "tensor")},
        sys=SimpleNamespace(downstreams=[SimpleNamespace(name="tensor_mem")]),
    )

    builder = _make_builder()
    _emit_sram_blackboxes(dumper, builder)
    lines = builder.render()

    assert any("mem_tensor_dataout = Wire(Bits(16))" in line for line in lines)
    assert any("sramBlackbox_tensor()" in line for line in lines)


def test_declare_fifo_wires_is_deterministic():
    port_a = SimpleNamespace(name="outA", dtype=SimpleNamespace(bits=8))
    port_b = SimpleNamespace(name="outB", dtype=SimpleNamespace(bits=16))
    module = SimpleNamespace(name="Producer", ports=[port_b, port_a])
    dumper = SimpleNamespace(sys=SimpleNamespace(modules=[module]))

    builder = _make_builder()
    _declare_fifo_wires(dumper, builder)
    lines = [line.strip() for line in builder.render() if "fifo_producer_" in line.lower()]

    assert lines[0].startswith("fifo_Producer_outA_push_valid")
    assert lines[1].startswith("fifo_Producer_outA_push_data")
    assert any("fifo_Producer_outB_push_valid" in line for line in lines)


def test_emit_trigger_counters_wires_trigger_counter_bundle():
    module = SimpleNamespace(name="Producer")
    dumper = SimpleNamespace(sys=SimpleNamespace(modules=[module]))

    builder = _make_builder()
    _emit_trigger_counters(dumper, builder)
    block = "\n".join(builder.render())

    assert "Producer_trigger_counter_inst = TriggerCounter" in block
    assert "Producer_trigger_counter_delta_ready.assign" in block
    assert "Producer_trigger_counter_pop_valid.assign" in block
