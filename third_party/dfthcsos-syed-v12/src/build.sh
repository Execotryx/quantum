#!/usr/bin/env bash
# Copyright 2026 Syed Asad Ali. Licensed under Apache-2.0.
# Credits: Syed Asad Ali, working with a team of AI agents (GPT-6 Astra Pro, Gemini 4 Argon, Fable 5.2, Mythos 5.2 and Opus 5.5), with Claude Science supporting the research.
#
# build.sh - rebuild our 15 dfthcsos ANGLE_k loader circuits from source and copy the frozen submission.npz.
#
#   bash build.sh ENGINE_DIR VERIFIERS_DIR OUT_DIR
#
# ENGINE_DIR     the competition's kickmix/ folder (holds the Linux kickmix.so). Copied into the work tree, never shipped.
# VERIFIERS_DIR  the competition's verifiers/ folder. Accepted for the common interface; this build does not read it.
# OUT_DIR        receives dfthcsos/angle_k_0..14.kmb and dfthcsos/submission.npz.
# Environment:   PY (default python3; CPython 3.13 with NumPy; may be a command with arguments, split on spaces),
#                WORK (default: a new folder ${TMPDIR:-/tmp}/dfthcsos.XXXXXX, removed at the end), PROOF (default 1: run our own exact
#                all-branch loader proof, about 2 s, NumPy only; PROOF=0 skips it), MAC_ENGINE (macOS test only: a
#                platform-tagged kickmix module, e.g. kickmix.cpython-313-darwin.so, copied beside the Linux kickmix.so).
# Prints one line "BUILT <file> <sha256>" per output file. Exits non-zero on any failure.
set -euo pipefail

die() { echo "build.sh: ERROR: $*" >&2; exit 1; }
[ "$#" -eq 3 ] || die "usage: bash build.sh ENGINE_DIR VERIFIERS_DIR OUT_DIR"
ENGINE_DIR="$1"; VERIFIERS_DIR="$2"; OUT_DIR="$3"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
read -r -a PYCMD <<< "${PY:-python3}"
PROOF="${PROOF:-1}"
T_START=$(date +%s)

# Target bytes (identical to the verified submission; rebuild.py also checks manifest.json).
KICKMIX_SHA=c66b3216c4029e0cdfd09054306aa0feadf53ab2f50c1164e37f752874e5005e
TARGETS="ce7ebaf342c5b49f7d539637359fb8a282718fb3057e7b25dd193f2a6a4b8974  dfthcsos/angle_k_0.kmb
3eac70665f021b0e304106fd62749277d4d69db775df008aacd6d950e4934193  dfthcsos/angle_k_1.kmb
c3e1454e29a05c3c28bcfd16c2aee02340b5d439d9466774424fedf0ed7601d1  dfthcsos/angle_k_2.kmb
d26b576ae789b0471ec6c11b7317c7c69eb3d7190472af8120ccf25cf217a8ea  dfthcsos/angle_k_3.kmb
2efacc9d944aa5a855acf780e6bbc3c07af16c0275eb9549bb24adc70acca344  dfthcsos/angle_k_4.kmb
7e4ed9a363c8f56d85410185c7b4449211788bc61e81b3dc7cbdd10ab7ce8a42  dfthcsos/angle_k_5.kmb
26ab1d5df8132bbc28e068a4eef0b247ea21a96fa4034f89a6d1bf306f07e284  dfthcsos/angle_k_6.kmb
1ae98642315e7aaedfde99773af4ae48198bf8b4f2e11e97883d6aa1bfe12bee  dfthcsos/angle_k_7.kmb
e69c554c360c709e52126a6f773afeaa3564da7be0927d6293665f342203771f  dfthcsos/angle_k_8.kmb
38848ce19bd553e4007a454d9b7d392d05ac105cf4b269f41521bd1003bf838e  dfthcsos/angle_k_9.kmb
fdb67807154e35d9f41471c22b38bbc3ed07e5c93efef30a57f0599fb8400ff7  dfthcsos/angle_k_10.kmb
d22baf8e2d294165618bcee40d958ef2806f0b35352c8b92e0d201aff3269c37  dfthcsos/angle_k_11.kmb
b1b6af502f4bf02e521ab888600f645aa5a5bed028290466b54a835423eb2517  dfthcsos/angle_k_12.kmb
1843d7993215656e4e0eee69169966ba269d544bc0b90e855e4ed5e6e113accc  dfthcsos/angle_k_13.kmb
b763f0cd2fdeaaa31e7811084e51fde5d51575b036fa22854fb28172c1712a8e  dfthcsos/angle_k_14.kmb
6418ec8e10b1a8da967ee26278434f9ac950474741185f4d61363e17a03da77f  dfthcsos/submission.npz"

