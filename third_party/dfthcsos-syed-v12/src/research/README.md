Copyright 2026 Syed Asad Ali. Licensed under Apache-2.0.
Credits: Syed Asad Ali, working with a team of AI agents (GPT-6 Astra Pro, Gemini 4 Argon, Fable 5.2, Mythos 5.2 and Opus 5.5), with Claude Science supporting the research.

# research/ - NOT part of the build

The build does not use this folder (`build.sh` only checks its checksums with the rest of the folder).
It is here for transparency.

`research/scripts/` holds our own research code behind the data in `../submission.npz` (the
factorization weights and the 1220 x 75 angle words) and behind many of the loader plans in `../plans/`:
the fast metric model and weight refits (`fastchem.py`, `refit.py`, `sqp.py`, `alfit.py`,
`exact_refit*.py`, `repair.py`, ...), the code-preserving word searches (`word_*.py`, `onebody.py`,
`parity_code.py`, `code_improve.py`, ...) and the loader planners (`planner.py`, `minrank.py`,
`compile_*.py`, `prefix_*.py`, ...). Some later loader plans came from agent work trees that are not
shipped. These were long fitting and search runs over inputs that are not in this folder (the
competition's FeMoCo reference files, our earlier work trees and intermediate arrays), so the scripts do
not run from here as they are. Every file is byte-identical to our verified package D35.

Not included: packaging, delivery and receipt tools, package-version assemblers, local environment and
resource-guard files, and two analyses that compared our loaders with public ones.
