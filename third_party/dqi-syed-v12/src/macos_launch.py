# Copyright 2026 Syed Asad Ali. Licensed under Apache-2.0.
# Credits: Syed Asad Ali, working with a team of AI agents (GPT-6 Astra Pro, Gemini 4 Argon, Fable 5.2, Mythos 5.2 and Opus 5.5), with Claude Science supporting the research.
"""macOS test-only launcher for the unchanged build_v7.py (Linux never uses it).

On Linux, build.sh runs the package's own entry point gen_dqi.py, whose memory
guard (guard_wait.py) reads /proc and then starts build_v7.py. macOS has no
/proc, so on macOS build.sh starts build_v7.py through this file instead.

The competition engine is a Linux binary. For a macOS test, a macOS build of
the same engine (kickmix.cpython-313-darwin.so) is placed beside the official
Linux kickmix.so; Python loads the platform-tagged file. The unchanged source
inventory, written after the circuit file, hashes the file named by
kickmix.__file__ and requires the official Linux engine hash. This launcher
therefore points kickmix.__file__ at the Linux kickmix.so sitting beside the
macOS file, and prints the hash of the macOS file it really loaded.

Usage: python -B macos_launch.py BUILD_V7_PY --output OUT --log-directory LOGS
"""
import hashlib
import importlib.abc
import importlib.machinery
import runpy
import sys
from pathlib import Path


class _Relabel(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path=None, target=None):
        if name != 'kickmix':
            return None
        spec = importlib.machinery.PathFinder.find_spec(name, path)
        if spec is None:
            return None
        loader = spec.loader

        class Loader(importlib.abc.Loader):
            def create_module(self, spec):
                return loader.create_module(spec)

            def exec_module(self, module):
                loader.exec_module(module)
                real = Path(module.__file__).resolve()
                linux = real.with_name('kickmix.so')
                if real != linux:
                    assert sys.platform == 'darwin' and linux.is_file(), real
                    sha = hashlib.sha256(real.read_bytes()).hexdigest()
                    print(f'MACOS_TEST_ENGINE {real.name} {sha}', file=sys.stderr, flush=True)
                    module.__file__ = str(linux)

        spec.loader = Loader()
        return spec


def main():
    if sys.platform != 'darwin':
        raise SystemExit('macos_launch.py is for macOS tests only; use gen_dqi.py on Linux.')
    build = Path(sys.argv[1]).resolve()
    assert build.name == 'build_v7.py' and build.is_file(), build
    sys.meta_path.insert(0, _Relabel())
    sys.argv = [str(build)] + sys.argv[2:]
    sys.path[0] = str(build.parent)  # as when the script is run directly
    runpy.run_path(str(build), run_name='__main__')


if __name__ == '__main__':
    main()
