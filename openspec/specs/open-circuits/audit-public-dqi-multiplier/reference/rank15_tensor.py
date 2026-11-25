"""Evidence: rank-15 symmetric GF(64) tensor in the pinned subfield basis.

Run from the repository root: python reference/rank15_tensor.py
It solves the output words for the registered vectors and runs the
repository's exhaustive GF(64) verifier.
"""
import sys
sys.path.insert(0, "src")
from qcompile.dqi.field import GF4096
from qcompile.dqi.tower import tower, linear
from qcompile.dqi import bilinear_search

VECTORS = (6, 8, 16, 17, 25, 26, 27, 28, 30, 35, 39, 46, 48, 51, 60)
F = GF4096()
basis = tower().basis[:6]
mapped = [linear(basis, i) for i in range(64)]
coord = {v: i for i, v in enumerate(mapped)}
pairs = [(i, j) for i in range(6) for j in range(i, 6)]
def symvec(bit):
    return sum(1 << p for p, (i, j) in enumerate(pairs) if bit(i, j))
prod = [[coord[F.mul(mapped[1 << i], mapped[1 << j])] for j in range(6)] for i in range(6)]
targets = [symvec(lambda i, j, k=k: prod[i][j] >> k & 1) for k in range(6)]
outers = [symvec(lambda i, j, a=a: (a >> i & 1) & (a >> j & 1)) for a in VECTORS]
rows = []
for n, v in enumerate(outers):
    t = 1 << n
    for bv, bt in rows:
        if v ^ bv < v:
            v, t = v ^ bv, t ^ bt
    if v:
        rows.append((v, t))
def express(x):
    t = 0
    for bv, bt in sorted(rows, key=lambda r: -r[0]):
        if x ^ bv < x:
            x, t = x ^ bv, t ^ bt
    assert x == 0, "target outside span"
    return t
coef = [express(x) for x in targets]
terms = tuple((a, a, sum(1 << k for k in range(6) if coef[k] >> n & 1)) for n, a in enumerate(VECTORS))
print(terms)
bilinear_search.verify(terms, exhaustive=True)
print("rank", len(terms), "exhaustive GF(64) verification passed")
