#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Generate the fixed full-size DQI candidate with an active memory guard.

Run with the supplied kickmix-compatible Python 3.13 environment. This entry
point always emits all 4,095 physical positions and the public j_min=15 policy;
it accepts no input profiles, terminal degrees, contacts, or verifier salts.
Building alone does not certify the circuit. Read the accompanying handoff
and checkpoint reports for the actual status of verification and cost gates.
"""
from pathlib import Path
import argparse
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('dqi.kmb'))
    parser.add_argument('--log-directory', type=Path, default=Path('dqi-build-logs'))
    parser.add_argument('--rss-soft', type=int, default=4_000_000_000)
    parser.add_argument('--available-reserve', type=int, default=4_000_000_000)
    args = parser.parse_args()
    if sys.version_info[:2] != (3, 13):
        parser.error('Use the supplied Python 3.13 runtime, e.g. /usr/bin/python3.13.')
    if args.rss_soft <= 0 or args.available_reserve <= 0:
        parser.error('Memory guard limits must be positive.')
    work = Path(__file__).resolve().parent
    output = args.output.resolve()
    logs = args.log_directory.resolve()
    logs.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, '-B', str(work/'runtime/guard.py'),
               '--log', str(logs/'memory-guard.json'),
               '--stdout', str(logs/'build.stdout'),
               '--rss-soft', str(args.rss_soft),
               '--reserve', str(args.available_reserve), '--',
               sys.executable, '-B', str(work/'night_c27/build_candidate.py'),
               '--output', str(output), '--log-directory', str(logs),
               '--conditional-flag-phases']
    return subprocess.run(command, check=False).returncode


if __name__ == '__main__':
    raise SystemExit(main())
