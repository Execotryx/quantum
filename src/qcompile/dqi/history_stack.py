"""Tagged routed-BM history with a persistent failure counter."""

from typing import Any


def _nonzero(builder: Any, word: Any, flag: Any) -> None:
    builder.x(flag)
    builder.flip_if_equal(word, 0, target=flag)


def _match(builder: Any, word: Any, value: int, control: Any, target: Any) -> None:
    flag = builder.alloc_qubits(1)[0]
    builder.flip_if_equal(word, value, target=flag)
    builder.ccx(flag, control, target)
    builder.flip_if_equal(word, value, target=flag)
    builder.free(flag)


class HistoryStack:
    """Store tagged retains, leaving overflowed inputs marked by a nonzero count."""

    def __init__(self, builder: Any, depth: int) -> None:
        if depth not in (1, 2, 3):
            raise ValueError("history depth must be 1, 2 or 3")
        self.depth = depth
        self.entries = [(builder.alloc_qubits(12), builder.alloc_qubits(7), builder.alloc_qubits(1)[0])
                        for _ in range(depth)]
        self.occupancy = builder.alloc_qubits(2)
        self.transfer = builder.alloc_qubits(12)
        self.overflows = builder.alloc_qubits(7)

    def push(self, builder: Any, r: int) -> None:
        if not 1 <= r <= 70:
            raise ValueError("history tag outside the round range")
        p, overflow, *selectors = builder.alloc_qubits(self.depth + 2)
        _nonzero(builder, self.transfer, p)
        _match(builder, self.occupancy, self.depth, p, overflow)
        for index, ((data, tag, valid), select) in enumerate(zip(self.entries, selectors, strict=True)):
            _match(builder, self.occupancy, index, p, select)
            for source, target in zip(self.transfer, data, strict=True):
                builder.ccx(select, source, target)
                builder.ccx(select, target, source)
            builder.gf2_iadd(r, target=tag, control=select)
            builder.cx(select, valid)
        for select in selectors:
            builder.iadd(1, target=self.occupancy, control=select)
        for (_, tag, valid), select in zip(self.entries, selectors, strict=True):
            _match(builder, tag, r, valid, select)
        builder.iadd(1, target=self.overflows, control=overflow)
        nonzero = builder.alloc_qubits(1)[0]
        _nonzero(builder, self.transfer, nonzero)
        _match(builder, self.occupancy, self.depth, nonzero, overflow)
        builder.cx(nonzero, p)
        _nonzero(builder, self.transfer, nonzero)
        for _, tag, valid in self.entries:
            _match(builder, tag, r, valid, p)
        builder.free(nonzero)
        for flag in (p, overflow, *selectors):
            builder.free(flag)

    def pop(self, builder: Any, r: int) -> None:
        if not 1 <= r <= 70:
            raise ValueError("history tag outside the round range")
        clean, tag_match, nonzero, *selectors = builder.alloc_qubits(self.depth + 3)
        builder.flip_if_equal(self.overflows, 0, target=clean)
        for (data, tag, valid), select in zip(self.entries, selectors, strict=True):
            _match(builder, tag, r, valid, tag_match)
            builder.ccx(clean, tag_match, select)
            _match(builder, tag, r, valid, tag_match)
            for source, target in zip(data, self.transfer, strict=True):
                builder.ccx(select, source, target)
                builder.ccx(select, target, source)
            builder.gf2_iadd(r, target=tag, control=select)
            builder.cx(select, valid)
        for select in selectors:
            builder.isub(1, target=self.occupancy, control=select)
        # Overflowed inputs may carry a dirty transfer word even without a pop.
        # Use the same eligibility predicate for data movement and flag clearing.
        _nonzero(builder, self.transfer, nonzero)
        builder.init_and(clean, nonzero, tag_match)
        for index, select in enumerate(selectors):
            _match(builder, self.occupancy, index, tag_match, select)
        builder.del_and(clean, nonzero, tag_match)
        _nonzero(builder, self.transfer, nonzero)
        builder.flip_if_equal(self.overflows, 0, target=clean)
        for flag in (clean, tag_match, nonzero, *selectors):
            builder.free(flag)

