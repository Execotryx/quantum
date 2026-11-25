# SPDX-License-Identifier: Apache-2.0
"""Controlled GF8 leaf without retained three-wire ordinary inverse.

SomeJoint/Nazemtsev: tower/controlled inverse. Own addition: inverse the
masked input in-place, then erase its cubic phase by exact classical repairs.
"""
import os
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
from pathlib import Path
import argparse,gc,inspect,json,sys
ROOT=Path(__file__).resolve().parent;BASE=ROOT

def setup(comp):
    sys.path[:0]=[str(BASE),str(BASE/'dqi'),str(BASE/'dqi/continued_fraction'),str(comp/'kickmix'),str(comp/'verifiers'),str(comp/'verifiers/dqi')]

def inverse8_inplace(b,word):
    """Three conjugated transpositions; zero and one fixed (modulus 0xb)."""
    from tower import elimination_gates
    for a,c in [(2,5),(3,6),(4,7)]:
        delta=a^c;other=next(v for v in range(1,8) if v not in (a,c,delta))
        gates=elimination_gates([delta,other,a^other])
        for op,i,j in gates:getattr(b,op)(word[i],word[j])
        b.ccx(word[1],word[2],word[0])
        for op,i,j in reversed(gates):getattr(b,op)(word[i],word[j])

def erase_combined(b,input,control,m):
    """A three-variable quadratic has rank <=2: one CCZ per nonzero mask."""
    from tower import elimination_gates
    for k,linear in [(0,[0,1,2]),(1,[2]),(2,[1,2])]:
        b.push_condition(m[k])
        for j in linear:b.cz(control,input[j])
        b.pop_condition()
    inv=b.alloc_bits(3);enabled=b.alloc_bits(1)[0]
    for k in range(3):b.bit_store(inv[k],True);b.bit_store(inv[k],False,control=m[k])
    pairs=[(1,2),(0,1),(0,2)]
    for value in range(1,8):
        a,c=next((a,c) for a in range(1,8) for c in range(a+1,8) if all((((a>>j&1)*(c>>k&1))^((a>>k&1)*(c>>j&1)))==(value>>i&1) for i,(j,k) in enumerate(pairs)))
        third=next(v for v in range(1,8) if v not in (a,c,a^c))
        rows=[a,c,third];columns=[sum((v>>j&1)<<i for i,v in enumerate(rows)) for j in range(3)]
        gates=list(reversed(elimination_gates(columns)))
        b.bit_store(enabled,True)
        for k in range(3):b.bit_store(enabled,False,control=inv[k] if value>>k&1 else m[k])
        b.push_condition(enabled)
        # The product's diagonal terms x_i^2=x_i are cancelled separately.
        for j in range(3):
            if (a&c)>>j&1:b.cz(control,input[j])
        for op,j,k in gates:getattr(b,op)(input[j],input[k])
        b.ccz(control,input[0],input[1])
        for op,j,k in reversed(gates):getattr(b,op)(input[j],input[k])
        b.pop_condition()
    b.free(inv);b.free(enabled)

def builder_type(*,combined=False):
    import kickmix as km
    from static_divisions import StaticArithmeticBuilder
    class LeafBuilder(StaticArithmeticBuilder):
        def init_controlled_inverse(self,input,control,*,target='alloc'):
            if len(input)!=3:return super().init_controlled_inverse(input,control,target=target)
            b=self.native;out=b.alloc_qubits(3) if isinstance(target,str) else target
            b.reset(out);b.init_and(control,input,out);inverse8_inplace(b,out)
            return out,km.array([])
        def del_controlled_inverse(self,input,control,*,target,scaffold):
            if len(input)!=3:return super().del_controlled_inverse(input,control,target=target,scaffold=scaffold)
            assert len(scaffold)==0
            b=self.native;m=b.alloc_bits(3);b.hmr(target,m)
            if combined:
                erase_combined(b,input,control,m);b.free(m);return
            # inv8(x): x0+x1+x2+x1*x2, x2+x0*x1, x1+x2+x0*x2.
            for k,linear,pair in [(0,[0,1,2],(1,2)),(1,[2],(0,1)),(2,[1,2],(0,2))]:
                b.push_condition(m[k])
                for j in linear:b.cz(control,input[j])
                b.ccz(control,input[pair[0]],input[pair[1]])
                b.pop_condition()
            b.free(m)
    return LeafBuilder

