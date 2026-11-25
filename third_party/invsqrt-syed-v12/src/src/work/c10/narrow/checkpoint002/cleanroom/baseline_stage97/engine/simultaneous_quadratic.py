# Copyright 2026 Syed Asad Ali (team syed3000)
# SPDX-License-Identifier: Apache-2.0
"""Simultaneous rank-reducing products on a frozen quadratic input code.

No circuit operations occur in this module. Unlike the prior incomplete
fan-in heuristic, inputs never change or retire during a block. A new product
is solved from common matrix-image constraints, not selected from one
output's existing factor list. Every accepted rank change is rechecked by
ordinary GF(2) elimination and every output truth is re-certified.
"""
from __future__ import annotations

from dataclasses import asdict
from itertools import combinations
import random
import time

from codebook import bits, factor_polynomial, parity_function


def gf2_rank(rows):
    pivots = {}
    for original in rows:
        value = int(original)
        while value:
            pivot = value.bit_length()-1
            if pivot not in pivots:
                pivots[pivot] = value
                break
            value ^= pivots[pivot]
    return len(pivots)


def solve_linear(rows, right, width):
    """Return one solution plus a homogeneous basis, or None if inconsistent."""
    rows, right = list(map(int, rows)), list(map(int, right))
    if len(rows) != len(right) or any(r not in (0, 1) for r in right):
        raise ValueError('Every GF(2) equation needs one right-hand-side bit.')
    mask = (1 << width)-1
    if any(row & ~mask for row in rows):
        raise ValueError('A linear equation extends beyond the declared width.')
    pivots = {}
    for value, constant in zip(rows, right):
        while value:
            pivot = value.bit_length()-1
            if pivot not in pivots:
                pivots[pivot] = (value, constant)
                break
            old, old_constant = pivots[pivot]
            value ^= old
            constant ^= old_constant
        else:
            if constant:
                return None

    def complete(free, homogeneous):
        result = free
        # Highest-bit pivots depend only on lower coordinates, so ascending
        # pivot order is exact back substitution with the free bits fixed.
        for pivot in sorted(pivots):
            row, constant = pivots[pivot]
            value = (row & result).bit_count() & 1
            if value ^ (0 if homogeneous else constant):
                result ^= 1 << pivot
        return result

    solution = complete(0, False)
    nullspace = [complete(1 << i, True) for i in range(width) if i not in pivots]
    if any(((row & solution).bit_count() & 1) != bit for row, bit in zip(rows, right)):
        raise AssertionError('GF(2) solution verification failed.')
    if any((row & vector).bit_count() & 1 for vector in nullspace for row in rows):
        raise AssertionError('GF(2) nullspace verification failed.')
    return solution, nullspace


def matrix_of(plan):
    rows = [0]*plan.width
    for i, j in plan.edges:
        rows[i] ^= 1 << j
        rows[j] ^= 1 << i
    rank = gf2_rank(rows)
    if rank != 2*plan.and_count:
        raise AssertionError('Alternating rank disagrees with the exact product factorization.')
    return rows


def product_polynomial(width, left, right):
    """The complete Boolean product, including diagonal linear terms."""
    if left <= 0 or right <= 0 or (left | right) >> width:
        raise ValueError('Product factors must be nonzero vectors of the declared width.')
    edges = set()
    for a in bits(left):
        for b in bits(right):
            if a == b:
                continue
            edge = tuple(sorted((a, b)))
            if edge in edges:
                edges.remove(edge)
            else:
                edges.add(edge)
    return factor_polynomial(width, False, left & right, edges)


def xor_polynomial(first, second):
    if first.width != second.width:
        raise ValueError('A simultaneous block must use one frozen input width.')
    return factor_polynomial(first.width, first.constant ^ second.constant,
                             first.linear ^ second.linear,
                             set(first.edges) ^ set(second.edges))


def vector_candidates(basis, trials, rng):
    """A bounded deterministic subset of nonzero vectors in one subspace."""
    limit = min(int(trials), (1 << len(basis))-1)
    if limit <= 0:
        return []
    found, seen = [], set()

    def add(value):
        if value and value not in seen and len(found) < limit:
            seen.add(value); found.append(value)

    for value in basis:
        add(value)
    for i in range(len(basis)):
        for j in range(i+1, len(basis)):
            add(basis[i]^basis[j])
            if len(found) >= limit:
                return found
    for _ in range(max(8, 8*limit)):
        add(parity_function(rng.getrandbits(len(basis)), basis))
        if len(found) >= limit:
            break
    return found


