# Copyright 2026 Syed Asad Ali. Licensed under Apache-2.0.
# Credits: Syed Asad Ali, working with a team of AI agents (GPT-6 Astra Pro, Gemini 4 Argon, Fable 5.2, Mythos 5.2 and Opus 5.5), with Claude Science supporting the research.
# Source this: common paths for the invsqrt generator (written for this release). build.sh replaces the
# token @FG_ROOT@ by the work tree and exports PY (CPython 3.13 with numpy) and MG (optional command prefix).
export FG=@FG_ROOT@
export PY="${PY:-python3}"
export MG="${MG:-}"
export NARROW=$FG/work/c10/narrow
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
