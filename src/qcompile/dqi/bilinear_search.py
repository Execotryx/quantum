"""Bounded flip-graph search for a smaller GF(64) multiplication tensor."""

import random
import time
from collections import defaultdict

from .field import GF4096
from .tower import BilinearTerm, linear, tower


def apply(terms: tuple[BilinearTerm, ...], left: int, right: int) -> int:
    result = 0
    for a, b, word in terms:
        if (a & left).bit_count() & (b & right).bit_count() & 1:
            result ^= word
    return result


def basis_tensor(terms: tuple[BilinearTerm, ...]) -> tuple[int, ...]:
    return tuple(apply(terms, 1 << i, 1 << j) for i in range(6) for j in range(6))


def verify(terms: tuple[BilinearTerm, ...], *, exhaustive: bool = False) -> None:
    """Compare against native-contract polynomial arithmetic in the pinned subfield basis."""
    if any(not all(0 < value < 64 for value in term) for term in terms):
        raise ValueError("tensor terms must contain nonzero 6-bit factors")
    field = GF4096()
    basis = tower().basis[:6]
    mapped = [linear(basis, i) for i in range(64)]
    values = range(64) if exhaustive else (1, 2, 4, 8, 16, 32)
    for a in values:
        for b in values:
            if mapped[apply(terms, a, b)] != field.mul(mapped[a], mapped[b]):
                raise ValueError(f"incorrect GF(64) tensor at {a}, {b}")


def reduce_terms(terms: tuple[BilinearTerm, ...]) -> tuple[BilinearTerm, ...]:
    """Merge terms that agree on two tensor axes, discarding zero terms."""
    work = list(terms)
    while True:
        merged = False
        for axis in range(3):
            seen = {}
            others = [i for i in range(3) if i != axis]
            for j, term in enumerate(work):
                key = (term[others[0]], term[others[1]])
                if key in seen:
                    i = seen[key]
                    combined = list(work[i])
                    combined[axis] ^= term[axis]
                    work.pop(j)
                    work.pop(i)
                    if combined[axis]:
                        work.append(tuple(combined))
                    merged = True
                    break
                seen[key] = j
            if merged:
                break
        if not merged:
            return tuple(sorted(work))


def flip(terms: tuple[BilinearTerm, ...], rng: random.Random) -> tuple[BilinearTerm, ...] | None:
    """Apply one tensor-preserving characteristic-two flip at a shared factor."""
    choices = []
    for axis in range(3):
        groups: dict[int, list[int]] = defaultdict(list)
        for index, term in enumerate(terms):
            groups[term[axis]].append(index)
        for indices in groups.values():
            for i, left in enumerate(indices):
                choices.extend((axis, left, right) for right in indices[i + 1:]
                               if sum(a == b for a, b in zip(terms[left], terms[right], strict=True)) == 1)
    if not choices:
        return None
    shared, i, j = rng.choice(choices)
    left, right = list(terms[i]), list(terms[j])
    axes = [axis for axis in range(3) if axis != shared]
    if rng.randrange(2):
        axes.reverse()
    b, c = axes
    left[b] ^= right[b]
    right[c] ^= left[c]
    result = [term for k, term in enumerate(terms) if k != i and k != j]
    result.extend((tuple(left), tuple(right)))
    return tuple(result)


def expand(terms: tuple[BilinearTerm, ...], rng: random.Random) -> tuple[BilinearTerm, ...]:
    """Add a cancelling pair sharing one factor with a randomly selected term."""
    term = rng.choice(terms)
    shared = rng.randrange(3)
    pair = [rng.randrange(1, 64) for _ in range(3)]
    pair[shared] = term[shared]
    for axis in range(3):
        if axis != shared and pair[axis] == term[axis]:
            pair[axis] = 1 if term[axis] != 1 else 2
    added = (pair[0], pair[1], pair[2])
    return (*terms, added, added)


def search(seed: int, max_steps: int, max_seconds: float, restart_steps: int) -> dict:
    """Walk with deterministic restarts; cap steps and wall time before starting."""
    if max_steps < 1 or max_seconds <= 0 or restart_steps < 1:
        raise ValueError("search limits must be positive")
    initial = reduce_terms(tower().subfield_terms)
    verify(initial, exhaustive=True)
    expected = basis_tensor(initial)
    rng = random.Random(seed)
    best = current = initial
    started = time.monotonic()
    completed = restarts = 0
    reason = "step_limit"
    for step in range(max_steps):
        if time.monotonic() - started >= max_seconds:
            reason = "time_limit"
            break
        if step and step % restart_steps == 0:
            current = best
            restarts += 1
        if step % 20 == 0:
            current = reduce_terms(current)
            if len(current) < len(best):
                if basis_tensor(current) != expected:
                    raise ValueError("reduction changed tensor")
                best = current
                if len(best) <= 15:
                    reason = "rank_15_found"
                    break
        candidate = flip(current, rng)
        if candidate is None:
            if len(current) <= len(best):
                current = expand(current, rng)
            else:
                current = best
                restarts += 1
            continue
        current = candidate
        completed += 1
    current = reduce_terms(current)
    if len(current) < len(best):
        if basis_tensor(current) != expected:
            raise ValueError("reduction changed tensor")
        best = current
        if len(best) <= 15:
            reason = "rank_15_found"
    verify(best, exhaustive=True)
    return {"initial_rank": len(initial), "best_rank": len(best), "terms": best,
            "basis": tower().basis[:6], "steps_completed": completed, "restarts": restarts,
            "termination": reason, "elapsed_seconds": time.monotonic() - started}
