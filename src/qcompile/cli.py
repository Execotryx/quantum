"""Explicit local operator commands; there is deliberately no remote-submit command."""

import argparse
import subprocess
import sys
import time
from pathlib import Path

from .artifacts import manifest
from .assets import acquire_metric, pin_backend
from .contract import load_contract
from .environment import capture
from .errors import ValidationError
from .experiments import CandidateStore, validate_budget
from .invsqrt.fixed import polynomial_model
from .io import identity, read_json, sha256, write_json
from .official import verify_candidate
from .reference.invsqrt import scan
from .release import certify_release, package_release


def parser():
    result = argparse.ArgumentParser(prog="qcompile")
    result.add_argument("--root", type=Path, default=Path.cwd(), help="project root; defaults to cwd")
    groups = result.add_subparsers(dest="group", required=True)
    contract = groups.add_parser("contract").add_subparsers(dest="action", required=True)
    validate = contract.add_parser("validate")
    validate.add_argument("--contract", type=Path, default=Path("contracts/contract.json"))
    assets = groups.add_parser("assets").add_subparsers(dest="action", required=True)
    acquire = assets.add_parser("acquire-metric")
    acquire.add_argument("--output", type=Path, default=Path("vendor/metric/google-quantum-ai-metric.ipynb"))
    pin = assets.add_parser("pin-backend")
    for name in ("metric", "verifiers", "kickmix", "output"):
        pin.add_argument("--" + name, required=True, type=Path)
    baseline = groups.add_parser("baseline").add_subparsers(dest="action", required=True)
    base_verify = baseline.add_parser("verify")
    base_verify.add_argument("--artifact-dir", type=Path, required=True)
    _verification_options(base_verify)
    test = groups.add_parser("test")
    test.add_argument("--tier", choices=["unit", "extended", "official"], default="unit")
    experiment = groups.add_parser("experiment").add_subparsers(dest="action", required=True)
    run = experiment.add_parser("run")
    run.add_argument("--config", type=Path, required=True)
    candidate = groups.add_parser("candidate").add_subparsers(dest="action", required=True)
    register = candidate.add_parser("register")
    register.add_argument("--selection", type=Path, required=True)
    status = candidate.add_parser("status")
    status.add_argument("--id", required=True)
    advance = candidate.add_parser("advance")
    advance.add_argument("--id", required=True)
    advance.add_argument("--state", required=True)
    advance.add_argument("--evidence", type=Path, required=True)
    for name in ("verify", "confirm"):
        command = candidate.add_parser(name)
        command.add_argument("--id", required=True)
        _verification_options(command)
        if name == "confirm":
            command.add_argument("--protocol", type=Path, required=True)
    release = groups.add_parser("release").add_subparsers(dest="action", required=True)
    build = release.add_parser("build")
    build.add_argument("--selection", type=Path, required=True)
    build.add_argument("--output", type=Path, required=True)
    verify = release.add_parser("verify")
    verify.add_argument("--release", type=Path, required=True)
    verify.add_argument("--supporting-evidence", type=Path, required=True)
    _verification_options(verify)
    return result


def _verification_options(command):
    command.add_argument("--backend", required=True, type=Path)
    command.add_argument("--tier", choices=["smoke", "full"], default="full")
    command.add_argument("--seed-policy", required=True, type=Path)
    command.add_argument("--output", type=Path, required=True)
    command.add_argument("--timeout", type=int, default=86400)


def _candidate_run(args, root, contract):
    store = CandidateStore(root / "runs/candidates")
    record = store.get(args.id)
    contract.require_ready(root)
    seed = read_json(args.seed_policy)
    if args.action == "confirm":
        protocol = read_json(args.protocol)
        if protocol["seed_policy"] != seed or args.tier != "full":
            raise ValidationError("confirmation must use full verification and its registered seed policy")
        store.register_confirmation(args.id, protocol)
    report = verify_candidate(
        record["artifacts"],
        contract,
        args.tier,
        seed,
        read_json(args.backend),
        args.output,
        timeout=args.timeout,
    )
    if args.action == "confirm":
        # A G0 mapping from actual verifier return fields is required. No invented counters.
        observed = report.get("official_results", {}).get("confirmation_observed")
        if observed is None:
            raise ValidationError(
                "official metric does not export registered sample counters; "
                "raw evidence retained, confirmation stays incomplete"
            )
        return store.finish_confirmation(args.id, {**report, "observed": observed})
    return report


