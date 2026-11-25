# Copyright 2026 Syed Asad Ali
# SPDX-License-Identifier: Apache-2.0
"""Fuse the final pair shift and semilog alignment with a radix-four route.

After the existing coarse normalization, the remaining leading-zero count
is r=2*f+e in 0..3. Two temporary wires hold e and m=f*e. Clearing the known
low-half leading one leaves an ordinary zero-supported left shift by r.
Five freshly synthesized C4 networks rotate the complete four-bit blocks;
three lane shifts transfer the wrapped bits to the next block. The partial
top block is zero when r>0. Its lane-one exchange has known values and is
therefore affine. This emits 33 controlled swaps plus one AND per direction.

Both helpers are erased immediately using the appropriate source/output
leading-bit identities. No new measurement debt reaches the packed phase,
the final thermometer conversion, or any other owner.
"""
from __future__ import annotations

from contextlib import contextmanager
import sys

import fusion.normalization as normalization
import normalization_fused
import prefix_normalization
from c4_routing_math import c4_synthesis
from shared_normalization_controls import SharedNormalizationCleanupPass


@contextmanager
def _parity(builder, wires):
    """Borrow a nonempty parity frame and restore every control wire."""
    wires = list(wires)
    if not wires or len(set(wires)) != len(wires):
        raise ValueError('A routing parity must contain distinct quantum controls.')
    pivot = wires[0]
    for other in wires[1:]:
        builder.cx(other, pivot)
    try:
        yield pivot
    finally:
        for other in reversed(wires[1:]):
            builder.cx(other, pivot)


def _local_blocks(builder, inputs, f, e, *, inverse):
    network, certificate = c4_synthesis()
    if len(network) != 4 or certificate['shortest_length'] != 4:
        raise AssertionError('The from-source C4 network has changed its four-swap contract.')
    blocks = range(5)
    sequence = list(network)
    if inverse:
        blocks = reversed(blocks)
        sequence.reverse()
    swaps = 0
    for block in blocks:
        for operation in sequence:
            mask = operation['control_mask']
            wires = [wire for bit, wire in enumerate((e, f)) if mask >> bit & 1]
            first, second = operation['swap']
            with _parity(builder, wires) as control:
                builder.cswap(control, inputs[4 * block + first], inputs[4 * block + second])
            swaps += 1
    if swaps != 20:
        raise AssertionError('The five full radix-four blocks must use twenty swaps.')
    return swaps


def _lane_transfers(builder, inputs, f, e, m, *, inverse):
    swaps = affine = 0
    lanes = reversed(range(3)) if inverse else range(3)
    for lane in lanes:
        positions = list(range(lane, len(inputs), 4))
        pairs = list(zip(positions[:-1], positions[1:]))
        if not inverse:
            pairs.reverse()
        # lane < r: lane0 = f OR e, lane1 = f, lane2 = f*e.
        controls = (e, f, m) if lane == 0 else ((f,) if lane == 1 else (m,))
        with _parity(builder, controls) as control:
            for first, second in pairs:
                if lane == 1 and second == 21:
                    # At the forward boundary, f=1 gives (1-e,0).
                    # XOR f*(1-e)=f XOR m into both wires also implements
                    # the exact inverse on the corresponding routed image.
                    for source in (f, m):
                        builder.cx(source, inputs[first])
                        builder.cx(source, inputs[second])
                    affine += 1
                else:
                    builder.cswap(control, inputs[first], inputs[second])
                    swaps += 1
    if swaps != 13 or affine != 1:
        raise AssertionError('The radix-four lanes must contain thirteen swaps and one affine exchange.')
    return swaps


def joint_pair_semilog(builder, inputs, f, *, inverse=False):
    """Map the post-coarse word to the usual semilog representation, or back.

    The input is positive and has at most three leading zero bits, with f
    equal to the high bit of that leading-zero count. The forward output
    exactly matches the existing last pair shift followed by semilog_align.
    """
    inputs = list(inputs)
    if len(inputs) != 22 or len(set(inputs + [f])) != 23:
        raise ValueError('The joint route needs twenty-two data bits and a distinct pair flag.')
    entry = builder.num_allocated_qubits
    m, e = builder.alloc_qubits(2)
    if inverse:
        builder.x(e)
        builder.cx(inputs[21], e)
        builder.ccx(f, e, m)
    else:
        # First m=h=f*x19, then e=1 XOR x21 XOR h and m=f XOR h=f*e.
        builder.ccx(f, inputs[19], m)
        builder.x(e)
        builder.cx(inputs[21], e)
        builder.cx(m, e)
        builder.cx(f, m)

    def toggle_low_half_leading_one():
        builder.cx(e, inputs[20])
        builder.cx(m, inputs[20])
        builder.cx(m, inputs[18])

    if inverse:
        lanes = _lane_transfers(builder, inputs, f, e, m, inverse=True)
        local = _local_blocks(builder, inputs, f, e, inverse=True)
        toggle_low_half_leading_one()
        # Restored support gives h=f*x19=f XOR m and e=1 XOR x21 XOR h.
        builder.cx(f, m)
        builder.x(e)
        builder.cx(inputs[21], e)
        builder.cx(m, e)
        builder.free(e)
        builder.del_and(f, inputs[19], m)
        builder.free(m)
    else:
        toggle_low_half_leading_one()
        local = _local_blocks(builder, inputs, f, e, inverse=False)
        lanes = _lane_transfers(builder, inputs, f, e, m, inverse=False)
        builder.del_and(f, e, m)
        builder.free(m)
        # The semilog branch remains exactly at the top of the routed word.
        builder.x(e)
        builder.cx(inputs[21], e)
        builder.free(e)
    if builder.num_allocated_qubits != entry:
        raise AssertionError('The joint route did not return its two helpers.')
    return dict(direction='inverse' if inverse else 'forward',
                controlled_swaps=local + lanes, local_block_swaps=local,
                lane_swaps=lanes, affine_top_lane_exchanges=1,
                temporary_ANDs=1, helper_qubits=2, exact_Toffoli_equivalents=34,
                all_controls_restored=True, pending_measurement_debts=0,
                forward_output_is_existing_semilog_representation=True)


