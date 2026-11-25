# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Fixed source roots for the T-only continuation of accepted v3."""
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
WORK = PROJECT.parent
ROOT = WORK.parent


def enable_new_sources():
    for path in (PROJECT/'blocks', PROJECT/'k24', PROJECT/'scan',
                 PROJECT/'audit/retained_child'):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))


# The accepted loader must establish its frozen import boundary before any
# new native-dependent arithmetic module is imported.
if str(PROJECT/'blocks') not in sys.path:
    sys.path.insert(0, str(PROJECT/'blocks'))