def run_experiment(config, contract, root):
    validate_budget(config)
    if config.get("kind") != "independent_numerical_diagnostic":
        raise ValidationError("circuit/search experiments require the unresolved G0/G1/opportunity gates")
    run_id = identity({"config": config, "contract_hash": contract.hash})
    directory = root / "runs" / run_id
    directory.mkdir(parents=True, exist_ok=False)
    registration = {"config": config, "contract_hash": contract.hash, "environment": capture(root)}
    write_json(directory / "registration.json", registration)
    started = time.monotonic()
    try:
        evaluate = polynomial_model(config["model"])
        # A diagnostic has no official compatibility or improvement claim.
        budget = config["budget"]

        def progress(completed, expected):
            if time.monotonic() - started > min(budget["max_wall_seconds"], budget["max_compute_seconds"]):
                raise ValidationError("registered diagnostic time budget exhausted")
            print(f"numerical scan: {completed}/{expected}", file=sys.stderr)

        report = scan(evaluate, first=config.get("first", 1), last=config["last"], progress=progress)
        write_json(directory / "numerical.json", report)
        result = {
            "status": "numerical_diagnostic_completed",
            "report_sha256": sha256(directory / "numerical.json"),
            "official_compatible": False,
            "run_id": run_id,
        }
    except Exception as error:
        write_json(
            directory / "failure.json",
            {"status": "failed", "error": str(error), "elapsed_seconds": time.monotonic() - started},
        )
        raise
    write_json(directory / "result.json", result)
    return result


def dispatch(args):
    root = args.root.resolve()
    if args.group == "test":
        flags = ["-m", "not slow and not official"] if args.tier == "unit" else ["-m", "not official"]
        if args.tier == "official":
            raise ValidationError("use baseline verify --tier full with pinned assets for official execution")
        result = subprocess.run([sys.executable, "-m", "pytest", *flags], cwd=root, check=False)
        return {"exit_code": result.returncode}
    contract = load_contract(root / "contracts/contract.json")
    if args.group == "contract":
        contract = load_contract(root / args.contract)
        blockers = contract.blockers(root)
        return {
            "contract_hash": contract.hash,
            "status": "blocked" if blockers else "ready",
            "blockers": blockers,
            "exit_code": 2 if blockers else 0,
        }
    if args.group == "assets":
        if args.action == "acquire-metric":
            source = read_json(root / "contracts/sources.lock.json")["sources"]["metric"]
            return acquire_metric(root / args.output, source["sha256"], source["version"])
        return pin_backend(args.metric, args.verifiers, args.kickmix, args.output)
    if args.group == "baseline":
        artifacts = manifest(
            args.artifact_dir,
            origin="retained_reference",
            provenance="unmodified acquired official reference; acceptance pending this run",
        )
        return verify_candidate(
            artifacts,
            contract,
            args.tier,
            read_json(args.seed_policy),
            read_json(args.backend),
            args.output,
            timeout=args.timeout,
        )
    if args.group == "experiment":
        return run_experiment(read_json(args.config), contract, root)
    if args.group == "candidate":
        store = CandidateStore(root / "runs/candidates")
        if args.action == "register":
            selection = read_json(args.selection)
            return store.create(
                selection["config"], contract.hash, selection["artifacts"], capture(root), selection["claims"]
            )
        if args.action == "status":
            return store.get(args.id)
        if args.action == "advance":
            if args.state in ("full_local_passed", "release_selected", "remote_accepted"):
                contract.require_ready(root)
            return store.advance(args.id, args.state, read_json(args.evidence))
        return _candidate_run(args, root, contract)
    if args.group == "release":
        contract.require_ready(root)
        if args.action == "build":
            selection = read_json(args.selection)
            selection["candidate"] = CandidateStore(root / "runs/candidates").get(selection["candidate_id"])
            selection["project_root"] = str(root)
            return package_release(selection, contract, args.output, source_environment=capture(root))
        if args.tier != "full":
            raise ValidationError("release verification requires the full tier")
        record = read_json(args.release / "release.json")
        if sha256(args.release / "submission.zip") != record["zip_sha256"]:
            raise ValidationError("release ZIP changed")
        from .artifacts import extract_archive

        # Re-extract the exact frozen ZIP at verification time; do not trust a prior directory.
        directory = args.release / ("verify-extracted-" + str(time.time_ns()))
        extract_archive(args.release / "submission.zip", directory, expected=record["artifact_hashes"])
        artifacts = record["candidate"]["artifacts"]
        artifacts = {
            name: {**item, "path": str((directory / name).resolve())} for name, item in artifacts.items()
        }
        report = verify_candidate(
            artifacts,
            contract,
            "full",
            read_json(args.seed_policy),
            read_json(args.backend),
            args.output,
            timeout=args.timeout,
        )
        certificate = certify_release(
            record, report, contract, supporting_evidence=read_json(args.supporting_evidence)
        )
        write_json(args.release / "certificate.json", certificate)
        return certificate
    raise ValidationError("unknown command")


def main():
    args = parser().parse_args()
    try:
        result = dispatch(args)
        import json

        print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
        code = result.get("exit_code", 0)
        if result.get("status") in ("failed", "incomplete"):
            code = 1
        return code
    except (ValidationError, OSError, KeyError, TypeError, subprocess.SubprocessError) as error:
        print(f"qcompile: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
