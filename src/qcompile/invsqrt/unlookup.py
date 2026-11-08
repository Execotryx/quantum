"""Measurement unlookup with a phase repair from the coefficient truth table."""

from typing import Any


def repair_table(rows: tuple[int, ...], low_bits: int) -> tuple[tuple[int, ...], ...]:
    """Compute low-address ANF coefficients, packed across the output bits."""
    span = 1 << low_bits
    if len(rows) % span:
        raise ValueError("incomplete repair truth table")
    banks = []
    for start in range(0, len(rows), span):
        words = list(rows[start:start + span])
        for bit in range(low_bits):
            mask = 1 << bit
            for subset in range(span):
                if subset & mask:
                    words[subset] ^= words[subset ^ mask]
        banks.append(tuple(words))
    return tuple(banks)


def unlookup(builder: Any, address: Any, registers: list[Any],
             table: tuple[tuple[int, ...], ...], *, sibling_cnot: bool = False) -> None:
    wires = [wire for register in registers for wire in register]
    packed = []
    for row in table:
        offset, word = 0, 0
        for value, register in zip(row, registers, strict=True):
            word |= value << offset
            offset += len(register)
        packed.append(word)
    low_bits = min(4, len(address) - 1)
    banks = repair_table((0,) * (1 << (len(address) - 2)) + tuple(packed), low_bits)
    outcomes = builder.alloc_bits(len(wires))
    builder.hmr(wires, outcomes)
    low, high = address[:low_bits], address[low_bits:]
    monomials = {1 << i: wire for i, wire in enumerate(low)}
    workspace = builder.alloc_qubits((1 << low_bits) - low_bits - 1)
    chain = []
    for subset in range(1, 1 << low_bits):
        if subset in monomials:
            continue
        bit = subset & -subset
        a, b, target = monomials[subset ^ bit], monomials[bit], workspace[len(chain)]
        builder.init_and(a, b, target)
        monomials[subset] = target
        chain.append((a, b, target))

    path = builder.alloc_qubits(len(high) - 1)

    def walk(depth: int, prefix: int, control: Any) -> None:
        if depth == len(high):
            for subset, mask in enumerate(banks[prefix]):
                while mask:
                    bit = mask & -mask
                    builder.push_condition(outcomes[bit.bit_length() - 1])
                    if subset:
                        builder.cz(control, monomials[subset])
                    else:
                        builder.z(control)
                    builder.pop_condition()
                    mask ^= bit
            return
        bit = high[len(high) - depth - 1]
        left = 2 * prefix
        remaining = len(high) - depth - 1
        if sibling_cnot and depth and ((left + 1) << remaining) > len(banks) // 4:
            flag = path[depth - 1]
            builder.x(bit)
            builder.init_and(control, bit, flag)
            builder.x(bit)
            walk(depth + 1, left, flag)
            builder.cx(control, flag)
            walk(depth + 1, left + 1, flag)
            builder.del_and(control, bit, flag)
            return
        for direction in (0, 1):
            child = left + direction
            if (child + 1) << remaining <= len(banks) // 4:
                continue
            if not direction:
                builder.x(bit)
            if depth:
                flag = path[depth - 1]
                builder.init_and(control, bit, flag)
                walk(depth + 1, child, flag)
                builder.del_and(control, bit, flag)
            else:
                walk(depth + 1, child, bit)
            if not direction:
                builder.x(bit)

    walk(0, 0, True)
    for a, b, target in reversed(chain):
        builder.del_and(a, b, target)
    builder.bit_store(outcomes, False)
    for allocation in (path, workspace, outcomes):
        builder.free(allocation)
