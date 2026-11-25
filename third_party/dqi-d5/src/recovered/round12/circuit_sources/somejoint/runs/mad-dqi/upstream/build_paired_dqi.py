"""Paired source decoder plus unchanged FULL official verification wrapper."""
import build_merge_dqi as verification

def build_circuit(variant='paired-v1'):
    from common import build
    from static_divisions import StaticArithmeticBuilder
    from jfraction_gap_decoder import GapJFractionDecoder
    from mask_projection import projected_record
    from merge_kernels import PointerBank,convert_pointers
    from paired_kernels import extract_paired
    from phase_tensor import forney_tensor
    if variant in ('paired-v3','paired-v4','paired-v5','paired-v6'):
        from matrix_pair_kernels import extract_hybrid as extract_paired
        if variant in ('paired-v4','paired-v5','paired-v6'):
            from functools import partial
            extract_paired=partial(extract_paired,fused=True)
            if variant=='paired-v6':
                import matrix_pair_kernels
                matrix_pair_kernels.BORROW_ZERO_META=True
                extract_paired=partial(extract_paired,matrix_threshold=14)
        from mc4_inverse import builder_class
        StaticArithmeticBuilder=builder_class()
        if variant in ('paired-v5','paired-v6'):
            import smallspace_inverse
            from norm_recycle_inverse import init_norm_recycle_inverse
            smallspace_inverse.init_smallspace_inverse=init_norm_recycle_inverse
    elif variant!='paired-v1':
        from one_mask_inverse import builder_class
        StaticArithmeticBuilder=builder_class()
    class PairedDecoder(GapJFractionDecoder):
        def build_syndrome_decoding_mbuc(self,builder,*,syndromes,error_mbuc,n_iters):
            assert len(syndromes)==70 and len(error_mbuc)==4095 and n_iters==35
            residual=projected_record(builder,syndromes,error_mbuc)
            builder.stage_records=[];words=list(syndromes);bank=PointerBank(builder,35)
            self._record(builder,'initialization')
            extract_paired(builder,words,bank)
            self._record(builder,'moment_to_fraction')
            p,q=convert_pointers(builder,words,bank,release_inverse='small')
            self._record(builder,'fraction_to_polynomials')
            forney_tensor(builder,p,q[1:],residual,field=self.field)
            self._record(builder,'phase_correction')
            convert_pointers(builder,words,bank,reverse=True,release_inverse='small')
            self._record(builder,'polynomials_to_fraction')
            extract_paired(builder,words,bank,reverse=True);bank.release_zero()
            self._record(builder,'fraction_to_moments')
    b=StaticArithmeticBuilder();c=build(b,iterations=35,decoder_type=PairedDecoder)
    return c,dict(variant=variant,stages=b.stage_records,
        extraction='exact two-level output equivalence, including zero pivots; adaptive small-tail threshold',
        history='inherited two 6-bit pointers, exact for <=2 first-order gaps',
        attribution='SomeJoint/Agniv Banerjee decoder; Manwithacat mask projection; Phuc Thai EXP-119a paired idea; ViberTeam independent source and exact zero-pivot extension')

def main():
    verification.build_circuit=build_circuit
    verification.main()

if __name__=='__main__':main()
