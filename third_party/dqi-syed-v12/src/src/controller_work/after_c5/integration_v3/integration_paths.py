# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Fixed local imports for the isolated post-C5 integration v3 branch."""
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
AFTER = HERE.parent
WORK = AFTER.parent
ROOT = WORK.parent
for directory in (
    WORK / 'work/round2/milestone152/source',
    ROOT / 'pro1_controller_bundle/1_task/official',
    WORK / 'night_converter', WORK / 'night_schedule', WORK / 'night_root',
    WORK / 'night_c27', WORK / 'night_c27/arithmetic',
    WORK / 'night_c27/controller', WORK / 'night_c27/synthesis',
    WORK / 'night_c27/mask_gauge', AFTER / 'extractor_width',
    AFTER / 'converter_width',
    AFTER / 'converter_width/tail_phase_defer',
    AFTER / 'converter_width/local_flag_defer',
    AFTER / 'arithmetic_t', HERE,
):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))