# --- Python: CPython 3.13 with NumPy -------------------------------------------------------------------------
"${PYCMD[@]}" -c 'import sys; sys.exit(0 if sys.implementation.name == "cpython" and sys.version_info[:2] == (3, 13) else 1)' \
  || die "PY='${PY:-python3}' must be CPython 3.13"
"${PYCMD[@]}" -c 'import numpy' || die "NumPy is not importable with PY='${PY:-python3}'"
sha256() {  # sha256 FILE... -> "<hex>  <path>" lines (hashlib, so no sha256sum/shasum difference between hosts)
  "${PYCMD[@]}" -c 'import hashlib, sys
for p in sys.argv[1:]:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    print(h.hexdigest() + "  " + p)' "$@"
}

# --- Host inputs ---------------------------------------------------------------------------------------------
[ -f "$ENGINE_DIR/kickmix.so" ] || die "ENGINE_DIR has no kickmix.so: $ENGINE_DIR"
[ -d "$VERIFIERS_DIR" ] || die "VERIFIERS_DIR is not a directory: $VERIFIERS_DIR"
ENGINE_SHA="$(sha256 "$ENGINE_DIR/kickmix.so" | cut -d' ' -f1)"
[ "$ENGINE_SHA" = "$KICKMIX_SHA" ] || echo "build.sh: WARNING: kickmix.so SHA-256 $ENGINE_SHA differs from the pinned $KICKMIX_SHA; the output hash checks below decide." >&2
if [ "$(uname -s)" = "Darwin" ] && [ -z "${MAC_ENGINE:-}" ]; then
  die "on macOS set MAC_ENGINE to a platform-tagged kickmix module (e.g. kickmix.cpython-313-darwin.so); the Linux kickmix.so cannot load here"
fi
if [ -n "${MAC_ENGINE:-}" ]; then
  [ -f "$MAC_ENGINE" ] || die "MAC_ENGINE is not a file: $MAC_ENGINE"
  case "$(basename "$MAC_ENGINE")" in kickmix.*.so) ;; *) die "MAC_ENGINE must be named kickmix.<platform tag>.so: $MAC_ENGINE" ;; esac
  MAC_ENGINE="$(cd "$(dirname "$MAC_ENGINE")" && pwd)/$(basename "$MAC_ENGINE")"
fi
# Absolute paths from here on (the build later changes directory).
ENGINE_DIR="$(cd "$ENGINE_DIR" && pwd)"; VERIFIERS_DIR="$(cd "$VERIFIERS_DIR" && pwd)"
mkdir -p "$OUT_DIR/dfthcsos" || die "cannot create OUT_DIR/dfthcsos: $OUT_DIR"
OUT_DIR="$(cd "$OUT_DIR" && pwd)"

# --- Writable work copy of this folder -----------------------------------------------------------------------
if [ -n "${WORK:-}" ]; then
  mkdir -p "$WORK"; WORK="$(cd "$WORK" && pwd)"; CLEAN=0
else
  WORK="$(mktemp -d "${TMPDIR:-/tmp}/dfthcsos.XXXXXX")"; CLEAN=1
fi
if [ "$CLEAN" = 1 ]; then trap 'rm -rf "$WORK"' EXIT; fi
case "$WORK/" in "$HERE/"*) die "WORK must not be inside this folder: $WORK" ;; esac
BASE="$WORK/dfthcsos_build"
rm -rf "$BASE"; mkdir -p "$BASE/src" "$BASE/build"
SRC="$BASE/src"; BLD="$BASE/build"
cp -R "$HERE/." "$SRC/"
chmod -R u+w "$SRC"
echo "work copy: $SRC"
# Every file of the folder must match SHA256SUMS, and nothing unlisted may be present.
"${PYCMD[@]}" -c 'import hashlib, os, sys
root = sys.argv[1]; listed = {}
for line in open(os.path.join(root, "SHA256SUMS")):
    h, p = line.rstrip("\n").split("  ", 1); listed[p] = h
