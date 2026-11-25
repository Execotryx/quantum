"""Private research adapter for the read/credited paired-v6 source.

Apache-2.0 source lineage: SomeJoint/Agniv Banerjee J-fraction decoder and
field arithmetic; Manwithacat mask projection; Phuc Thai paired extraction
and gap pointers; ViberTeam exact paired-v6 implementation. Upstream NOTICE
and LICENSE are preserved. All imported local public modules were read before
use. Notebook orchestration and its executable cells are never executed.
"""
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
SRC=HERE/'upstream'
DQI=SRC/'upstream/dqi'
sys.dont_write_bytecode=True
sys.path[:0]=[str(SRC),str(DQI),str(DQI/'continued_fraction'),
              str(DQI/'continued_fraction/keyeq'),str(ROOT/'data/comp/kickmix'),
              str(ROOT/'data/comp/verifiers/dqi')]

def make_builder():
    from mc4_inverse import builder_class
    import smallspace_inverse
    from norm_recycle_inverse import init_norm_recycle_inverse
    smallspace_inverse.init_smallspace_inverse=init_norm_recycle_inverse
    return builder_class()()

def build_circuit(*,phase=None,extraction=None,builder=None):
    from functools import partial
    from common import build
    from jfraction_gap_decoder import GapJFractionDecoder
    from mask_projection import projected_record
    from merge_kernels import PointerBank,convert_pointers
    import matrix_pair_kernels
    from phase_tensor import forney_tensor
    matrix_pair_kernels.BORROW_ZERO_META=True
    extract=extraction or partial(matrix_pair_kernels.extract_hybrid,
                                 fused=True,matrix_threshold=14)
    phase=phase or forney_tensor
    class Decoder(GapJFractionDecoder):
        def build_syndrome_decoding_mbuc(self,b,*,syndromes,error_mbuc,n_iters):
            assert len(syndromes)==70 and len(error_mbuc)==4095 and n_iters==35
            residual=projected_record(b,syndromes,error_mbuc)
            b.stage_records=[]
            words=list(syndromes)
            bank=PointerBank(b,35)
            self._record(b,'initialization')
            extract(b,words,bank)
            self._record(b,'moment_to_fraction')
            p,q=convert_pointers(b,words,bank,release_inverse='small')
            self._record(b,'fraction_to_polynomials')
            phase(b,p,q[1:],residual,field=self.field)
            self._record(b,'phase_correction')
            convert_pointers(b,words,bank,reverse=True,release_inverse='small')
            self._record(b,'polynomials_to_fraction')
            extract(b,words,bank,reverse=True)
            bank.release_zero()
            self._record(b,'fraction_to_moments')
    b=builder or make_builder()
    c=build(b,iterations=35,decoder_type=Decoder)
    return c,b.stage_records
