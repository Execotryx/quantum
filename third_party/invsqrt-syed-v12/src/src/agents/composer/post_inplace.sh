#!/bin/bash
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0. Credits: Opus and Astra.
# COMPOSER: apply a text post-pass (e.g. micro47's relocate_cs2.py) to a composed run IN PLACE, recompile, re-prove.
# post_inplace.sh FINALDIR NAME FGROOT PASS.py   (PASS relative to FGROOT; the pre-pass artifacts are kept as precs.*)
set -euo pipefail
F=$1; NAME=$2; ROOT=$3; PASS=$4
source $ROOT/tools/env.sh
mv $F/final_text.kmx $F/final_text_precs.kmx
for s in kmb kmx build.json proof.json; do cp $F/$NAME.$s $F/precs.$s; done
$PY $ROOT/$PASS $F/final_text_precs.kmx $F/final_text.kmx > $F/post.log 2>&1 || { echo "POST PASS FAILED"; tail -5 $F/post.log; exit 1; }
$MG $PY $ROOT/tools/macrun.py $ROOT/tools/kmx_to_kmb.py $F/final_text.kmx --out $F/$NAME.kmb > $F/compile_post.log
$PY -c "import json,sys;d=json.load(open(sys.argv[1]));print('compiled',d['kmb_sha256'],d['cost_model'])" $F/$NAME.build.json
$MG $PY $ROOT/tools/macrun.py $ROOT/tools/prove_any.py --circuit $F/$NAME.kmb --out $F/$NAME.proof.json > $F/prove_post.log 2>&1 || { echo "PROOF FAILED"; tail -5 $F/prove_post.log; exit 1; }
$PY -c "import json,sys;d=json.load(open(sys.argv[1]));print('proof',d['status'],d['proved_inputs'],'HMR',d['independent_HMR_variables'],d['circuit_sha256'])" $F/$NAME.proof.json