present = set()
for d, _, fs in os.walk(root):
    for f in fs:
        rel = os.path.relpath(os.path.join(d, f), root).replace(os.sep, "/")
        if "__pycache__/" not in rel: present.add(rel)  # bytecode caches are ignored
present.discard("SHA256SUMS")
bad = [p for p, h in listed.items() if p not in present or hashlib.sha256(open(os.path.join(root, p), "rb").read()).hexdigest() != h]
extra = sorted(present - set(listed))
if bad or extra: sys.exit("SHA256SUMS check failed: bad=%s extra=%s" % (sorted(bad)[:10], extra[:10]))
print("SHA256SUMS OK: %d files" % len(listed))' "$SRC" || die "source folder does not match SHA256SUMS"
# No baked-in absolute paths: rebuild.py and compiler/ resolve every input relative to their own file.
# Host engine beside rebuild.py, where the pinned rebuild.py imports it (import kickmix).
cp "$ENGINE_DIR/kickmix.so" "$SRC/kickmix.so"
if [ -n "${MAC_ENGINE:-}" ]; then cp "$MAC_ENGINE" "$SRC/$(basename "$MAC_ENGINE")"; fi

# --- Build ---------------------------------------------------------------------------------------------------
cd "$SRC"
PYENV=(env PYTHONPATH="$SRC${PYTHONPATH:+:$PYTHONPATH}" PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1)
"${PYENV[@]}" "${PYCMD[@]}" rebuild.py --submission "$SRC/submission.npz" \
  --output "$BLD/circuits" --source-output "$BLD/sources" || die "rebuild.py failed"
mkdir -p "$BLD/dfthcsos"
for k in $(seq 0 14); do cp "$BLD/circuits/angle_k_$k.kmb" "$BLD/dfthcsos/angle_k_$k.kmb"; done
cp "$SRC/submission.npz" "$BLD/dfthcsos/submission.npz"
(cd "$BLD" && sha256 $(echo "$TARGETS" | awk '{print $2}')) > "$BLD/got.sha256"
if [ "$(cat "$BLD/got.sha256")" != "$TARGETS" ]; then
  echo "expected:" >&2; echo "$TARGETS" >&2; echo "got:" >&2; cat "$BLD/got.sha256" >&2; die "output SHA-256 mismatch"
fi
echo "all 16 output files match the target SHA-256 list"

if [ "$PROOF" = 1 ]; then
  "${PYENV[@]}" "${PYCMD[@]}" verification/prove_loader_branches.py "$BLD/sources" "$SRC/submission.npz" "$BLD/branch_proof.json" \
    > "$BLD/branch_proof.stdout" || die "own branch proof failed"
  "${PYCMD[@]}" -c 'import json, sys
d = json.load(open(sys.argv[1]))
assert d["status"] == "PASS" and d["circuits"] == 15 and d["all_HMR_outcomes"] is True, d["status"]
print("own exact branch proof: %s, %d circuits x %d directions, %d addresses, all HMR outcomes, ANGLE Toffolis per pass %d"
      % (d["status"], d["circuits"], d["directions_per_circuit"], d["addresses"], d["angles_toffoli_per_pass"]))' \
    "$BLD/branch_proof.json" || die "own branch proof did not pass"
fi

# --- Outputs -------------------------------------------------------------------------------------------------
for f in $(echo "$TARGETS" | awk '{print $2}'); do cp "$BLD/$f" "$OUT_DIR/$f"; done
(cd "$OUT_DIR" && sha256 $(echo "$TARGETS" | awk '{print $2}')) > "$BLD/out.sha256"
[ "$(cat "$BLD/out.sha256")" = "$TARGETS" ] || die "copied outputs do not match the target SHA-256 list"
awk '{print "BUILT " $2 " " $1}' "$BLD/out.sha256"
echo "build.sh: done in $(( $(date +%s) - T_START )) s"
