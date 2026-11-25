"""Source build + unchanged full official DQI verifier on a large-memory CPU."""
import argparse
import gc
import json
import os
import platform
import sys
import time
from pathlib import Path

from build_projected_dqi import HERE, PROJECT, SALT, authenticate, load_runtime, sha256, write_json

OFFICIAL_SHA='f14274bc0943fb9769ddb01131be6063191a15009fe1caf1d4bdd9fd25194e65'


def build_circuit(variant='merge-v1'):
    from common import build
    from static_divisions import StaticArithmeticBuilder, StaticDivisionDecoder
    from jfraction_gap_decoder import GapJFractionDecoder
    from mask_projection import projected_record
    from merge_kernels import PointerBank, extract_pointers, forney_lean, convert_pointers
    release_inverse='norm' if variant in ('merge-v3-norm','merge-exact-history','merge-exact-terminal') else variant=='merge-v2-tensor'
    exact_history=variant in ('merge-exact-history','merge-exact-terminal')
    terminal=variant=='merge-exact-terminal'
    if exact_history:
        from compact_gap_variant import GapBank
        from merge_kernels import extract_exact_late,convert_exact_late
        if terminal:
            from merge_kernels import terminal_zero_bank_class
            GapBank=terminal_zero_bank_class()
    if release_inverse:
        from phase_tensor import forney_tensor
    forney=forney_tensor if release_inverse else forney_lean
    class MergedDecoder(GapJFractionDecoder):
        def build_syndrome_decoding_mbuc(self,builder,*,syndromes,error_mbuc,n_iters):
            assert len(syndromes)==70 and len(error_mbuc)==4095 and n_iters==35
            residual=projected_record(builder,syndromes,error_mbuc)
            builder.stage_records=[]
            words=list(syndromes)
            bank=GapBank(builder,35) if exact_history else PointerBank(builder,35)
            self._record(builder,'initialization')
            if exact_history:extract_exact_late(builder,words,bank,inverse_mode=release_inverse,qubit_cap=898 if terminal else None)
            else:extract_pointers(builder,words,bank,release_inverse=release_inverse)
            self._record(builder,'moment_to_fraction')
            if exact_history:p,q=convert_exact_late(builder,words,bank,inverse_mode=release_inverse)
            else:p,q=convert_pointers(builder,words,bank,release_inverse=release_inverse)
            self._record(builder,'fraction_to_polynomials')
            forney(builder,p,q[1:],residual,field=self.field)
            self._record(builder,'phase_correction')
            if exact_history:convert_exact_late(builder,words,bank,reverse=True,inverse_mode=release_inverse)
            else:convert_pointers(builder,words,bank,reverse=True,release_inverse=release_inverse)
            self._record(builder,'polynomials_to_fraction')
            if exact_history:extract_exact_late(builder,words,bank,reverse=True,inverse_mode=release_inverse,qubit_cap=898 if terminal else None,retire=terminal)
            else:extract_pointers(builder,words,bank,reverse=True,release_inverse=release_inverse)
            bank.release_zero()
            self._record(builder,'fraction_to_moments')
    b=StaticArithmeticBuilder()
    c=build(b,iterations=35,decoder_type=MergedDecoder)
    return c,{'variant':variant,'stages':b.stage_records,
              'history':('exact 4->3 codec, omit provably terminal zero flag' if terminal else 'exact 4->3 no-adjacent codec') if exact_history else 'two 6-bit pointers, exact for <=2 first-order gaps',
              'attribution':'SomeJoint/Agniv Banerjee; Manwithacat; Phuc Thai EXP-118c idea; ViberTeam independent implementation'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--official-root',type=Path,default=PROJECT/'data/competition')
    parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--variant',default='paired-v1',choices=('paired-v1','paired-v2','paired-v3','paired-v4','paired-v5','paired-v6','merge-v1','merge-v2-tensor','merge-v3-norm','merge-exact-history','merge-exact-terminal'))
    parser.add_argument('--workers',type=int,default=2)
    parser.add_argument('--build-only',action='store_true')
    args=parser.parse_args()
    assert args.workers in (1,2)
    # Explicitly disallow a full local build, even if invoked accidentally.
    assert str(Path.cwd()).startswith('/kaggle/'), 'Full source builds are Kaggle-only in this task.'
    authenticate(HERE/'upstream/dqi')
    km,verifier,_=load_runtime(args.official_root,HERE/'upstream/dqi')
    assert sha256(Path(verifier.__file__))==OFFICIAL_SHA
    output=args.output_dir.resolve();output.mkdir(parents=True,exist_ok=True)
    started=time.monotonic()
    print('MERGE_SOURCE_BUILD_START',args.variant,flush=True)
    c,details=build_circuit(args.variant)
    stats=c.operation_statistics()
    assert 'Z_POW' not in stats
    spec=verifier.ProblemSpecDQI.benchmark_instance()
    verifier.validate_registers(c,spec)
    path=output/'dqi.kmb'
    c.to_file(str(path),format='kmb')
    digest=sha256(path)
    receipt={'status':'BUILT_NOT_VERIFIED','classification':'partial/resource count',
        'Q':c.num_qubits,'static_T':stats.num_toffoli_like,'num_ops':len(c),'num_bits':c.num_bits,
        'circuit_sha256':digest,'bytes':path.stat().st_size,'build_seconds':time.monotonic()-started,
        **details}
    write_json(output/'dqi_build.json',receipt)
    print(json.dumps(receipt,indent=2),flush=True)
    gc.collect()
    if args.build_only:return
    assert (spec.m,spec.n,spec.degree,spec.r,spec.num_shots)==(4095,70,12,2016,102400)
    assert verifier.DEFAULT_BATCH_SIZE==256 and verifier.DEFAULT_LOG2_DELTA==-128.0
    started=time.monotonic()
    print('FULL_OFFICIAL_102400_START',flush=True)
    try:
        report=verifier.verify(c,spec,salt=SALT,seed=None,batch_size=256,
                              log2_delta=-128.0,max_workers=args.workers)
    except Exception as error:
        write_json(output/'FAIL_REPORT.json',{'status':'FAIL','error':repr(error),
            'circuit_sha256':digest,'seconds':time.monotonic()-started})
        raise
    assert report['verified_shots']==102400 and report['circuit_sha256']==digest
    report['classification']='FULL-PASS'
    report['verification_context']={'fresh':True,'salt':SALT,'seed':None,'batch_size':256,
        'log2_delta':-128.0,'max_workers':args.workers,'official_verifier_sha256':OFFICIAL_SHA,
        'verification_seconds':time.monotonic()-started,'python':sys.version,'platform':platform.platform(),
        'kernel_ref':os.environ.get('VQCC_KERNEL_REF'),'kernel_version':os.environ.get('VQCC_KERNEL_VERSION'),
        'variant':args.variant,'source_built':True,'pregenerated_shots':False}
    report['Q']=report['num_qubits'];report['meanT']=report['toffoli_count']
    report['eps_plus']=report['effective_error_rate'];report['R']=report['repetition_factor']
    report['cost']=report['score']
    write_json(output/'PASS_REPORT.json',report)
    print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':main()
