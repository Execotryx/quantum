#!/bin/bash
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0. Credits: Opus and Astra.
# pipeline.sh IN.kmx OUTDIR NAME [Q]
# Mechanical finishing passes on any invsqrt kmx text, then the exact full-domain proof:
#   1. recomputed-product scan (audit_pairs) + hold pass (hold_pass)
#   2. affine-product audit (audit_affine) + rewrite (postpass), repeated until nothing is found
#   2b. Z_POW gates on the same Boolean feature merged (merge_zpow): folds T gates into rotations
#   3. compile to canonical kmb/kmx (kmx_to_kmb) and prove (prove_any)
# A result counts only after this proof AND kme/official verification on salts default, 1, 2, 3.
set -euo pipefail
source @FG_ROOT@/tools/env.sh
IN=$1; OUT=$2; NAME=$3; Q=${4:-48}
T=$FG/tools
mkdir -p "$OUT"
$MG $PY $T/audit_affine.py "$IN" --out "$OUT/s1.audit.json" > "$OUT/s1.audit.log"
$MG $PY $T/audit_pairs.py "$IN" --live "$OUT/s1.audit.live.npy" --out "$OUT/s1.pairs.json" > "$OUT/s1.pairs.log"
$MG $PY $T/hold_pass.py "$IN" "$OUT/s1.pairs.json" --out "$OUT/s2.kmx" --Q "$Q" > "$OUT/s2.hold.log"
CUR="$OUT/s2.kmx"
for ROUND in 1 2 3 4; do
  $MG $PY $T/audit_affine.py "$CUR" --out "$OUT/r$ROUND.audit.json" > "$OUT/r$ROUND.audit.log"
  N=$($PY -c "import json,sys;print(len(json.load(open(sys.argv[1]))['findings']))" "$OUT/r$ROUND.audit.json")
  echo "affine round $ROUND: $N findings"
  if [ "$N" = "0" ]; then break; fi
  $MG $PY $T/postpass.py "$CUR" "$OUT/r$ROUND.audit.json" --out "$OUT/r$ROUND.kmx"
  CUR="$OUT/r$ROUND.kmx"
done
$MG $PY $T/merge_zpow.py "$CUR" --out "$OUT/zpow.kmx" > "$OUT/zpow.log"
echo "zpow merge: $(cat "$OUT/zpow.log")"
CUR="$OUT/zpow.kmx"
cp "$CUR" "$OUT/final_text.kmx"
$MG $PY $T/macrun.py $T/kmx_to_kmb.py "$OUT/final_text.kmx" --out "$OUT/$NAME.kmb" > "$OUT/compile.log"
$PY -c "import json,sys;d=json.load(open(sys.argv[1]));print('compiled',d['kmb_sha256'],d['cost_model'])" "$OUT/$NAME.build.json"
$MG $PY $T/macrun.py $T/prove_any.py --circuit "$OUT/$NAME.kmb" --out "$OUT/$NAME.proof.json" > "$OUT/prove.log" 2>&1 || { echo "PROOF FAILED"; tail -5 "$OUT/prove.log"; exit 1; }
$PY -c "import json,sys;d=json.load(open(sys.argv[1]));print('proof',d['status'],d['proved_inputs'],'HMR',d['independent_HMR_variables'],d['circuit_sha256'])" "$OUT/$NAME.proof.json"
