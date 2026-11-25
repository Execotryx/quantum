# Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.
"""Own rank-74 low-basis planner for a reordered prefix loader.

Projection-kernel cuts are optional retained structure. Padding, physical
basis conversion, exact matching, original emission and both endpoint proofs
are mandatory before reporting a component.
"""
from pathlib import Path
import sys,json,time,random,hashlib,argparse
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
V=ROOT/'inputs/chem_goal_v18/deliverables/six_cache_words_combined_v18'
sys.path[:0]=[str(ROOT/'scripts'),str(V/'compiler'),str(ROOT/'agents/planner189'),str(ROOT/'inputs/chem_goal_v18/refit')]
from planner import BlockPlan,complete_words,cross_tensor,basis,reduce,proj,physical_cuts,solve_padding,padded_words,NDIM,candidates
from transport_cuts import complete_forced
from minrank import dependencies
from lowbasis import inverse15,transform_target,to_physical
from compile_reordered_prefix import top_sparse_drops,drop
from packed_rank import rank_pairs
from extract_matching import matching
from emit_plan import emit
from prove_loader_branches import prove_one

PARTS=[[3*i+j for j in range(3)] for i in range(5)]

def projection_kernels(full):
    per=[];allv=[]
    for l in range(1,8):
        ds=dependencies([proj(phi,l) for phi in full]);vs=[]
        for dd in ds:
            phi=0
            for i,u in enumerate(full):
                if dd>>i&1:phi^=u
            assert proj(phi,l)==0
            vs.append(phi)
        per.append(vs);allv+=vs
    return per,list(basis(allv).values())

def setup(W,bb,k,forced=True):
    target=cross_tensor(complete_words(np.asarray(W,dtype=np.uint8)),k)
    rows=list(map(int,bb['rows']));B=inverse15(rows);tt=transform_target(target,B)
    bp=BlockPlan(tt,PARTS,[],per_coord=False,hmax=76);info=[]
    for i,full in enumerate(bp.full):
        per,F=projection_kernels(full)
        if not forced:F=[]
        bp.F[i]=F;bp.Q[i]=complete_forced(full,F)
        info.append({'rank':105-len(full),'full_dimension':len(full),'projection_kernel_dimensions':list(map(len,per)),'retained_kernel_span':len(F)})
    return bp,target,rows,B,info

