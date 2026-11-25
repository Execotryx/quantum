# Copyright 2026 Syed Asad Ali
# SPDX-License-Identifier: Apache-2.0
"""Install fresh twelve-swap routing inside the accepted high phase body."""
from __future__ import annotations

from contextlib import contextmanager

import high_c4_phase
from c4_routing_math import flag_terms
from high_slack_math import synthesize
from reencoded_c20_phase import LinearFlagSpace


ORIGINAL_ROUTE = high_c4_phase.route_high


def route_high(builder, value, packed, u, *, inverse=False, omit_repayment=False,
               omit_first_swap=False):
    """Twelve generated CSWAPs and four exactly erased flag products."""
    value = list(value)
    if len(value) != 8 or len(set(value)) != 8:
        raise ValueError('The high slack route requires eight distinct data wires.')
    if not packed.is_packed or packed.max_k != 10:
        raise ValueError('The high slack route requires the accepted packed count promise.')
    if len(set(value+list(packed.residual)+[packed.t, u])) != len(value)+len(packed.residual)+2:
        raise ValueError('The high data and all packed-count owners must be disjoint.')
    before = builder.num_allocated_qubits
    if builder.max_qubits-before < 2:
        raise ValueError('The high slack route requires its two temporary flag slots.')
    route, schedule, certificate = synthesize()
    steps = list(zip(route, schedule['chosen_subspaces']))
    if inverse:
        steps.reverse()
    flags = LinearFlagSpace(builder, list(packed.residual[:4])+[packed.t, u], flag_terms,
                            omit_repayment=omit_repayment)
    swaps = 0
    try:
        for (mask, left, right), space in steps:
            flags.move_to(space)
            with flags.control(mask) as control:
                if not (omit_first_swap and swaps == 0):
                    builder.cswap(control, value[left], value[right])
                swaps += 1
    finally:
        flags.close()
    if (swaps != 12 or flags.products != 4 or flags.measurements != 4 or
            builder.num_allocated_qubits != before):
        raise AssertionError('The fresh high route changed its charge or helper ownership.')
    return dict(cswaps=swaps, and_products=flags.products, maximum_live_flags=2,
                inverse=bool(inverse), mathematical_synthesis=certificate,
                flag_transitions=flags.transitions, all_local_flag_measurements_repaid=True,
                cyclic_bounded_slack_high=True,
                negative_control_omits_first_swap=bool(omit_first_swap),
                negative_control_omits_flag_repayment=bool(omit_repayment))


@contextmanager
def installed(*, audit=None, omit_repayment=False, omit_first_swap=False):
    """Replace the route adapter, preserving the existing high-body scope."""
    previous = high_c4_phase.route_high
    if previous is not ORIGINAL_ROUTE:
        raise RuntimeError('Another high-route replacement is active; replace its installation rather than nesting.')
    records = [] if audit is None else audit
    negative_phase, negative_swap = bool(omit_repayment), bool(omit_first_swap)

    def emit(builder, value, packed, u, *, inverse=False, omit_repayment=False):
        metadata = route_high(builder, value, packed, u, inverse=inverse,
                              omit_repayment=omit_repayment or negative_phase,
                              omit_first_swap=negative_swap and not inverse)
        records.append(dict(inverse=bool(inverse), cswaps=metadata['cswaps'],
                            flag_products=metadata['and_products'], maximum_live_flags=2,
                            unchanged_allocation_count=builder.num_allocated_qubits,
                            mathematical_synthesis=metadata['mathematical_synthesis'],
                            flag_transitions=metadata['flag_transitions']))
        return metadata

    high_c4_phase.route_high = emit
    try:
        yield records
    finally:
        high_c4_phase.route_high = previous
