"""Shared predicate utilities for the Verilog backend."""

from __future__ import annotations

from typing import Callable, Sequence, Tuple, TypeVar

from ...utils import enforce_type

__all__ = ["emit_predicate_mux_chain", "reduce_predicates"]

T = TypeVar("T")


@enforce_type
def reduce_predicates(
    predicates: Sequence[str],
    *,
    default_literal: str | None,
    op: str = "or_",
) -> str:
    """Format a reduction expression with configurable operator and default literal."""

    if not predicates:
        if default_literal is None:
            raise ValueError("Cannot build predicate reduction without a default literal")
        return default_literal

    if default_literal is None and len(predicates) == 1:
        return predicates[0]

    joined = ", ".join(predicates)
    if default_literal is None:
        return f"reduce({op}, [{joined}])"

    return f"reduce({op}, [{joined}], {default_literal})"


@enforce_type
def emit_predicate_mux_chain(
    entries: Sequence[T],
    *,
    render_predicate: Callable[[T], str],
    render_value: Callable[[T], str],
    default_value: str,
    aggregate_predicates: Callable[[Sequence[str]], str],
) -> Tuple[str, str]:
    """Return both the mux chain and aggregate predicate for *entries*."""

    predicate_terms = [render_predicate(entry) for entry in entries]
    aggregate_expr = aggregate_predicates(predicate_terms)

    if not entries:
        return default_value, aggregate_expr

    value_terms = [render_value(entry) for entry in entries]

    if len(value_terms) == 1:
        return value_terms[0], aggregate_expr

    mux_expr = default_value
    for predicate_expr, value_expr in zip(predicate_terms, value_terms):
        mux_expr = f"Mux({predicate_expr}, {mux_expr}, {value_expr})"

    return mux_expr, aggregate_expr