def build(W,state,out):
    out.mkdir(parents=True,exist_ok=True)
    pairs,cert=matching({'parts':PARTS,'cuts':state['cuts']})
    rows=state['rows'];B=state['B'];k=state['k']
    physical=[{'l1':int(to_physical(p[2],B)),'l2':int(to_physical(p[3],B)),'out':int(p[4])} for p in pairs]
    s={'k':k,'explicit_products':physical,'explicit_certificate':dict(cert,method='own rank-74 low basis with optional projection-kernel cuts, balanced sparse descent, physical basis conversion and original exact matching',low_basis_dual_rows=rows,sum_cuts=sum(map(len,state['cuts'])),search=state['search'])}
    WP=padded_words(W,k,state['padding_F'])
    s['padding_completion']={'version':1,'first_unused_address':1220,'word_width':75,'words':WP[1220:].astype(int).tolist(),'real_word_prefix_sha256':hashlib.sha256(np.ascontiguousarray(np.asarray(W,dtype=np.uint8)).tobytes()).hexdigest()}
    source=out/f'angle_k_{k}.kmx';rep=emit(s,complete_words(np.asarray(W,dtype=np.uint8)),source)
    assert rep['product_count']<=215
    proofs=[prove_one(source,W,k,rev) for rev in [False,True]]
    import kickmix as km
    c=km.Circuit.from_file(str(source));binary=out/f'angle_k_{k}.kmb';c.to_file(str(binary),format='kmb')
    assert c.operation_statistics().num_toffoli_like==rep['toffoli_count']
    (out/f'angle_k_{k}.plan_state.json').write_text(json.dumps(s,indent=1)+'\n')
    (out/'all_branch_proof.json').write_text(json.dumps({'status':'PASS','checks':proofs},indent=2)+'\n')
    report=dict(rep,status='NATIVE_COMPONENT_AND_EXACT_SOURCE_PROOF_PASS',kmx_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),kmb_sha256=hashlib.sha256(binary.read_bytes()).hexdigest())
    (out/'native_component_report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('COMPILED',json.dumps(report),flush=True)
    return report

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--k',type=int,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--basis',type=Path,required=True);ap.add_argument('--seed',type=int,default=2718);ap.add_argument('--seconds',type=float,default=400);ap.add_argument('--per-block',type=int,default=5);ap.add_argument('--floor',type=int,default=19);ap.add_argument('--spread',type=int,default=2);ap.add_argument('--tag',default='basis902_forced');ap.add_argument('--free-kernels',action='store_true');ap.add_argument('--from-state',type=Path)
    ap.add_argument('--words',type=Path,default=ROOT/'agents/loaders48/reordered_uncoded15.npz')
    args=ap.parse_args()
    out=args.out;out.mkdir(parents=True,exist_ok=True)
    with np.load(args.words,allow_pickle=False) as word_file:
        W=word_file['words' if 'words' in word_file.files else 'angle_words'].astype(np.int64)
    bb=json.loads(args.basis.read_text())
    prefix=hashlib.sha256(np.ascontiguousarray(W.astype(np.uint8)).tobytes()).hexdigest()
    if 'target_prefix_sha256' in bb:assert prefix==bb['target_prefix_sha256']
    bp,target,rows,B,info=setup(W,bb,args.k,not args.free_kernels)
    print('BASIS',json.dumps(info),flush=True)
    R=[list(x) for x in bp.Q]
    if args.from_state:
        prev=json.loads(args.from_state.read_text());R=[complete_forced(prev['cuts'][i],bp.F[i]) for i in range(5)]
    rng=random.Random(args.seed);t0=time.time();records=[]
    def evalR(R,rank=True):
        cs=[bp.F[i]+R[i] for i in range(5)];ps,_=candidates({'parts':PARTS,'cuts':cs},cs)
        d=NDIM-sum(map(len,cs));sp=len(basis(v for p in ps for v in p[:2]));rk=rank_pairs(ps,rng) if rank else -1
        return d,sp,rk
    d,sp,rk=evalR(R)
    while time.time()-t0<args.seconds:
        cs=[bp.F[i]+R[i] for i in range(5)]
        rec={'seed':args.seed,'cuts':NDIM-d,'dimension':d,'span':sp,'rank':rk,'seconds':time.time()-t0,'block_dimensions':list(map(len,cs))}
        records.append(rec);print(json.dumps(rec),flush=True)
        st={'k':args.k,'parts':PARTS,'cuts':cs,'rows':rows,'B':B,'forced':bp.F,'search':rec,'basis_info':info}
        (out/f'state_{NDIM-d}.json').write_text(json.dumps(st,indent=1)+'\n');(out/'progress.json').write_text(json.dumps(records,indent=2)+'\n')
        if d%2==0 and rk==d:
            F=solve_padding(physical_cuts(PARTS,cs,Binv=rows),target[76])
            if F is not None:
                st['padding_F']=F;(out/'perfect.json').write_text(json.dumps(st,indent=1)+'\n')
                assert d//2<=215
                build(W,st,out/f'compiled_k{args.k}');return
        sizes=list(map(len,cs));pool=[]
        for b in range(5):
            if sizes[b]<=args.floor or sizes[b]<=max(sizes)-args.spread:continue
            pool += [(score,b,y) for score,y in top_sparse_drops(bp,R,b,args.per_block,rng)]
        if not pool:break
        trials=[]
        for sc,b,y in pool:
            rn=[list(x) for x in R];rn[b]=drop(R[b],y);dn,sn,_=evalR(rn,False)
            trials.append((sn,sc,b,y,rn,dn))
        trials.sort(key=lambda x:(x[0],x[1]),reverse=True);best=None
        for sn,sc,b,y,rn,dn in trials[:max(5,args.per_block*2)]:
            _,_,rr=evalR(rn);key=(rr,sn,sc)
            if best is None or key>best[0]:best=(key,rn,dn,sn,rr)
        _,R,d,sp,rk=best
    print('NO_QUALIFIED_PLAN',flush=True)

if __name__=='__main__':main()
