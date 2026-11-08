"""Offline evidence and pinned preflight checks for the roadmap controls."""

import io
import sys
import zipfile
from importlib import import_module
from pathlib import Path

import numpy as np
import pytest

from qcompile.artifacts import deterministic_npz
from qcompile.experiments import screen_outcome
from qcompile.io import read_json, sha256, write_json
from qcompile.worker import load_metric

SUBMISSIONS = (
    "ref,fileName,date,description,status,publicScore,privateScore\r\n"
    "174,submission.zip,2026-11-08T10:45:00Z,v3 920fcfba647e,SubmissionStatus.COMPLETE,1.57533,\r\n"
    "173,submission.zip,2026-11-08T09:45:00Z,v2 control,complete,1.37797,\r\n"
)


@pytest.fixture
def tools(monkeypatch, project_root):
    monkeypatch.syspath_prepend(str(project_root / "tools"))
    return import_module("kaggle_receipt"), import_module("dqi_development"), import_module("hybrid_preflight")


@pytest.fixture
def official(project_root):
    backend = project_root / "vendor/backend.json"
    if sys.platform != "linux" or not backend.is_file():
        pytest.skip("pinned Linux native backend required")
    metric = load_metric(read_json(backend))
    return metric, import_module("kickmix")


@pytest.mark.parametrize(
    ("trace", "flags", "expected"),
    [
        ([0.02, 0.017], {}, "go"),
        ([4.0] * 15 + [3.9, 3.8, 3.7, 3.6, 3.5], {"cap_reached": True}, "budget_limited"),
        ([4.0] * 20, {"cap_reached": True}, "no_go"),
        ([4.0] * 15 + [3.99] * 4 + [3.98], {}, "inconclusive"),
        ([], {"excluded_by_bound": True}, "no_go"),
        ([4.0], {"cap_reached": True, "optimizer_converged": False}, "budget_limited"),
    ],
)
def test_screen_outcome(trace, flags, expected):
    assert screen_outcome(trace, 0.0195, **flags) == expected


def test_bound_external_observation_and_immutable_ledger(tools, tmp_path):
    receipt, _, _ = tools
    archive = tmp_path / "submission.zip"
    archive.write_bytes(b"offline receipt fixture")
    certificate = tmp_path / "certificate.json"
    certificate.write_bytes(b"fixture certificate")
    preflight = tmp_path / "preflight.json"
    preflight.write_bytes(b"fixture preflight")
    digest = sha256(archive)
    message = receipt.submission_message("v3", digest)
    assert message == f"v3 {digest[:12]}"
    observed = receipt.read_submission(SUBMISSIONS, "v3 920fcfba647e")
    assert observed["kaggle_public_score"] == "1.57533"
    with pytest.raises(ValueError, match="matching the bound message"):
        receipt.read_submission(SUBMISSIONS, "v3 wrong")
    with pytest.raises(ValueError, match="no terminal score"):
        receipt.read_submission(SUBMISSIONS.replace("COMPLETE", "PENDING"), "v3 920fcfba647e")
    record = tmp_path / "prepared.json"
    write_json(record, {
        "zip_sha256": digest, "zip_bytes": archive.stat().st_size, "archive_class": "exact",
        "local_score": "1.5753293577", "local_certificate": {"path": str(certificate), "sha256": sha256(certificate)},
        "submission_message": message, "preflight_sha256": sha256(preflight),
    })
    bound = receipt.read_submission(SUBMISSIONS.replace("v3 920fcfba647e", message), message)
    write_json(tmp_path / "observed.json", {"prepared_sha256": sha256(record), **bound})
    ledger = tmp_path / "ledger"
    path = receipt.reconcile(tmp_path, ledger)
    assert read_json(path)["reconciled"] is True
    with pytest.raises(FileExistsError):
        receipt.reconcile(tmp_path, ledger)
    archive.write_bytes(b"different archive")
    with pytest.raises(ValueError, match="changed"):
        receipt.reconcile(tmp_path, ledger)


