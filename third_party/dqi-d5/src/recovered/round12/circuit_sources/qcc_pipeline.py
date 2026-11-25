# SPDX-License-Identifier: Apache-2.0
import pathlib, sys, zipfile
import numpy as np
SRC=pathlib.Path(__file__).resolve().parent
COMP=None

def setup(competition_dir) -> None:
    global COMP
    COMP = pathlib.Path(competition_dir)
    for p in (COMP / 'kickmix', COMP / 'verifiers', SRC / 'dqi', SRC / 'dqi/continued_fraction', COMP / 'verifiers/dqi'):
        if str(p) not in sys.path:
            sys.path.append(str(p))

def verify_all(sub: pathlib.Path, salt: str, workers: int | None = None) -> dict:
    """The three official verifiers at their full shot counts."""
    import kickmix as km
    from invsqrt import verify_submission_invsqrt as VI
    from dqi import verify_submission_dqi as VD
    from dfthcsos import verify as VC
    load = lambda p: km.Circuit.from_file(str(p), format='kmb')  # noqa: E731
    res = {'invsqrt': VI.verify(load(sub / 'invsqrt.kmb'), VI.ProblemSpecInvSqrt.for_n_p(10), salt=salt,
                                max_workers=workers),
           'dqi': VD.verify(load(sub / 'dqi.kmb'), VD.ProblemSpecDQI.benchmark_instance(), salt=salt,
                            max_workers=min(workers or 4, 8))}
    folder = sub / 'dfthcsos'
    files = sorted(folder.glob('angle_k_*.kmb'), key=lambda p: int(p.stem.rsplit('_', 1)[1]))
    res['dfthcsos'] = VC.verify(folder, salt=salt)
    return res

def write_zip(sub: pathlib.Path, path: pathlib.Path) -> pathlib.Path:
    members = [sub / 'invsqrt.kmb', sub / 'dqi.kmb'] + sorted((sub / 'dfthcsos').iterdir())
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for m in members:
            z.write(m, m.relative_to(sub).as_posix())
    return path
