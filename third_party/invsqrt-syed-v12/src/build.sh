#!/bin/bash
# Copyright 2026 Syed Asad Ali. Licensed under Apache-2.0.
# Credits: Syed Asad Ali, working with a team of AI agents (GPT-6 Astra Pro, Gemini 4 Argon, Fable 5.2, Mythos 5.2 and Opus 5.5), with Claude Science supporting the research.
#
# Rebuild the invsqrt circuit invsqrt.kmb from the generator tree in src/ and check its SHA-256.
#
#   bash build.sh ENGINE_DIR VERIFIERS_DIR OUT_DIR
#
#   ENGINE_DIR     the competition's kickmix/ folder (holds the Linux kickmix.so)
#   VERIFIERS_DIR  the competition's verifiers/ folder (holds invsqrt/verify_submission_invsqrt.py)
#   OUT_DIR        output folder; invsqrt.kmb is written there
#
# Optional environment:
#   PY          CPython 3.13 with numpy (default python3).
#   MG          command prefix for the heavy steps, e.g. a memory guard (default empty).
#   WORK        a writable folder (default ${TMPDIR:-/tmp}); the build makes a fresh subfolder invsqrt_build.XXXXXX
#               in it for the work tree and logs. The path must not contain spaces or @.
#   MAC_ENGINE  macOS only: a macOS build of the kickmix extension (kickmix.cpython-313-darwin.so). It is copied
#               beside the Linux kickmix.so, which stays in place because the sources check its SHA-256.
#
# The host files (kickmix.so, the official verifier) are not part of this folder: they are copied from ENGINE_DIR and
# VERIFIERS_DIR into the work tree where the pinned sources expect them. The token @FG_ROOT@ in the .py/.sh files
# outside work/c10 is replaced by the work tree path. Steps: patched generator (tools/build_variant.py), mechanical
# passes + compile + exact full-domain proof (tools/pipeline.sh), the declared post pass (agents/composer/post_inplace.sh,
# which compiles and proves again), then the SHA-256 check.
set -euo pipefail
NAME=s15k7a
WANT=321aff83636214196daa9cbc9dcc9c5e12a155bcff8d9989e98b8cee40935177
KSO_SHA=c66b3216c4029e0cdfd09054306aa0feadf53ab2f50c1164e37f752874e5005e
VER_SHA=ddef520dec6b68d1cf0a6f328ddd36d79eb84570b9192cf3f7acaf073f06733a
PASS_STATUS=PASS_EXACT_NATIVE_TEXT_ALL_REQUESTED_INPUTS_ALL_HMR_TRANSCRIPTS
die() { echo "build.sh: $*" >&2; exit 1; }
[ $# -eq 3 ] || { sed -n '5,20p' "$0" >&2; exit 2; }
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
[ -d "$1" ] || die "ENGINE_DIR not found: $1"
[ -d "$2" ] || die "VERIFIERS_DIR not found: $2"
ENGINE_DIR=$(cd "$1" && pwd); VERIFIERS_DIR=$(cd "$2" && pwd)
mkdir -p "$3"; OUT_DIR=$(cd "$3" && pwd)
export PY="${PY:-python3}"
export MG="${MG:-}"
# variables the generator reads as overrides; they must not leak in from the caller
unset DIVIDER_FORCE_CAP DIVIDER_PLACEHOLDER DIVIDER_RETIRE LD_FIRST_JSON LEAD_SECOND_JSON TK46_SECOND_JSON \
      W2_E_HOLD W2_F_HOLD W2_R2 W2_V10_G1 W2_V9_FORM W2_V9_PLACEHOLDER FG NARROW
T0=$(date +%s)

$PY - <<'EOF' || die "PY must be CPython 3.13 with numpy (PY=$PY)"
import platform, sys
assert sys.implementation.name == 'cpython' and sys.version_info[:2] == (3, 13), sys.version
import numpy
print(f'python {platform.python_version()} ({sys.platform} {platform.machine()}), numpy {numpy.__version__}')
EOF
sha() { $PY -I -c "import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" "$1"; }

KSO=$ENGINE_DIR/kickmix.so; VER=$VERIFIERS_DIR/invsqrt
[ -f "$KSO" ] || die "missing $KSO"
[ -f "$VER/verify_submission_invsqrt.py" ] || die "missing $VER/verify_submission_invsqrt.py"
[ "$(sha "$KSO")" = "$KSO_SHA" ] || die "kickmix.so SHA-256 differs from the pinned host file ($KSO_SHA)"
[ "$(sha "$VER/verify_submission_invsqrt.py")" = "$VER_SHA" ] || die "verifier SHA-256 differs from the pinned host file ($VER_SHA)"
if [ "$(uname -s)" = Darwin ]; then
  [ -n "${MAC_ENGINE:-}" ] && [ -f "$MAC_ENGINE" ] || die "macOS: set MAC_ENGINE to a macOS kickmix build (kickmix.cpython-313-darwin.so)"
fi

PARENT=${WORK:-${TMPDIR:-/tmp}}
mkdir -p "$PARENT"; PARENT=$(cd "$PARENT" && pwd)
WORK=$(mktemp -d "$PARENT/invsqrt_build.XXXXXX") || die "cannot create a work folder in $PARENT"
case "$WORK" in *[[:space:]]*|*@*) die "WORK path must not contain spaces or @: $WORK";; esac
X=$WORK/tree
mkdir -p "$X"
cp -R "$HERE/src/." "$X/"
chmod -R u+w "$X"
OFF=$X/work/c10/narrow/base/official
mkdir -p "$OFF/kickmix" "$OFF/verifier_invsqrt"
cp "$KSO" "$OFF/kickmix/kickmix.so"
for f in __init__.py nr_reference_circuit.py verify_submission_invsqrt.py; do
  if [ -f "$VER/$f" ]; then cp "$VER/$f" "$OFF/verifier_invsqrt/$f"; fi
