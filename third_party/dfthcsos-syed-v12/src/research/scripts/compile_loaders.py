# Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.
"""Plan, match, emit and prove new loaders for a candidate word table (our own driver).

Uses the v18 portable compiler (emit_plan.emit, extract_matching.matching) unchanged.
Each new loader gets a plan with literal parts, cuts and explicit products, so the
rebuild never reruns a randomized search.
"""
import sys, time, json, hashlib, random
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
V18 = ROOT / 'inputs/chem_goal_v18/deliverables/six_cache_words_combined_v18'
sys.path.insert(0, str(V18 / 'compiler'))
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'inputs/chem_goal_v18/refit'))
from planner import BlockPlan, complete_words, REL_LSB, REL_P1, cross_tensor, NDIM, local_search, top_down
from extract_matching import matching
from emit_plan import emit
from prove_loader_branches import prove_one

MODES = ('top-down',)
SCREEN_N, SCREEN_KEEP = 150, 3


def screen_parts(target, rels, n=150, keep=3, seed=11):
    from planner import basis, candidates
    rng = random.Random(seed)
    LIN = [0, 1, 3, 7]; NL = [i for i in range(15) if i not in LIN]
    res = []
    for it in range(n):
        nl = NL[:]; rng.shuffle(nl)
        pts = [[LIN[i], nl[2 * i], nl[2 * i + 1]] for i in range(4)] + [nl[8:11]]
        bp = BlockPlan(target, pts, rels, per_coord=True)
        full = [list(basis(f).values()) for f in bp.full]
        pairs, _ = candidates({'parts': pts, 'cuts': full}, full)
        sp = len(basis([x for p in pairs for x in p[:2]]))
        res.append((sp - (NDIM - sum(map(len, full))), pts))
    res.sort(key=lambda x: -x[0])
    return [r[1] for r in res[:keep]]
PARTS = {k: json.loads((V18 / f'plans/angle_k_{k}.json').read_text()).get('parts') for k in range(8, 15)}


def compile_one(W, k, outdir, parts=None, nrel=6, time_limit=900, seed=1, verbose=True):
    Wc = complete_words(W.astype(np.uint8))
    target = cross_tensor(Wc, k)
    rels = REL_LSB + ([REL_P1] if nrel == 6 else [])
    cand_parts = [parts] if parts else screen_parts(target, rels, n=SCREEN_N, keep=SCREEN_KEEP)
    best = None
    for pi, pts in enumerate(cand_parts):
        bp = BlockPlan(target, pts, rels, per_coord=True)
        if verbose:
            print(f'k{k} parts {pts} F {[len(f) for f in bp.F]} full {[len(f) for f in bp.full]}', flush=True)
        for mode in MODES:
            if mode == 'bottom-up':
                c0 = bp.greedy(seed=seed, time_limit=150, verbose=False, extra_random=0)
            else:
                c0 = top_down(bp, seed=seed + 5, trials=40, verbose=False, time_limit=200)
            if c0 is None:
                continue
            bp.best = c0
            c1 = local_search(bp, c0, seconds=time_limit, seed=seed + 11, verbose=False)
            sc = sum(map(len, c1))
            if verbose:
                print(f'   {mode}: start {sum(map(len, c0))} -> LS {sc} (products {(NDIM - sc) // 2})', flush=True)
            if best is None or sc > best[0]:
                best = (sc, c1, pts)
    if best is None:
        return None
    _, cuts, parts = best
    s = {'k': k, 'parts': parts, 'cuts': cuts}
    t = time.time()
    pairs, cert = matching(s)
    s['explicit_products'] = [{'l1': int(p[2]), 'l2': int(p[3]), 'out': int(p[4])} for p in pairs]
    s['explicit_certificate'] = dict(cert, method='own greedy block-cut planner + v18 matching',
                                     relations=[int(r) for r in rels], sum_cuts=sum(map(len, cuts)))
    outdir.mkdir(parents=True, exist_ok=True)
    kmx = outdir / f'angle_k_{k}.kmx'
    rep = emit(s, Wc, kmx)
    proofs = [prove_one(kmx, np.asarray(W, dtype=np.int64), k, rev) for rev in (False, True)]
    s['report'] = rep
    (outdir / f'angle_k_{k}.plan_state.json').write_text(json.dumps(s, indent=1) + '\n')
    res = {'k': k, 'products': rep['product_count'], 'toffoli': rep['toffoli_count'], 'qubits': rep['num_qubits'],
           'sum_cuts': sum(map(len, cuts)), 'proof_toffoli': proofs[0]['toffoli_count'],
           'proof_hmr': proofs[0]['independent_HMR_variables'], 'kmx_sha256': proofs[0]['source_sha256'],
           'match_seconds': round(time.time() - t, 1)}
    if verbose:
        print('COMPILED', json.dumps(res), flush=True)
    return res


if __name__ == '__main__':
    cand = np.load(ROOT / sys.argv[1])
    W = cand['words'] if 'words' in cand.files else cand['angle_words']
    outdir = ROOT / sys.argv[2]
    ks = [int(x) for x in sys.argv[3].split(',')]
    tl = float(sys.argv[4]) if len(sys.argv) > 4 else 900
    nrel = int(sys.argv[5]) if len(sys.argv) > 5 else 6
    out = []
    for k in ks:
        r = compile_one(W, k, outdir, time_limit=tl, nrel=nrel)
        out.append(r)
        (outdir / 'compile_summary.json').write_text(json.dumps(out, indent=1) + '\n')
