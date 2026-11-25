# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0
# Credits: Opus and Astra.
# Source-derived alternative segmentation for paper counter only.
import paired_arithmetic as _pa
from paired_arithmetic import *
_inputs=_pa._inputs
_terminal_partition=_pa._terminal_partition
_segment_repay=_pa._segment_repay
_phase_borrow=_pa._phase_borrow
def inverse_add_optimized_paper(builder, source, target, debt: CarryDebt, *, carry_in=False,
                signed_source=False, carry_budget=None, dirty_wires=(),
                carry_lifecycle=None, overflow_phase=None,
                allow_dirty_overflow=False):
    """Undo the matching forward add and repay every recorded carry phase.

    If overflow_phase is a classical bit, additionally phase the final
    borrow carry by (-1)**overflow_phase.  The supported multi-bit case has
    two literal high source zeros.  Its final borrow is a three-bit product
    already exposed at the ordinary two-bit terminal, so one conditioned
    CCZ suffices without an additional clean wire.  This optional mode
    excludes dirty terminal fallbacks by default.  The optional
    allow_dirty_overflow mode compares exact sparse terminals too, paying
    their final product phase with an independently proved dirty-MCZ echo.
    """
    a, b, preserve = _inputs(source, target, carry_in, signed_source)
    n = len(b)
    if overflow_phase is not None and (signed_source or
            (n>=2 and (a[-2] is not False or a[-1] is not False))):
        raise ValueError('Overflow-phase inverse needs an unsigned source with two high zeros.')
    if debt.width != n:
        raise ValueError("This carry debt belongs to a different adder width.")
    if debt.consumed:
        raise ValueError("This forward adder's phase debt has already been consumed.")
    debt.consumed = True
    if not n:
        return
    available = builder.max_qubits-builder.num_allocated_qubits
    desired = max(0, n-2) if carry_budget is None else carry_budget
    clean = int(min(available, desired, max(0, n-2)))
    terminal_dirty = None
    if carry_lifecycle is not None:
        if signed_source or not isinstance(carry_in,km.q):
            raise ValueError('Disposable incoming carry requires an unsigned quantum-carry adder.')
        sizes,terminal_dirty = _terminal_partition(a,b,carry_in,clean,dirty_wires,
                                                   release_input=True,ordinary_final=True,
                                                   allow_dirty_terminal=overflow_phase is None or allow_dirty_overflow,
                                                   overflow_phase=overflow_phase is not None and allow_dirty_overflow)
    elif overflow_phase is not None and allow_dirty_overflow:
        sizes,terminal_dirty = _terminal_partition(a,b,carry_in,clean,dirty_wires,
                                                   ordinary_final=True,overflow_phase=True)
    else:
        if signed_source or overflow_phase is not None:
            sizes = partition(n, clean)
        else:
            sizes,terminal_dirty = _terminal_partition(a,b,carry_in,clean,dirty_wires,
                                                       ordinary_final=True)
    builder.x(km.array(b))
    boundaries = []
    start, carry = 0, carry_in
    released_input=False
    for number, length in enumerate(sizes):
        aa, bb = a[start:start+length], b[start:start+length]
        retain = number+1 < len(sizes)
        if not retain and terminal_dirty is not None:
            terminal_add(builder,aa,bb,carry,dirty=terminal_dirty,debt=debt,start=start,
                         overflow_phase=overflow_phase)
            outgoing = False
        else:
            outgoing = _segment_repay(builder, aa, bb, carry, retain_outgoing=retain,
                                      preserve=preserve, start=start, debt=debt,
                                      overflow_phase=overflow_phase if not retain else None)
        if retain:
            recorded_incoming=carry
            if number==0 and carry_lifecycle is not None:
                carry_lifecycle[0](carry_in)
                recorded_incoming=None
                released_input=True
            boundaries.append((aa, bb, recorded_incoming, outgoing))
        carry = outgoing
        start += length
    for aa, bb, incoming, outgoing in reversed(boundaries):
        if outgoing is False:
            continue
        result = builder.alloc_bits(1)[0]
        builder.hmr(outgoing, result)
        builder.free(outgoing)
        builder.push_condition(result)
        recreated = incoming is None
        if recreated:
            incoming=carry_lifecycle[1]()
        _phase_borrow(builder, aa, bb, incoming, preserve=preserve)
        if recreated:
            carry_lifecycle[0](incoming)
        builder.pop_condition()
        builder.free(result)
    builder.x(km.array(b))
    if debt.measurements:
        raise AssertionError(f"Unpaid carry positions: {sorted(debt.measurements)}")
    return released_input

