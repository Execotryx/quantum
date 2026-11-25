# Copyright 2026 Syed Asad Ali (team syed3000)
# SPDX-License-Identifier: Apache-2.0
"""Batch exact table-measurement phase debts into one final correction.

The generator supplies each measured table as a function of the SAME logical
address. Its physical address wires may be modified, encoded, or measured
between ``erase`` and ``flush``; at ``flush`` the original address must have
been reconstructed. Intermediate quantum operations must be computational-
basis permutations, diagonal phases, or exact measurement gadgets of that
kind. Under these conditions pending signs simply follow their original
logical input labels and can be corrected together at the end.

No measurement outcome is assumed. All branch signs, including constants,
are retained. Tables and their ANFs come only from mathematical truth tables.
"""
from __future__ import annotations

import kickmix as km
from codebook import Codebook,word_functions,parity_function


def _set_bits(value):
    while value:
        bit = value & -value
        yield bit.bit_length()-1
        value ^= bit


def _anf(table):
    values = list(map(int, table))
    if not values or len(values) & (len(values)-1):
        raise ValueError('Expected a power-of-two mathematical truth table.')
    n = len(values).bit_length()-1
    for bit in range(n):
        for address in range(len(values)):
            if address & (1 << bit):
                values[address] ^= values[address ^ (1 << bit)]
    return values