def test_bands_and_drift(tools, tmp_path):
    receipt, _, _ = tools
    exact = {"archive_class": "exact", "local_score": "1.5", "kaggle_public_score": "1.49999"}
    assert receipt.band_result(exact)["reconciled"] is True
    assert receipt.band_result({**exact, "kaggle_public_score": "1.499989"})["reconciled"] is False
    priced = {**exact, "archive_class": "failure_priced", "local_score_range": ("1.49", "1.51")}
    assert receipt.band_result({**priced, "kaggle_public_score": "1.48999"})["reconciled"] is True
    notebook = tmp_path / "metric.ipynb"
    notebook.write_bytes(b"different published notebook")
    with pytest.raises(ValueError, match="published metric drift"):
        receipt.require_metric(notebook)


def test_prepare_blocks_drift_before_writing_archive(tools, tmp_path, monkeypatch):
    receipt, _, _ = tools
    release = tmp_path / "release"
    release.mkdir()
    archive = release / "submission.zip"
    archive.write_bytes(b"unit test archive")
    write_json(release / "certificate.json", {
        "status": "locally_verified_awaiting_kaggle_acceptance", "two_builds_identical": True,
        "zip_sha256": sha256(archive), "predicted_aggregate_score": 1.5753293577,
        "verification": {
            "status": "passed", "tier": "full", "complete": True,
            "official_results": {"raw_verifier_results": {"dqi": {"circuit_sha256": receipt.REFERENCE_DQI}}},
        },
    })

    def fake_cli(_, *args):
        if args == ("--version",):
            return "Kaggle API 2.2.5"
        assert args[:3] == ("kernels", "pull", receipt.METRIC)
        notebook = Path(args[args.index("-p") + 1]) / "google-quantum-ai-metric.ipynb"
        notebook.write_bytes(b"changed metric")
        return ""

    monkeypatch.setattr(receipt, "run_cli", fake_cli)
    destination = tmp_path / "preparation"
    with pytest.raises(ValueError, match="published metric drift"):
        receipt.prepare(release, "v3", destination, tmp_path / "backend", tmp_path / "ledger", "kaggle")
    assert not destination.exists()


def test_full_development_schedule(tools):
    _, development, _ = tools
    config = {
        "trials": [{"role": "full_development", "salt": str(i) * 32} for i in range(5)],
        "confirmation_salt": "r" * 32, "workers": 2, "wall_seconds": 3600, "dqi_kind": "failure_priced",
    }
    assert development.validate_schedule(config)[1] == "r" * 32
    with pytest.raises(ValueError, match="five"):
        development.validate_schedule({**config, "trials": config["trials"][:4]})
    with pytest.raises(ValueError, match="invalid bounded"):
        development.validate_schedule({**config, "confirmation_salt": "1" * 32})


def test_score_range_is_derived_from_bound_campaign(tools, tmp_path):
    receipt, _, _ = tools
    digest = "c" * 64
    trials = [{"role": "full_development", "salt": str(i) * 32} for i in range(5)]
    write_json(tmp_path / "registration.json", {"config": {
        "trials": trials, "confirmation_salt": "r" * 32, "workers": 2, "wall_seconds": 3600,
        "dqi_kind": "failure_priced", "candidate": {"sha256": digest},
    }})
    write_json(tmp_path / "pricing.json", {
        "status": "priced", "failures_by_salt": list(range(5)), "k_max": 4, "priced_failures": 6,
    })
    for i, trial in enumerate(trials):
        lane = tmp_path / f"trial-{i:02}"
        write_json(lane / "trial.json", trial)
        write_json(lane / "cases.json", {"salt": trial["salt"], "shots": 102400})
        write_json(lane / "status.json", {"status": "complete"})
        write_json(lane / "candidate.json", {
            "status": "PASS", "circuit_sha256": digest, "verified_shots": 102400,
            "score": 1 + i, "value_errors": i, "phase_errors": 0,
        })
    costs = dict.fromkeys(("invsqrt", "dqi", "dfthcsos"), 1)
    certificate = {
        "artifact_hashes": {"dqi.kmb": digest},
        "supporting_evidence": {"accepted_reference_costs": costs},
        "verification": {"official_results": {"costs": costs, "raw_verifier_results": {"dqi": {
            "circuit_sha256": digest, "verified_shots": 102400, "num_qubits": 10, "toffoli_count": 20,
        }}}},
    }
    observed = receipt.matched_score_range(tmp_path, certificate)
    assert list(map(float, observed["local_score_range"])) == pytest.approx([5 ** (-1 / 3), 1])
    certificate["artifact_hashes"]["dqi.kmb"] = "d" * 64
    with pytest.raises(ValueError, match="different DQI artifact"):
        receipt.matched_score_range(tmp_path, certificate)


