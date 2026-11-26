from importlib import import_module
from io import BytesIO


def test_live_product_rewrite_preserves_guards_and_rejects_unknown_control(project_root, monkeypatch):
    monkeypatch.syspath_prepend(str(project_root / "tools"))
    rewrite = import_module("dqi_live_products").rewrite
    source = BytesIO(
        b"HMR q2 b0\nCCX q0 q1 q2\nCCX q1 q0 q3 if b1\nCCZ q0 q1 q2 if b2\n"
        b"X q2 if b3\nCCX q0 q1 q4\n"
        b"HMR q5 b4 if b5\nCCX q1 q5 q6\n"
    )
    output = BytesIO()
    assert rewrite(source, output) == {
        "product_gates": 5, "live_products": 2,
        "repeated_products": 1, "disjoint_repeated_product_pairs": 1,
    }
    assert output.getvalue() == (
        b"HMR q2 b0\nCCX q0 q1 q2\nCX q2 q3 if b1\nZ q2 if b2\n"
        b"X q2 if b3\nCCX q0 q1 q4\n"
        b"HMR q5 b4 if b5\nCCX q1 q5 q6\n"
    )


def test_live_product_rewrite_handles_constant_product_and_nested_reset(project_root, monkeypatch):
    monkeypatch.syspath_prepend(str(project_root / "tools"))
    rewrite = import_module("dqi_live_products").rewrite
    source = BytesIO(
        b"HMR q2 b0\nCCX q0 q2 q3\nX q2\nCX q2 q4\n"
        b"PUSH_CONDITION if b1\nHMR q2 b2\nPOP_CONDITION\nCCX q0 q2 q3\n"
    )
    output = BytesIO()
    assert rewrite(source, output) == {"product_gates": 2, "zero_products": 1}
    assert output.getvalue() == source.getvalue().replace(b"CCX q0 q2 q3\n", b"", 1)
