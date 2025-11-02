"""Ensure external exposure bookkeeping retains raw predicate metadata."""

from collections import defaultdict
from types import SimpleNamespace

from assassyn.codegen.verilog._expr.intrinsics import codegen_external_intrinsic
from assassyn.ir.const import Const
from assassyn.ir.dtype import Bits, UInt
from assassyn.ir.expr.intrinsic import ExternalIntrinsic
from assassyn.ir.module.external import ExternalSV, WireSpec


class ModuleStub:
    """Hashable module surrogate for dumper bookkeeping."""

    def __init__(self, name: str):
        self.name = name

    def __hash__(self) -> int:  # pragma: no cover - trivial helper
        return hash(self.name)

    def __eq__(self, other):  # pragma: no cover - trivial helper
        if not isinstance(other, ModuleStub):
            return NotImplemented
        return self.name == other.name


class _StubRegistry:
    """Minimal registry exposing reads recorded for an external instance."""

    def __init__(self, mapping):
        self._mapping = mapping
        self.frozen = True

    def reads_for_instance(self, instance):
        """Return the stored reads for *instance*."""
        return self._mapping.get(instance, ())


class _StubDumper:
    """Provide the subset of CIRCTDumper used by codegen_external_intrinsic."""

    def __init__(self, registry, current_module):
        self.external_metadata = registry
        self.current_module = current_module
        self.external_wrapper_names = {}
        self.external_instance_names = {}
        self.external_wire_outputs = {}
        self.external_output_exposures = defaultdict(dict)

    def dump_rval(self, node, _with_namespace, module_name=None):
        """Return a deterministic binding name for *node*."""
        if hasattr(node, "as_operand"):
            return node.as_operand()
        return repr(node)

    def get_external_wire_key(self, instance, port_name, index_operand):
        """Match CIRCTDumper's wire-key normalisation for index-less ports."""
        idx_key = None
        if index_operand is not None:
            idx_key = ("expr", index_operand)
        return (instance, port_name, idx_key)

    def get_pred(self, expr):
        """Legacy helper retained so the pre-refactor path still executes."""
        del expr  # unused
        return "Bits(1)(1)"


class DummyExternal(ExternalSV):  # type: ignore[misc]
    """Simple external module used for predicate propagation tests."""


DummyExternal.set_metadata({
    "source": "dummy.sv",
    "module_name": "DummyExternal",
})
DummyExternal.set_port_specs(
    {
        "value": WireSpec(
            name="value",
            dtype=UInt(8),
            direction="out",
            kind="wire",
        ),
    }
)


def test_external_intrinsic_tracks_raw_meta_cond():
    """External exposures should retain the original Expr.meta_cond value."""

    producer = ModuleStub("producer")
    consumer = ModuleStub("consumer")

    instance = ExternalIntrinsic(DummyExternal)
    instance.parent = producer

    predicate = Const(Bits(1), 1)
    instance._meta_cond = predicate  # pylint: disable=protected-access

    read_expr = SimpleNamespace(dtype=UInt(8))
    registry = _StubRegistry({
        instance: (
            SimpleNamespace(
                expr=read_expr,
                producer=producer,
                consumer=consumer,
                instance=instance,
                port_name="value",
                index_operand=None,
            ),
        )
    })

    dumper = _StubDumper(registry, consumer)

    result = codegen_external_intrinsic(dumper, instance)
    assert "DummyExternal_ffi" in result

    exposures = dumper.external_output_exposures[consumer]
    assert exposures, "External outputs should be registered for the consumer module"
    data = next(iter(exposures.values()))

    assert data["meta_cond"] is predicate
    assert "condition" not in data
