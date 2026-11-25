# Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.
"""Try for 147 cuts (189 products) on a loader that already has a 145-cut plan (our own).

Re-runs the scored-drop descent in the saved low basis, takes the state with 147 cuts on that path
and climbs the pairing rank at a fixed cut count (planner.rank_climb: swap one cut for another
annihilator of the same block, keep if the rank does not fall). If the pairing becomes perfect the
loader is emitted and proved exactly like compile_basis.compile_one. Nothing is written otherwise.
"""
import sys, json, time
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import compile_basis as cb
from planner import BlockPlan, descend_smart, rank_climb, physical_cuts, solve_padding, NDIM
from lowbasis import inverse15, transform_target


def main(words_path, plans_dir, outdir, k, seed, climb_seconds=90, level=147):
    cand = np.load(ROOT / words_path)
    W = cand['words'] if 'words' in cand.files else cand['angle_words']
    s = json.loads((ROOT / plans_dir / f'angle_k_{k}.plan_state.json').read_text())
    rows = [int(x) for x in s['explicit_certificate']['low_basis_dual_rows']]
    t0 = time.time()

    def plan(target, seeds=(7,), trials=40, verbose=True, time_limit=600, generic=False):
        B = inverse15(rows)
        tt = transform_target(target, B)
        bp = BlockPlan(tt, cb.PARTS5, [], per_coord=True, hmax=76)
        path = descend_smart(bp, seed=seed, per_block=cb.PER_BLOCK, time_limit=600)
        print('   path (sum c: rank/d):', {c: f'{r}/{d}' for c, (R, d, r) in sorted(path.items(), reverse=True)}, f'({time.time()-t0:.0f}s)', flush=True)
        if level not in path:
            return None
        R, d, r = path[level]
        for attempt in range(3):
            if r >= d:
                break
            R, d, r = rank_climb(bp, R, seconds=climb_seconds / 3, seed=seed + 11 + attempt, verbose=False)
            print(f'   climb attempt {attempt}: rank {r}/{d} ({time.time()-t0:.0f}s)', flush=True)
        if r < d or d % 2:
            return None
        cuts = [list(bp.F[i]) + list(R[i]) for i in range(5)]
        F = solve_padding(physical_cuts(cb.PARTS5, cuts, Binv=rows), target[76])
        print(f'   perfect at sum c {NDIM - d} -> products {d // 2}; padding {"ok" if F is not None else "UNSOLVABLE"}', flush=True)
        if F is None:
            return None
        return {'sum_c': NDIM - d, 'rows': rows, 'B': B, 'cuts': cuts, 'F': F, 'd': d}

    cb.plan_one = plan
    return cb.compile_one(W, k, ROOT / outdir, seeds=(seed,))


if __name__ == '__main__':
    a = sys.argv
    r = main(a[1], a[2], a[3], int(a[4]), int(a[5]), climb_seconds=float(a[6]) if len(a) > 6 else 90)
    print('RESULT', json.dumps(r), flush=True)
