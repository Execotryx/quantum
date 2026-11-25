#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Guarded full4095-position post-C5 candidate generator, public cutoff15.

This separate entry does not replace controller_work/gen_dqi.py, which still
rebuilds accepted C5. Public switches choose code variants, never an input
profile, terminal, contact set, polynomial alias table, or verifier salt.
"""
from pathlib import Path
import argparse
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('dqi-post-c5.kmb'))
    parser.add_argument('--log-directory', type=Path, default=Path('dqi-post-c5-build'))
    parser.add_argument('--rss-soft', type=int, default=4_000_000_000)
    parser.add_argument('--available-reserve', type=int, default=4_000_000_000)
    parser.add_argument('--first-two-charts', action='store_true')
    parser.add_argument('--nested-norm', action='store_true')
    parser.add_argument('--finish-seam', action='store_true')
    args = parser.parse_args()
    if sys.version_info[:2] != (3, 13):
        parser.error('Use the supplied Python3.13 runtime.')
    if args.rss_soft <= 0 or args.available_reserve <= 0:
        parser.error('Positive memory guard limits are required.')
    here = Path(__file__).resolve().parent
    work = here.parents[1]
    logs = args.log_directory.resolve()
    logs.mkdir(parents=True, exist_ok=True)
    public_flags = []
    if args.first_two_charts:
        public_flags.append('--first-two-charts')
    if args.nested_norm:
        public_flags.append('--nested-norm')
    if args.finish_seam:
        public_flags.append('--finish-seam')
    command = [sys.executable, '-B', str(work/'runtime/guard.py'),
               '--log', str(logs/'memory-guard.json'),
               '--stdout', str(logs/'build.stdout'),
               '--rss-soft', str(args.rss_soft),
               '--reserve', str(args.available_reserve), '--',
               sys.executable, '-B', str(here/'build_candidate.py'),
               '--output', str(args.output.resolve()),
               '--log-directory', str(logs), *public_flags]
    return subprocess.run(command, check=False).returncode


if __name__ == '__main__':
    raise SystemExit(main())
