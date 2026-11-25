#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Fixed full4095-position v5 generator, guarded and independent of profiles."""
from pathlib import Path
import argparse
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('dqi.kmb'))
    parser.add_argument('--log-directory', type=Path, default=Path('dqi-v5-build'))
    parser.add_argument('--rss-soft', type=int, default=4_000_000_000)
    parser.add_argument('--available-reserve', type=int, default=4_000_000_000)
    args = parser.parse_args()
    if not __debug__ or sys.version_info[:2] != (3,13):
        parser.error('Use the supplied Python3.13 runtime without optimization.')
    if args.rss_soft <= 0 or args.available_reserve <= 0:
        parser.error('Positive memory guard limits are required.')
    here = Path(__file__).resolve().parent
    work = here.parents[1]
    logs = args.log_directory.resolve()
    if args.output.exists() or (logs.exists() and any(logs.iterdir())):
        parser.error('Use a new output path and a new build-log directory.')
    logs.mkdir(parents=True, exist_ok=True)
    command = [sys.executable,'-B',str(work/'after_c5/root/guard_wait.py'),
               '--log',str(logs/'memory-guard.json'),'--stdout',str(logs/'build.stdout'),
               '--rss-soft',str(args.rss_soft),'--reserve',str(args.available_reserve),'--',
               sys.executable,'-B',str(here/'build_v5.py'),
               '--output',str(args.output.resolve()),'--log-directory',str(logs)]
    return subprocess.run(command,check=False).returncode


if __name__ == '__main__':
    raise SystemExit(main())