def common_product(plans, *, seed, factor_trials=64, deadline=None, progress=None):
    """Find one certified product reducing at least two output ranks.

    For a symmetric alternating matrix A, im(A)=ker(A)^perp. If A*w=u,
    u,v are both in im(A), and w dot v=1, then adding u*v^T+v*u^T drops
    rank(A) by2. These conditions are only candidate generators here: every
    resulting rank is recomputed independently before any product is accepted.
    """
    if not plans or len({p.width for p in plans}) != 1:
        raise ValueError('All forms must have the same nonempty fixed input basis.')
    width = plans[0].width
    matrices = [matrix_of(p) for p in plans]
    ranks = [gf2_rank(rows) for rows in matrices]
    kernels = [solve_linear(rows, [0]*width, width)[1] for rows in matrices]
    active = [i for i, rank in enumerate(ranks) if rank]
    counters = dict(subsets=0, left_vectors=0, right_solutions=0,
                    independently_checked_products=0, stopped_by_deadline=False)
    best = None
    seen_products = set()
    for count in range(len(active), 1, -1):
        for subset in combinations(active, count):
            if deadline is not None and time.perf_counter() >= deadline:
                counters['stopped_by_deadline'] = True
                return best, counters
            counters['subsets'] += 1
            constraints = [vector for i in subset for vector in kernels[i]]
            solved = solve_linear(constraints, [0]*len(constraints), width)
            common_basis = solved[1]
            if len(common_basis) < 2:
                continue
            subset_mask = sum(1 << i for i in subset)
            rng = random.Random(seed+104729*subset_mask)
            candidates = vector_candidates(common_basis, factor_trials, rng)
            for left in candidates:
                if deadline is not None and time.perf_counter() >= deadline:
                    counters['stopped_by_deadline'] = True
                    return best, counters
                counters['left_vectors'] += 1
                inverse_images = []
                for i in subset:
                    answer = solve_linear(matrices[i], [(left >> j) & 1 for j in range(width)], width)
                    if answer is None:
                        raise AssertionError('A common-image candidate has no matrix preimage.')
                    inverse_images.append(answer[0])
                equations = constraints+inverse_images
                answer = solve_linear(equations, [0]*len(constraints)+[1]*len(subset), width)
                if answer is None:
                    continue
                counters['right_solutions'] += 1
                right, freedom = answer
                right_choices = [right]+[right ^ value for value in freedom[:3]]
                for candidate_right in right_choices:
                    canonical = tuple(sorted((left, candidate_right)))
                    if canonical in seen_products:
                        continue
                    seen_products.add(canonical)
                    product = product_polynomial(width, *canonical)
                    if product.and_count != 1:
                        raise AssertionError('Rank-pair conditions did not yield one independent product.')
                    product_matrix = matrix_of(product)
                    after = [gf2_rank([a ^ b for a, b in zip(matrix, product_matrix)])
                             for matrix in matrices]
                    counters['independently_checked_products'] += 1
                    affected = tuple(i for i, (old, new) in enumerate(zip(ranks, after))
                                     if new == old-2)
                    if not set(subset) <= set(affected):
                        raise AssertionError('A proposed shared product failed exact rank reduction.')
                    if len(affected) < 2:
                        continue
                    key = (-len(affected), sum(x.bit_count() for x in canonical), canonical,
                           affected)
                    if best is None or key < best['key']:
                        best = dict(key=key, left=canonical[0], right=canonical[1],
                                    outputs=list(affected), product=product,
                                    matrix_ranks_before=ranks,
                                    matrix_ranks_after=[after[i] if i in affected else ranks[i]
                                                        for i in range(len(plans))],
                                    common_image_dimension=len(common_basis),
                                    witness_subset=list(subset))
                    if len(affected) == len(active):
                        # This product reaches the maximum possible immediate
                        # saving. No search for a prettier Clifford frame is
                        # needed for the bounded AND screen.
                        return best, counters
            if progress is not None and counters['subsets'] % 16 == 0:
                progress(dict(event='subset_progress', **counters,
                              best_shared_outputs=0 if best is None else len(best['outputs'])))
        if best is not None:
            # All larger subsets were tested first. Stop at the first subset
            # cardinality with a successful certificate; this is a heuristic
            # over factor candidates, never a proof of global optimality.
            return best, counters
    return best, counters