class DeferredTablePhases:
    """An exact classical ledger of outcome-dependent table signs."""

    def __init__(self, address_bits):
        self.address_bits = int(address_bits)
        if self.address_bits < 1:
            raise ValueError('A nonempty address is required.')
        self.pending = []
        self.erased_words = 0
        self.erased_qubits = 0

    def erase(self, builder, table, targets):
        """HMR a known table word immediately; keep its exact phase debt.

        Targets are reset to zero and remain allocated. No address wire and
        no quantum workspace is required by this operation. Call outside any
        classical condition block: this ledger records unconditional erasures.
        """
        targets = list(targets)
        table = list(map(int, table))
        if len(table) != 1 << self.address_bits:
            raise ValueError('All debt tables must share the logical address.')
        if any(value < 0 or value >= 1 << len(targets) for value in table):
            raise ValueError('A debt table exceeds its target word.')
        coefficients = _anf(table)
        # A complete algebraic certificate for every address and outcome:
        # reconstruct the whole vector-valued truth table, not sampled bits.
        if _anf(coefficients) != table:
            raise AssertionError('Boolean Mobius transform certificate failed.')
        outcomes = builder.alloc_bits(len(targets))
        builder.hmr(km.array(targets), outcomes)
        self.pending.append((coefficients, outcomes))
        self.erased_words += 1
        self.erased_qubits += len(targets)
        return {'and_count': 0, 'workspace_qubits': 0,
                'measurement_bits': len(targets), 'phase_deferred': True}

    def record_measurements(self, table, outcomes):
        """Own already-created HMR bits for a remaining table-only phase.

        The caller must first repay every non-table component of the measured
        wire's value exactly. This method emits no gates; it records the
        residual sign (-1) ** dot(outcomes, table(address)). Ownership of the
        classical bits transfers to this ledger and they are freed at flush.
        """
        outcomes=km.array(list(outcomes))
        table=list(map(int,table))
        if len(table)!=1 << self.address_bits:
            raise ValueError('An external measurement debt uses a different logical address.')
        if not len(outcomes) or any(value<0 or value>=1 << len(outcomes) for value in table):
            raise ValueError('An external measurement debt exceeds its classical word.')
        existing={bit for _,word in self.pending for bit in word}
        if len(set(outcomes))!=len(outcomes) or existing.intersection(outcomes):
            raise ValueError('A measurement result already belongs to a pending phase debt.')
        coefficients=_anf(table)
        if _anf(coefficients)!=table:
            raise AssertionError('An external phase-debt truth certificate failed.')
        self.pending.append((coefficients,outcomes))
        self.erased_words+=1;self.erased_qubits+=len(outcomes)
        return {'and_count':0,'workspace_qubits':0,'measurement_bits':len(outcomes),
                'phase_deferred':True,'external_measurement':True}

    def flush(self, builder, address):
        """Repay all debts, once the same logical address has been restored.

        A balanced 4+4 split for an8-bit address uses22 ANDs and14 workspace
        qubits, regardless of the number of erased words or their widths.
        Lower-workspace splits are chosen automatically when necessary.
        """
        address = list(address)
        if len(address) != self.address_bits or len(set(address)) != len(address):
            raise ValueError('Wrong restored address register.')
        if not self.pending:
            return {'and_count': 0, 'workspace_qubits': 0, 'erased_words': 0}
        capacity = builder.max_qubits - builder.num_allocated_qubits
        n = self.address_bits
        choices = []
        for left_count in range(n+1):
            right_count = n-left_count
            left_products = (1 << left_count)-left_count-1
            right_products = (1 << right_count)-right_count-1
            workspace = left_products+max(0, right_count-1)
            if workspace <= capacity:
                choices.append((left_products+right_products, workspace, left_count))
        if not choices:
            raise ValueError('No valid workspace schedule for deferred table phases.')
        expected_ands, workspace_count, left_count = min(choices)
        right_count = n-left_count
        left_products = (1 << left_count)-left_count-1
        workspace = list(builder.alloc_qubits(workspace_count))
        parity = builder.alloc_bits(1)[0]
        left = {1 << bit: address[bit] for bit in range(left_count)}
        steps = []
        position = 0
        for mask in range(1, 1 << left_count):
            if mask.bit_count() < 2:
                continue
            bit = mask.bit_length()-1
            parent = mask ^ (1 << bit)
            temporary = workspace[position]
            position += 1
            builder.ccx(left[parent], address[bit], temporary)
            left[mask] = temporary
            steps.append((left[parent], address[bit], temporary))

        def sign_terms(right_mask, right_wire):
            for left_mask in range(1 << left_count):
                mask = left_mask | (right_mask << left_count)
                terms = [(outcomes, coefficients[mask])
                         for coefficients, outcomes in self.pending
                         if coefficients[mask]]
                if not terms:
                    continue
                builder.bit_store(parity, False)
                for outcomes, output_mask in terms:
                    for bit in _set_bits(output_mask):
                        builder.cx(outcomes[bit], parity)
                if not left_mask and not right_mask:
                    builder.z(parity)
                else:
                    builder.push_condition(parity)
                    if not left_mask:
                        builder.z(right_wire)
                    elif not right_mask:
                        builder.z(left[left_mask])
                    else:
                        builder.cz(left[left_mask], right_wire)
                    builder.pop_condition()

        def visit_right(mask, product, depth):
            sign_terms(mask, product)
            for bit in range(mask.bit_length(), right_count):
                temporary = workspace[left_products+depth]
                control = address[left_count+bit]
                builder.ccx(product, control, temporary)
                visit_right(mask | (1 << bit), temporary, depth+1)
                builder.del_and(product, control, temporary)

        sign_terms(0, None)
        for bit in range(right_count):
            visit_right(1 << bit, address[left_count+bit], 0)
        for a, b, temporary in reversed(steps):
            builder.del_and(a, b, temporary)
        builder.free(km.array(workspace))
        builder.free(parity)
        for _, outcomes in self.pending:
            builder.free(outcomes)
        words, qubits = self.erased_words, self.erased_qubits
        self.pending.clear()
        self.erased_words = self.erased_qubits = 0
        return {'and_count': expected_ands, 'workspace_qubits': workspace_count,
                'left_address_bits': left_count, 'erased_words': words,
                'erased_qubits': qubits}

    def flush_on_code(self,builder,variables,functions):
        """Repay pending signs on a static quadratic code using Clifford gates.

        Every variable must contain the supplied function of the same logical
        address. This does not erase those variables: their subsequent cleanup
        requires its own exact phase correction. All debts are proved solvable
        before any circuit or ledger mutation is performed.
        """
        variables=list(variables);functions=list(map(int,functions))
        if len(variables)!=len(functions) or len(set(variables))!=len(variables):
            raise ValueError('A static phase code requires distinct matching quantum wires.')
        if not self.pending:
            return {'and_count':0,'workspace_qubits':0,'erased_words':0}
        size=1 << self.address_bits
        code=Codebook(functions,size=size)
        terms={}
        certified=0
        for coefficients,outcomes in self.pending:
            table=_anf(coefficients)
            for bit,function in enumerate(word_functions(table,len(outcomes))):
                expression=code.span.solve(function)
                if expression is None:
                    raise ValueError('The static code cannot repay every pending table phase quadratically.')
                if parity_function(expression,code.columns)!=function:
                    raise AssertionError('A static-code phase certificate is incorrect.')
                certified+=1
                for index in _set_bits(expression):
                    terms.setdefault(code.monomials[index],[]).append(outcomes[bit])
        parity=builder.alloc_bits(1)[0]
        for monomial,outcomes in sorted(terms.items()):
            builder.bit_store(parity,False)
            for outcome in outcomes:builder.cx(outcome,parity)
            if not monomial:
                builder.z(parity)
            else:
                builder.push_condition(parity)
                if len(monomial)==1:builder.z(variables[monomial[0]])
                else:builder.cz(variables[monomial[0]],variables[monomial[1]])
                builder.pop_condition()
        builder.free(parity)
        for _,outcomes in self.pending:builder.free(outcomes)
        words,qubits=self.erased_words,self.erased_qubits
        self.pending.clear();self.erased_words=self.erased_qubits=0
        return {'and_count':0,'workspace_qubits':0,'erased_words':words,
                'erased_qubits':qubits,'quadratic_code_rank':len(code.span.pivots),
                'phase_monomials':len(terms),'functions_certified':certified,
                'addresses_per_certificate':size}

