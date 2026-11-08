"""Reduced virtual-template shift lookup with coherent age and enable inputs."""

from typing import Any


def shifted_template_xor(builder: Any, base: list[Any], age: Any,
                         enabled: Any, output: list[Any]) -> None:
    """XOR the in-range coefficients of z**(age+1)*base into output.

    All words and control wires are disjoint. This is a lookup primitive, not
    a complete BM round. Its caller must establish that enabled inputs have no
    nonzero coefficient beyond the output range.
    """
    if not base or len(base) != len(output):
        raise ValueError("template and output shapes must match")
    if not age or any(len(word) != 12 for word in (*base, *output)):
        raise ValueError("lookup requires an age register and 12-bit words")
    if len(base) - 1 > 1 << len(age):
        raise ValueError("age register cannot address the lookup range")
    flag = builder.alloc_qubits(1)[0]
    for current_age in range(len(base) - 1):
        builder.flip_if_equal(age, current_age, target=flag, control=enabled)
        for i in range(len(base) - current_age - 1):
            for source, target in zip(base[i], output[i + current_age + 1], strict=True):
                builder.ccx(flag, source, target)
        builder.flip_if_equal(age, current_age, target=flag, control=enabled)
    builder.free(flag)