def certify_truths(functions, targets, residuals, products, *, size=256):
    full = (1 << size)-1
    truths = [0]*len(targets)
    for record in products:
        polynomial = product_polynomial(len(functions), record['left'], record['right'])
        truth = parity_function(record['left'], functions) & parity_function(record['right'], functions)
        if polynomial.evaluate_functions(functions, full) != truth or polynomial.evaluate_factored_functions(functions, full) != truth:
            raise AssertionError('The shared product truth certificate failed.')
        for i in record['outputs']:
            truths[i] ^= truth
    for i, (target, residual) in enumerate(zip(targets, residuals)):
        direct = residual.evaluate_functions(functions, full)
        factored = residual.evaluate_factored_functions(functions, full)
        if direct != factored or truths[i] ^ direct != target:
            raise AssertionError('A complete simultaneous output truth certificate failed.')
        matrix_of(residual)
    return dict(rows=size, outputs=len(targets),
                shared_products=len(products), complete_output_truths=True)


def extract_shared(functions, targets, initial_plans, *, seed=2026110641,
                   factor_trials=64, maximum_steps=32, deadline=None,
                   progress=None, size=256):
    plans = list(initial_plans)
    if len(plans) != len(targets) or any(plan.width != len(functions) for plan in plans):
        raise ValueError('Every target requires a polynomial on the same frozen code.')
    steps = []
    before = sum(plan.and_count for plan in plans)
    certificate = certify_truths(functions, targets, plans, steps, size=size)
    stop_reason = 'step_limit'
    search_counters = []
    for step in range(maximum_steps):
        selected, counters = common_product(
            plans, seed=seed+1000003*step, factor_trials=factor_trials,
            deadline=deadline, progress=progress)
        search_counters.append(counters)
        if selected is None:
            stop_reason = 'soft_deadline' if counters['stopped_by_deadline'] else 'no_common_product_found'
            break
        product = selected['product']
        old = [plan.and_count for plan in plans]
        for i in selected['outputs']:
            plans[i] = xor_polynomial(plans[i], product)
            if plans[i].and_count != old[i]-1:
                raise AssertionError('Accepted rank reduction did not remove one residual AND.')
        record = {key: value for key, value in selected.items() if key not in {'key', 'product'}}
        record.update(step=step, emitted_product_ANDs=1,
                      incremental_AND_saving=len(selected['outputs'])-1,
                      residual_ANDs_before=old,
                      residual_ANDs_after=[plan.and_count for plan in plans])
        steps.append(record)
        certificate = certify_truths(functions, targets, plans, steps, size=size)
        actual = len(steps)+sum(plan.and_count for plan in plans)
        if actual != before-sum(item['incremental_AND_saving'] for item in steps):
            raise AssertionError('Aggregate AND savings do not account for shared helper costs.')
        if progress is not None:
            progress(dict(event='shared_product_accepted', step=step,
                          outputs=selected['outputs'], total_shared_products=len(steps),
                          residual_ANDs=sum(plan.and_count for plan in plans),
                          total_decoder_ANDs=actual, saved_from_fixed_forms=before-actual,
                          truth_rows_checked=size,
                          certificate_checkpoint=dict(
                              products=list(steps), residual_forms=[asdict(p) for p in plans])))
        if counters['stopped_by_deadline']:
            stop_reason = 'soft_deadline'
            break
    return plans, dict(
        independent_fixed_decoder_ANDs=before,
        shared_product_ANDs=len(steps), residual_decoder_ANDs=sum(plan.and_count for plan in plans),
        total_decoder_ANDs=len(steps)+sum(plan.and_count for plan in plans),
        saved_from_fixed_forms=before-len(steps)-sum(plan.and_count for plan in plans),
        steps=steps, search_counters=search_counters, stop_reason=stop_reason,
        truth_certificate=certificate, fixed_basis_preserved=True,
        exhaustive_optimality_claim=False)
