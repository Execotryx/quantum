"""A width-aware controlled row with an on-demand gated operand bit."""

from typing import Any


def add_row(builder: Any, inverse: bool, control: Any, terms: list[tuple[Any, int]],
            target: Any, scratch: Any, *, subtract: bool = False) -> None:
    """Ripple using scratch as carry bits and a single measured gated bit.

    The target width must fit in scratch. Carry bits are uncomputed before the
    corresponding target bit is updated, preserving their original controls.
    Subtraction follows from complementing the target before and after addition.
    """
    if not terms:
        return
    low = min(column for _, column in terms)
    lane = target[low:]
    if len(scratch) < len(lane):
        raise ValueError("row requires a carry lane and one temporary bit")
    sources = {column - low: source for source, column in terms}
    if len(sources) != len(terms) or any(column < 0 or column >= len(lane) for column in sources):
        raise ValueError("invalid row columns")
    carries = scratch[:len(lane) - 1]
    gated = scratch[len(lane) - 1]
    if inverse != subtract:
        builder.x(lane)

    def carry(column: int) -> None:
        bit = lane[column]
        source = sources.get(column)
        incoming = carries[column - 1] if column else None
        if source is not None:
            builder.init_and(control, source, gated)
            if incoming is not None:
                builder.cx(incoming, bit)
            builder.ccx(gated, bit, carries[column])
            if incoming is not None:
                builder.cx(incoming, bit)
            builder.del_and(control, source, gated)
        if incoming is not None:
            builder.ccx(bit, incoming, carries[column])

    for column in range(len(lane) - 1):
        carry(column)
    for column in reversed(range(len(lane))):
        if column < len(lane) - 1:
            carry(column)
        if column:
            builder.cx(carries[column - 1], lane[column])
        source = sources.get(column)
        if source is not None:
            builder.init_and(control, source, gated)
            builder.cx(gated, lane[column])
            builder.del_and(control, source, gated)
    if inverse != subtract:
        builder.x(lane)
