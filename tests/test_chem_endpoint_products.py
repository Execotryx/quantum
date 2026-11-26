from importlib import import_module

import numpy as np
import pytest


def test_endpoint_proof_replaces_only_equal_product(project_root, monkeypatch):
    monkeypatch.syspath_prepend(str(project_root / "tools"))
    rewrite = import_module("chem_endpoint_products").rewrite
    header = [
        "APPEND_TO_REGISTER q0 r0\n", "APPEND_TO_REGISTER q1 r0\n", 'REGISTER r0 "selection"\n',
        "APPEND_TO_REGISTER q2 r1\n", 'REGISTER r1 "word_0"\n',
    ]
    words = np.array([[0], [0], [0], [1]], dtype=np.int64)
    operations = ["CCX q0 q1 q3\n", "CCX q1 q0 q2\n", "HMR q3 b0\n", "CZ q0 q1 if b0\n"]
    actual, record = rewrite(header + operations, words, 0)
    assert actual == header + [operations[0], "CX q3 q2\n", *operations[2:]]
    assert record == {"eliminated": 0, "replaced_by_clifford": 1, "endpoint_rows": 8}
    with pytest.raises(ValueError, match="endpoint"):
        rewrite(header + operations, np.zeros((4, 1), dtype=np.int64), 0)