def fixture(out,*,combined=False):
    import kickmix as km,numpy as np
    rows=[];Builder=builder_type(combined=combined)
    for n in (3,6,12):
        b=Builder();x=b.create_quantum_register(n,'x');ctl=b.create_quantum_register(1,'c')[0]
        y,scaf=b.init_controlled_inverse(x,ctl);forward=b.finish_circuit()
        # finish_circuit returns the current prefix; further operations append.
        b.del_controlled_inverse(x,ctl,target=y,scaffold=scaf);b.free(y+scaf);roundtrip=b.finish_circuit()
        field=km.GF2Field(n);errors=[]
        for seed in (312,987):
            batch=256;sim=km.Simulator(batch_size=batch,seed=seed,counting_operations=True)
            for k in range(0,2*(1<<n),batch):
                code=(np.arange(batch,dtype=np.uint64)+k)%(2<<n);values=code&((1<<n)-1);controls=code>>n
                sim.clear_for_shot();sim.write_across_shots(x,(values[None,:]>>np.arange(n,dtype=np.uint64)[:,None])&1==1);sim.write_across_shots(km.array([ctl]),controls[None,:]==1)
                sim.do(forward);got=sim.read_across_shots(y);want=np.array([field.pow(int(v),(1<<n)-2) if flag else 0 for v,flag in zip(values,controls)],dtype=np.uint64)
                assert np.array_equal(got,(want[None,:]>>np.arange(n,dtype=np.uint64)[:,None])&1==1)
                sim.clear_for_shot();sim.write_across_shots(x,(values[None,:]>>np.arange(n,dtype=np.uint64)[:,None])&1==1);sim.write_across_shots(km.array([ctl]),controls[None,:]==1);sim.do(roundtrip)
                scratch=km.array([km.q(q) for q in range(n+1,roundtrip.num_qubits)])
                assert not sim.read_across_shots(scratch).any()
                assert np.array_equal(sim.read_across_shots(x),(values[None,:]>>np.arange(n,dtype=np.uint64)[:,None])&1==1)
                assert all(sim.read_shot_phase(j)%2==0 for j in range(batch))
        rows.append(dict(degree=n,distinct_inputs=2*(1<<n),seeds=[312,987],forward_qubits=forward.num_qubits,roundtrip_qubits=roundtrip.num_qubits,status='PASS'))
    (out/'leaf_fixture.json').write_text(json.dumps(rows,indent=1));return rows

def build_circuit(*,combined=False):
    import merged_own as M,round6_dqi as R
    from common import build
    from jfraction_gap_decoder import GapJFractionDecoder
    from mask_projection import projected_record
    from round9_pointer import GapStack,convert_short_lifetime,install_compact_scaling
    install_compact_scaling()
    class Decoder(GapJFractionDecoder):
        def build_syndrome_decoding_mbuc(self,builder,*,syndromes,error_mbuc,n_iters):
            b=builder;b.stage_records=[];words=list(syndromes);outcomes=projected_record(b,syndromes,error_mbuc);stack=GapStack(b,older_width=5)
            self._record(b,'initialization');M.extract(b,words,stack,self.field);self._record(b,'moment_to_fraction')
            numerator,denominator=convert_short_lifetime(b,words,stack);self._record(b,'fraction_to_polynomials')
            R.lean_forney(b,numerator,denominator,outcomes,self.field);self._record(b,'phase_correction')
            convert_short_lifetime(b,words,stack,reverse=True);self._record(b,'polynomials_to_fraction')
            M.extract(b,words,stack,self.field,reverse=True);stack.release();self._record(b,'fraction_to_moments')
    b=builder_type(combined=combined)();b.compact_first_division=True;c=build(b,iterations=35,decoder_type=Decoder)
    return c,dict(stages=b.stage_records,method='v12 merged extraction; no ordinary-inverse leaf scaffold')

def main():
    import round10_verify as D
    ap=argparse.ArgumentParser();ap.add_argument('--fixture-only',action='store_true');ap.add_argument('--combined',action='store_true');a=ap.parse_args();setup(D.COMP);D.start_audit()
    D.progress('leaf_fixture');rows=fixture(D.OUT,combined=a.combined);D.progress('leaf_fixture_done',results=rows)
    if not a.fixture_only:
        name='DQI-LEAF-COMBINED' if a.combined else 'DQI-LEAF-OWN';D.progress('build',candidate=name);c,details=build_circuit(combined=a.combined);folder=D.OUT/name;folder.mkdir(exist_ok=True);path=folder/'dqi.kmb';c.to_file(str(path),format='kmb');details.update(num_qubits=c.num_qubits,static_toffoli=c.operation_statistics().num_toffoli_like)
        D.record('build.json',details);del c;gc.collect();D.measure('dqi',path,name)
    D.finish_audit();D.progress('done')
if __name__=='__main__':main()
