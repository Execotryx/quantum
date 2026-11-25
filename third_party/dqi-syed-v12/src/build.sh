#!/usr/bin/env bash
# Copyright 2026 Syed Asad Ali. Licensed under Apache-2.0.
# Credits: Syed Asad Ali, working with a team of AI agents (GPT-6 Astra Pro, Gemini 4 Argon, Fable 5.2, Mythos 5.2 and Opus 5.5), with Claude Science supporting the research.
#
# Rebuild dqi.kmb from source.
#   bash build.sh ENGINE_DIR VERIFIERS_DIR OUT_DIR
# ENGINE_DIR    the competition's kickmix/ folder (holds the Linux kickmix.so)
# VERIFIERS_DIR the competition's verifiers/ folder (holds dqi/verify_submission_dqi.py)
# OUT_DIR       where dqi.kmb is written
# Environment: PY (default python3; must be CPython 3.13, not -O, with numpy),
#              WORK (writable scratch dir; default a new temp dir),
#              KEEP_WORK=1 keeps the copied source tree after success,
#              MAC_ENGINE (macOS test only: path to kickmix.cpython-313-darwin.so).
# The host files (kickmix.so, verify_submission_dqi.py) are copied in at run time;
# they are not part of this folder.
set -euo pipefail

EXPECTED_SHA=7cbe8ecf6f6e9743529b574f019504bb1712ce06fbb570c719ce9d9e2c914cd9
EXPECTED_BYTES=455590024
ENGINE_SHA=c66b3216c4029e0cdfd09054306aa0feadf53ab2f50c1164e37f752874e5005e
VERIFIER_SHA=f14274bc0943fb9769ddb01131be6063191a15009fe1caf1d4bdd9fd25194e65

die() { echo "build.sh: ERROR: $*" >&2; exit 1; }

[ "$#" -eq 3 ] || die "usage: bash build.sh ENGINE_DIR VERIFIERS_DIR OUT_DIR"
ENGINE_DIR=$1
VERIFIERS_DIR=$2
OUT_DIR=$3
PY=${PY:-python3}
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

# The pinned sources require ordinary (non-optimized) Python 3.13.
unset PYTHONOPTIMIZE || true
export PYTHONDONTWRITEBYTECODE=1

"$PY" -c 'import sys; sys.exit(0 if (sys.implementation.name == "cpython" and sys.version_info[:2] == (3, 13) and __debug__) else 1)' \
  || die "PY=$PY must be CPython 3.13 without optimization"
"$PY" -c 'import numpy' || die "numpy is required"

sha256() {
  "$PY" -c 'import hashlib, sys
h = hashlib.sha256()
with open(sys.argv[1], "rb") as f:
    for block in iter(lambda: f.read(1 << 20), b""):
        h.update(block)
print(h.hexdigest())' "$1"
}

[ -f "$ENGINE_DIR/kickmix.so" ] || die "missing $ENGINE_DIR/kickmix.so"
[ -f "$VERIFIERS_DIR/dqi/verify_submission_dqi.py" ] || die "missing $VERIFIERS_DIR/dqi/verify_submission_dqi.py"
[ -d "$HERE/src/controller_work" ] || die "missing $HERE/src/controller_work"

if [ -z "${WORK:-}" ]; then
  WORK=$(mktemp -d "${TMPDIR:-/tmp}/dqi_work.XXXXXX")
fi
mkdir -p "$WORK"
RUN=$(mktemp -d "$WORK/dqi_build.XXXXXX")
ROOT=$RUN/root
mkdir -p "$ROOT"
cp -R "$HERE/src/." "$ROOT/"
chmod -R u+w "$ROOT"

# Host files go where the pinned sources expect them (their hashes are pinned).
OFFICIAL=$ROOT/pro1_controller_bundle/1_task/official
mkdir -p "$OFFICIAL" "$ROOT/pro1_controller_bundle/1_task/verifiers/dqi"
cp "$ENGINE_DIR/kickmix.so" "$OFFICIAL/kickmix.so"
cp "$VERIFIERS_DIR/dqi/verify_submission_dqi.py" "$ROOT/pro1_controller_bundle/1_task/verifiers/dqi/verify_submission_dqi.py"
[ "$(sha256 "$OFFICIAL/kickmix.so")" = "$ENGINE_SHA" ] || die "kickmix.so is not the official engine (sha256 $ENGINE_SHA)"
[ "$(sha256 "$ROOT/pro1_controller_bundle/1_task/verifiers/dqi/verify_submission_dqi.py")" = "$VERIFIER_SHA" ] \
  || die "verify_submission_dqi.py is not the official verifier (sha256 $VERIFIER_SHA)"

# No baked-in absolute path needs relocating: every pinned path is relative to $ROOT.
OUT_KMB=$RUN/out/dqi.kmb
LOGS=$RUN/build-v6
START=$SECONDS
echo "build.sh: building dqi.kmb in $RUN (about 3 minutes)"
case "$(uname -s)" in
  Linux)
    # The package's own entry point: memory guard (guard_wait.py) + build_v7.py.
    set +e
    (cd "$ROOT" && "$PY" controller_work/after_v3/integration_v7/gen_dqi.py \
        --output "$OUT_KMB" --log-directory "$LOGS")
    STATUS=$?
    set -e
    ;;
  Darwin)
    # macOS test only: the guard reads /proc, so start build_v7.py directly with
    # a macOS build of the engine placed beside the Linux kickmix.so.
    [ -n "${MAC_ENGINE:-}" ] && [ -f "$MAC_ENGINE" ] || die "on macOS set MAC_ENGINE to kickmix.cpython-313-darwin.so"
    SUFFIX=$("$PY" -c 'import importlib.machinery as m; print(m.EXTENSION_SUFFIXES[0])')
    cp "$MAC_ENGINE" "$OFFICIAL/kickmix$SUFFIX"
    mkdir -p "$LOGS"
    set +e
    (cd "$ROOT" && "$PY" -B "$HERE/macos_launch.py" controller_work/after_v3/integration_v7/build_v7.py \
        --output "$OUT_KMB" --log-directory "$LOGS" > "$LOGS/build.stdout" 2>&1)
    STATUS=$?
    set -e
    ;;
  *) die "unsupported system $(uname -s)" ;;
esac
ELAPSED=$((SECONDS - START))
if [ "$STATUS" -ne 0 ] || [ ! -f "$OUT_KMB" ]; then
  [ -f "$LOGS/build.stdout" ] && tail -n 40 "$LOGS/build.stdout" >&2
  die "generator failed (exit $STATUS) after ${ELAPSED}s; logs in $LOGS"
fi

GOT=$(sha256 "$OUT_KMB")
BYTES=$("$PY" -c 'import os, sys; print(os.path.getsize(sys.argv[1]))' "$OUT_KMB")
mkdir -p "$OUT_DIR"
mv -f "$OUT_KMB" "$OUT_DIR/dqi.kmb"
echo "BUILT dqi.kmb $GOT"
echo "build.sh: ${BYTES} bytes in ${ELAPSED}s; build logs in $LOGS"
if [ "${KEEP_WORK:-0}" != "1" ]; then
  rm -rf "$ROOT"
fi
[ "$GOT" = "$EXPECTED_SHA" ] && [ "$BYTES" = "$EXPECTED_BYTES" ] \
  || die "dqi.kmb sha256 $GOT ($BYTES bytes) differs from expected $EXPECTED_SHA ($EXPECTED_BYTES bytes)"