@pytest.mark.official
def test_pinned_conservative_pricing(tools, official):
    _, development, _ = tools
    api = import_module("dqi.verify_submission_dqi")
    trials = [{
        "value_errors": 0, "phase_errors": 0, "verified_shots": 102400,
        "log2_delta": api.DEFAULT_LOG2_DELTA, "num_qubits": 10, "toffoli_count": 20,
    } for _ in range(5)]
    assert api.repetition_overhead(api.clopper_pearson_upper_bound(0, 102400, api.DEFAULT_LOG2_DELTA)) == (
        pytest.approx(1.19126, abs=0.00002)
    )
    zero = development.conservative_price(trials, api)
    assert zero["priced_failures"] == 2
    trials[-1].update(value_errors=5, phase_errors=7)
    stressed = development.conservative_price(trials, api)
    assert stressed["priced_failures"] == 14
    assert stressed["repetition_factor"] == pytest.approx(1.24, abs=0.0001)


@pytest.mark.official
@pytest.mark.parametrize(("bad_case", "message"), [
    ("version", "format 1.0"),
    ("endianness", "plain number type"),
    ("integer", "plain number type"),
    ("physical_size", "physical NPZ exceeds 64 MiB"),
])
def test_preflight_npz_boundaries(tools, official, tmp_path, bad_case, message):
    _, _, preflight = tools
    metric, _ = official
    path = tmp_path / "submission.npz"
    arrays = {
        "U": np.zeros((1, 1, 76)), "W": np.zeros((1, 1, 1)), "H2_I": np.zeros((1, 1)),
        "H1_I": np.array(0.), "Hsym_lower": np.zeros(2926), "tree_edges": np.zeros((75, 2), dtype=np.int64),
    }
    if bad_case == "physical_size":
        with path.open("wb") as stream:
            stream.truncate(2**26 + 1)
    else:
        canonical = tmp_path / "valid.npz"
        deterministic_npz(canonical, arrays)
        arr = arrays["U"]
        if bad_case == "endianness":
            arr = arr.astype(">f8")
        elif bad_case == "integer":
            arr = arr.astype(np.int64)
        buffer = io.BytesIO()
        np.lib.format.write_array(buffer, arr, version=(2, 0) if bad_case == "version" else (1, 0))
        with zipfile.ZipFile(canonical) as good, zipfile.ZipFile(path, "x") as mutated:
            for name in good.namelist():
                mutated.writestr(name, buffer.getvalue() if name == "U.npy" else good.read(name))
    origin = "local_guard" if bad_case == "physical_size" else "pinned_metric"
    with pytest.raises(ValueError, match=f"{origin}.*{message}"):
        preflight.factorization_shape(path, metric["read_npz"])