done
if [ "$(uname -s)" = Darwin ]; then cp "$MAC_ENGINE" "$OFF/kickmix/kickmix.cpython-313-darwin.so"; fi

# relocation: @FG_ROOT@ -> X in .py/.sh files outside work/c10 (data files and the pinned base tree are not edited)
$PY -I - "$X" <<'EOF' || die "relocation failed"
import os, sys
root = sys.argv[1]; base = os.path.join(root, 'work', 'c10'); tok = '@FG_ROOT@'; n = 0
for d, subdirs, files in os.walk(root):
    if os.path.abspath(d) == os.path.abspath(base):
        subdirs[:] = []
        continue
    for f in files:
        p = os.path.join(d, f)
        with open(p, 'rb') as fh:
            b = fh.read()
        if tok.encode() not in b:
            continue
        if not f.endswith(('.py', '.sh')):
            sys.exit(f'token in a non-source file: {p}')
        with open(p, 'wb') as fh:
            fh.write(b.replace(tok.encode(), root.encode()))
        n += 1
print(f'relocated {n} files to {root}')
EOF
if grep -rl '@FG_ROOT@' "$X" >/dev/null 2>&1; then die "token left in: $(grep -rl '@FG_ROOT@' "$X" | head -3)"; fi

source "$X/tools/env.sh"
[ "$FG" = "$X" ] || die "env.sh FG=$FG, expected $X"
Q=$(awk '$1=="Q"{print $2}' "$X/patches/PATCH_ORDER.txt")
ARGS=(); POSTS=()
while read -r kind name || [ -n "${kind:-}" ]; do
  if [ "$kind" = patch ]; then ARGS+=(--patch "$X/patches/$name"); fi
  if [ "$kind" = post ]; then POSTS+=("$name"); fi
done < "$X/patches/PATCH_ORDER.txt"
[ -n "$Q" ] && [ ${#ARGS[@]} -gt 0 ] || die "PATCH_ORDER.txt gave no Q or no patches"
cd "$X"
echo "build: $NAME at Q$Q, ${#ARGS[@]} patch args, work tree $X"
$MG $PY "$X/tools/macrun.py" "$X/tools/build_variant.py" --out "$X/build" --name "${NAME}raw" --Q "$Q" "${ARGS[@]}" \
  > "$WORK/build.log" 2>&1 || { tail -8 "$WORK/build.log" >&2; die "generator failed (log $WORK/build.log)"; }
echo "generator done ($(( $(date +%s) - T0 )) s)"
bash "$X/tools/pipeline.sh" "$X/build/${NAME}raw.kmx" "$X/final" "$NAME" "$Q" > "$WORK/pipeline.log" 2>&1 \
  || { tail -5 "$WORK/pipeline.log" >&2; die "pipeline failed (log $WORK/pipeline.log)"; }
echo "pipeline done ($(( $(date +%s) - T0 )) s)"
for name in ${POSTS[@]+"${POSTS[@]}"}; do
  bash "$X/agents/composer/post_inplace.sh" "$X/final" "$NAME" "$X" "$name" > "$WORK/post.log" 2>&1 \
    || { tail -5 "$WORK/post.log" >&2; die "post pass failed (log $WORK/post.log)"; }
done
echo "post pass done ($(( $(date +%s) - T0 )) s)"

STATUS=$($PY -c "import json,sys;print(json.load(open(sys.argv[1]))['status'])" "$X/final/$NAME.proof.json")
[ "$STATUS" = "$PASS_STATUS" ] || die "exact proof status $STATUS"
echo "proof: $STATUS"
GOT=$(sha "$X/final/$NAME.kmb")
[ "$GOT" = "$WANT" ] || die "SHA-256 mismatch: got $GOT, want $WANT"
cp "$X/final/$NAME.kmb" "$OUT_DIR/invsqrt.kmb"
GOT=$(sha "$OUT_DIR/invsqrt.kmb")
[ "$GOT" = "$WANT" ] || die "SHA-256 mismatch after copy: $GOT"
echo "wall time $(( $(date +%s) - T0 )) s; work tree $WORK"
echo "BUILT invsqrt.kmb $GOT"
