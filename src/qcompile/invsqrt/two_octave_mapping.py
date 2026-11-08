"""In-place two-octave address selection with reversible controlled swaps."""

from typing import Any


def permute_address(builder: Any, x: Any, segment_bits: int, *, inverse: bool = False) -> None:
    """Rotate the address window left by one bit exactly for the upper octave.

    The original low bit moves to the high end of the window, allowing the
    additional upper-octave arithmetic row to recover it without an address
    copy. Calling with ``inverse=True`` restores every input qubit.
    """
    low = len(x) - 2 - segment_bits
    if segment_bits < 1 or low < 1:
        raise ValueError("two-octave window does not fit")
    flag = x[-1]
    positions = reversed(range(segment_bits)) if inverse else range(segment_bits)
    for i in positions:
        builder.cswap(flag, x[low + i], x[low + i + 1])