@pytest.mark.official
@pytest.mark.parametrize(("bad_case", "message"), [
    ("id", "qubit or bit id 699050"),
    ("register", "register"),
    ("dqi_rotation", "DQI does not permit Z_POW"),
    ("angle_rotation", "Z_POW rotations are not allowed"),
    ("angle_width", "exceeds 128-qubit cap"),
])
def test_preflight_circuit_boundaries(tools, official, tmp_path, bad_case, message):
    _, _, preflight = tools
    metric, km = official
    builder = km.CircuitBuilder()
    if bad_case.startswith("angle"):
        circuits = import_module("dfthcsos.scoreinfra.circuits")
        chemistry = import_module("dfthcsos.verify")
        selection = builder.create_quantum_register(7, name=circuits.SELECTION_REGISTER)
        builder.create_quantum_register(8, name=circuits.word_register(0))
        if bad_case == "angle_rotation":
            builder.z_pow(selection[0], 0.125)
        else:
            workspace = builder.alloc_qubits(114)
            builder.x(workspace[-1])
        path = tmp_path / "angle_k_0.kmb"
        builder.finish_circuit().to_file(path, format="kmb")
        with pytest.raises(ValueError, match=f"pinned_metric.*{message}"):
            preflight.angle_summary(tmp_path, 1, 1, 1, metric["read_circuit"], chemistry, circuits)
    else:
        invsqrt = import_module("invsqrt.verify_submission_invsqrt")
        dqi = import_module("dqi.verify_submission_dqi")
        dqi_spec = dqi.ProblemSpecDQI.benchmark_instance(m=4, n=2, degree=12)
        if bad_case == "id":
            kmb = tmp_path / "invsqrt.kmb"
            kmx = tmp_path / "source.kmx"
            kmx.write_text("X q699050\n")
            km.Circuit.from_file(kmx, format="kmx").to_file(kmb, format="kmb")
        elif bad_case == "dqi_rotation":
            kmb = tmp_path / "dqi.kmb"
            for i in range(dqi_spec.n):
                register = builder.create_quantum_register(12, name=f"S{i}")
                builder.z_pow(register[0], 0.125)
            for i in range(dqi_spec.m):
                builder.create_classical_register(12, name=f"E{i}")
            builder.finish_circuit().to_file(kmb, format="kmb")
        else:
            kmb = tmp_path / "invsqrt.kmb"
            builder.create_quantum_register(22, name="wrong")
            builder.finish_circuit().to_file(kmb, format="kmb")
        with pytest.raises(ValueError, match=f"pinned_metric.*{message}"):
            if bad_case == "dqi_rotation":
                preflight.circuit_summary(kmb, 6, metric["read_circuit"], dqi.validate_registers, dqi_spec)
            else:
                spec = invsqrt.ProblemSpecInvSqrt.for_n_p(10)
                preflight.circuit_summary(kmb, 1, metric["read_circuit"], invsqrt.validate_registers, spec)


@pytest.mark.official
@pytest.mark.parametrize(("extra", "message"), [
    ("dfthcsos/angle_k_2.kmb", "angle indices must be contiguous"),
    ("dfthcsos/angle_k_0.kmb", "duplicate archive member"),
    ("unexpected.kmb", "canonical binary circuits"),
])
def test_preflight_zip_layout(tools, official, project_root, tmp_path, extra, message):
    _, _, preflight = tools
    archive = tmp_path / "malformed.zip"
    with zipfile.ZipFile(archive, "x") as output:
        for name in ("invsqrt.kmb", "dqi.kmb", "dfthcsos/submission.npz", "dfthcsos/angle_k_0.kmb"):
            output.writestr(name, b"fixture")
        if extra == "dfthcsos/angle_k_0.kmb":
            with pytest.warns(UserWarning, match="Duplicate name"):
                output.writestr(extra, b"fixture")
        else:
            output.writestr(extra, b"fixture")
    with pytest.raises(ValueError, match=f"local_guard.*{message}"):
        preflight.preflight(archive, project_root / "vendor/backend.json", tmp_path / "check")