class JointNormalizationSemilogPass:
    """Replace only the final pair route and its two matched semilog calls."""
    def __init__(self, *, semilog_modules=()):
        self.semilog_modules = tuple(semilog_modules)
        self.states = {}
        self.routes = []
        self.noop_calls = []

    @staticmethod
    def _key(builder, inputs):
        return id(builder), tuple(inputs)

    @contextmanager
    def install(self):
        old_shift = normalization_fused._fused_shift
        if (old_shift.__module__ != normalization_fused.__name__
                or old_shift.__name__ != '_fused_shift'):
            raise RuntimeError('The fused normalization route already has another scoped owner.')
        modules = [normalization]
        scheduled = sys.modules.get('scheduled_generator')
        for module in self.semilog_modules + ((scheduled,) if scheduled is not None else ()):
            if module not in modules:
                modules.append(module)
        previous_align = [(module, module.semilog_align) for module in modules]
        if any(function is not normalization.semilog_align for _, function in previous_align):
            raise RuntimeError('A semilog alias has an incompatible active owner.')

        def shift(builder, inputs, flags, *, inverse):
            inputs, flags, maximum = prefix_normalization._shape(inputs, flags)
            if len(inputs) != 22 or maximum != 10:
                raise ValueError('The joint route requires the selected original count geometry.')
            key = self._key(builder, inputs)
            if inverse:
                if self.states.get(key) != 'inverse_semilog_matched':
                    raise AssertionError('Inverse normalization lacks its matched preceding semilog call.')
                self.routes.append(joint_pair_semilog(builder, inputs, flags[0], inverse=True))
                normalization_fused._coarse(builder, inputs, flags, inverse=True)
                self.states[key] = 'completed'
            else:
                if key in self.states:
                    raise AssertionError('The selected joint normalization may run forward only once.')
                normalization_fused._coarse(builder, inputs, flags, inverse=False)
                self.routes.append(joint_pair_semilog(builder, inputs, flags[0]))
                self.states[key] = 'forward_route_emitted'

        def align(builder, inputs, *, inverse=False):
            inputs = list(inputs)
            key = self._key(builder, inputs)
            expected = 'forward_semilog_matched' if inverse else 'forward_route_emitted'
            if self.states.get(key) != expected:
                raise AssertionError('A semilog no-op is not adjacent to its matching joint lifecycle.')
            self.states[key] = 'inverse_semilog_matched' if inverse else 'forward_semilog_matched'
            self.noop_calls.append('inverse' if inverse else 'forward')

        normalization_fused._fused_shift = shift
        for module, _ in previous_align:
            module.semilog_align = align
        try:
            yield self
        finally:
            normalization_fused._fused_shift = old_shift
            for module, function in previous_align:
                module.semilog_align = function
        if list(self.states.values()) != ['completed'] or self.noop_calls != ['forward', 'inverse']:
            raise AssertionError('A joint route or its explicit semilog alias remained unmatched.')
        if [record['direction'] for record in self.routes] != ['forward', 'inverse']:
            raise AssertionError('The joint pair/semilog route must complete both directions once.')

    def metadata(self):
        if list(self.states.values()) != ['completed']:
            raise AssertionError('The joint normalization lifecycle is incomplete.')
        return dict(status='JOINT_RADIX4_PAIR_SEMILOG_LIFECYCLE_COMPLETED',
                    routes=self.routes, matched_semilog_calls=self.noop_calls,
                    original_final_pair_and_semilog_E=80,
                    joint_final_pair_and_semilog_E=68,
                    exact_saved_E_vs_stage86=12,
                    existing_coarse_route_and_count_basis_unchanged=True,
                    no_extra_qubits_at_other_region_boundaries=True,
                    immediate_HMR_phase_repayment=True,
                    original_semilog_representation_preserved=True,
                    full_generator_official_verification_required=True)


class SharedRadix4NormalizationCleanupPass(SharedNormalizationCleanupPass):
    """Compose the joint route inside the accepted shared-count lifecycle."""
    def __init__(self, *, semilog_modules=()):
        super().__init__()
        self.joint = JointNormalizationSemilogPass(semilog_modules=semilog_modules)

    @contextmanager
    def install(self):
        with super().install(), self.joint.install():
            yield self

    def metadata(self):
        result = super().metadata()
        result['joint_radix4_pair_semilog'] = self.joint.metadata()
        result['component_saving_E_vs_stage85'] = '47/2'
        result['component_saving_E_vs_stage86'] = '12'
        return result
