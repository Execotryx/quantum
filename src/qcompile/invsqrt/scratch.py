"""Conservative KMX value identities across all inputs and measurement outcomes."""

from collections import defaultdict


class ScratchProof:
    """Represent XORs exactly and intern nonlinear products as independent atoms."""

    def __init__(self, input_width: int):
        self.next_atom = 1
        self.products: dict[tuple[int, ...], int] = {}
        self.values: dict[str, int] = defaultdict(int)
        for wire in range(input_width):
            self.values[f"q{wire}"] = self.atom()
        self.conditions = [1]

    def atom(self) -> int:
        value = 1 << self.next_atom
        self.next_atom += 1
        return value

    def product(self, *terms: int) -> int:
        factors = set(terms)
        if 0 in factors or any(term ^ 1 in factors for term in factors):
            return 0
        factors.discard(1)
        if not factors:
            return 1
        if len(factors) == 1:
            return factors.pop()
        key = tuple(sorted(factors))
        if key not in self.products:
            self.products[key] = self.atom()
        return self.products[key]

    def step(self, parts: list[str]) -> bool:
        """Apply the value action and report whether a phase or reversible gate is identity."""
        op, *operands = parts
        state = self.values
        enabled = self.conditions[-1]
        if operands[-2:-1] == ["if"]:
            enabled = self.product(enabled, state[operands[-1]])
            operands = operands[:-2]
        if op == "PUSH_CONDITION":
            self.conditions.append(enabled)
        elif op == "POP_CONDITION":
            self.conditions.pop()
        elif op in {"X", "CX", "CCX", "BIT_INVERT"}:
            target = operands[-1]
            delta = self.product(enabled, *(state[key] for key in operands[:-1]))
            state[target] ^= delta
            return delta == 0
        elif op in {"SWAP", "CSWAP"}:
            left, right = operands[-2:]
            delta = self.product(enabled, state[left] ^ state[right], *(state[key] for key in operands[:-2]))
            state[left] ^= delta
            state[right] ^= delta
            return delta == 0
        elif op in {"Z", "CZ", "CCZ", "Z_POW", "NEG"}:
            if op == "Z_POW":
                operands = operands[:1]
            return self.product(enabled, *(state[key] for key in operands)) == 0
        elif op in {"HMR", "R", "BIT_STORE0", "BIT_STORE1"}:
            target = operands[0]
            desired = int(op == "BIT_STORE1")
            state[target] ^= self.product(enabled, state[target] ^ desired)
            if op == "HMR":
                bit = operands[1]
                state[bit] ^= self.product(enabled, state[bit] ^ self.atom())
        else:
            raise ValueError(f"Unsupported symbolic KMX instruction {op}")
        return False

    def shared_product(self, parts: list[str], wires: range) -> list[str] | None:
        """Use an already live predicate instead of computing it again."""
        if parts[0] not in {"CCX", "CCZ"}:
            return None
        left, right, target = parts[1:4]
        product = self.product(self.values[left], self.values[right])
        if product in (0, 1):
            return None
        if parts[0] == "CCZ" and self.values[target] == product:
            return ["Z", target, *parts[4:]]
        for index in wires:
            wire = f"q{index}"
            if wire != target and self.values[wire] == product:
                return [("CX" if parts[0] == "CCX" else "CZ"), wire, target, *parts[4:]]
        return None
