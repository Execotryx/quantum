#!/usr/bin/env python3
# Copyright2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Authorized coefficient-top component: native text/all-HMR and sampled runtime."""
from pathlib import Path
import hashlib,importlib.util,json,os,resource,sys,time
HERE=Path(__file__).resolve().parent;NARROW=HERE.parents[2]
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
assert resource.getrlimit(resource.RLIMIT_AS)[1]==512*1024**2,'Fresh512MiB guard required'
resource.setrlimit(resource.RLIMIT_CPU,(90,90))
AUTH=NARROW/'arithmetic_round2/receipts/COEFFICIENT_TOP_PAPER_ACCEPTED.json'
auth=json.loads(AUTH.read_text())
assert auth['status']=='PAPER_GATE_ACCEPTED_COMPONENT_NATIVE_PROOF_AUTHORIZED'
assert auth['paper_sha256']==hashlib.sha256((HERE/'TOP_TRANSFER_PAPER.json').read_bytes()).hexdigest()
sys.path.insert(0,str(NARROW/'native/candidate01'))
import common
from common import km,array,with_registers,MODEL
assert hashlib.sha256((NARROW/'native/candidate01/lifecycle.py').read_bytes()).hexdigest()=='47b73f1f24ea027eedcbd1950cde7fc2535b32afeeb2e366ebdc4b6f1eb3c068'
spec=importlib.util.spec_from_file_location('round2_baseline_coefficient_lifecycle',NARROW/'native/candidate01/lifecycle.py')
lc=importlib.util.module_from_spec(spec);sys.modules[spec.name]=lc;spec.loader.exec_module(lc)
import native_transfer as new
from component_text_proof import prove_native_text
from branch_prover import generated_text
import numpy as np


def packed(values):return sum((int(v)&1)<<i for i,v in enumerate(values))
def functions(words,width):return[packed(int(v)>>i for v in words)for i in range(width)]
def bits(values,width):return((np.asarray(values,dtype=np.uint64)[None,:]>>np.arange(width,dtype=np.uint64)[:,None])&1).astype(bool)
def read(sim,wires):return(sim.read_across_shots(array(wires)).astype(np.uint64)<<np.arange(len(wires),dtype=np.uint64)[:,None]).sum(axis=0)


def row_fixture(negative=None):
    b=km.CircuitBuilder();b.set_max_qubits(24)
    src=list(b.alloc_qubits(5));target=list(b.alloc_qubits(7));cin,sign=b.alloc_qubits(2)
    original=src+target+[cin,sign]
    saved=b.alloc_qubits(1)[0];b.cx(target[6],saved)
    for q in target:b.cx(sign,q)
    debt=lc.ar.forward_add(b,src,target,carry_in=cin)
    for q in target:b.cx(sign,q)
    m=b.alloc_bits(1)[0];b.hmr(target[6],m);b.cx(saved,target[6]);b.cx(target[6],saved);b.free(saved)
    for q in target[:6]:b.cx(sign,q)
    new.inverse_low6(b,src,target[:6],debt,carry_in=cin,top_outcome=m,ar=lc.ar,omit_wrap=negative=='wrap')
    for q in target[:6]:b.cx(sign,q)
    if negative=='saved':b.free(m)
    else:lc.ar.repay_saved_bit(b,target[6],m)
    assert b.num_allocated_qubits==14 and debt.consumed and not debt.measurements
    c=with_registers(b.finish_circuit(),{'inputs':original})
    assert c.operation_statistics().num_toffoli_like==11
    return c


def full_fixture(negative=None):
    # The13 original-A anchor wires are fixture-only. Subtract13 from each
    # allocation cut to obtain the production arithmetic budget. Fifteen
    # unchanged spectators are fully symbolic; five additional zero owners
    # reproduce the first/second preparation occupancy and are released only
    # when the real product/seed schedule has released its extra five owners.
    b=km.CircuitBuilder();b.set_max_qubits(61)
    roots=list(b.alloc_qubits(6));H=list(b.alloc_qubits(5));anchor=list(b.alloc_qubits(13))
    spectators=list(b.alloc_qubits(15));idle=list(b.alloc_qubits(5))
    original=roots+H+anchor;v=roots[:5]+[None]*3+[roots[5]]+[None]*3
    D=list(b.alloc_qubits(13))
    for a,d in zip(anchor,D):b.cx(a,d)
    assert b.num_allocated_qubits==57
    first=lc.coefficient_forward(b,v,D,H)
    first_snapshot=lc.ar.release_saved_bit(b,first.saved_bit);first.saved_bit=None
    first_D=[]
    for q in D:
        m=b.alloc_bits(1)[0];b.hmr(q,m);b.free(q);first_D.append(m)
    D=list(b.alloc_qubits(13))
    for a,d in zip(anchor,D):b.cx(a,d)
    lc.ar.repay_saved_bit(b,D[6],first_snapshot)
    second=lc.coefficient_forward(b,v,D,H)
    prefix=b.finish_circuit();prefix_wires=D[:]
    for q,m in zip(D,first_D):
        b.push_condition(m);b.z(q);b.pop_condition();b.free(m)
    lc.merge_coefficient_transcripts(b,first,second)
    b.free(array(idle));assert b.num_allocated_qubits==53
    before=b.finish_circuit().operation_statistics().num_toffoli_like
    new.coefficient_inverse(b,v,D,H,second,spectators,baseline=lc,
                            omit_wrap=negative=='wrap',omit_saved=negative=='saved')
    after=b.finish_circuit().operation_statistics().num_toffoli_like
    assert after-before==36 and b.num_allocated_qubits==52
    for a,d in zip(anchor,D):b.cx(a,d)
    b.free(array(D));assert b.num_allocated_qubits==39
    for token in(first,second):
        assert token.saved_bit is None
        assert all(d.consumed and not d.measurements for d in token.row_debts)
        assert token.overflow_debt.consumed and not token.overflow_debt.measurements
    c=with_registers(b.finish_circuit(),{'inputs':original,'spectators':spectators})
    assert c.operation_statistics().num_toffoli_like==118 and c.num_qubits==61
    return c,original,spectators,prefix,prefix_wires


def run_native(circuit,original,spectators,prefix,prefix_wires,rows):
    checks=[]
    for seed in(0,1,2,3):
        sim=km.Simulator(batch_size=256,counting_operations=True,seed=seed)
        forward=km.Simulator(batch_size=256,counting_operations=True,seed=seed+81)
        for first in range(0,4096,256):
            words=np.asarray(rows[first:first+256],dtype=np.uint64)
            spec=(np.arange(first,first+256,dtype=np.uint64)*4051+seed*91)&32767
            for obj in(sim,forward):
                obj.clear_for_shot();obj.write_across_shots(array(original),bits(words,24));obj.write_across_shots(array(spectators),bits(spec,15))
            forward.do(prefix)
            assert np.array_equal(read(forward,prefix_wires),np.asarray(MODEL['D'][first:first+256],dtype=np.uint64)),'Coefficient value differs'
            sim.do(circuit)
            assert np.array_equal(read(sim,original),words),'Original inputs differ'
            assert np.array_equal(read(sim,spectators),spec),'Spectators differ'
            keep=set(original+spectators);scratch=[km.q(i)for i in range(circuit.num_qubits)if km.q(i)not in keep]
            assert not sim.read_across_shots(array(scratch)).any(),'Nonzero scratch'
            assert all(sim.read_shot_phase(i)%2==0 for i in range(256)),'Native phase differs'
        sampled=sim.operation_statistics().num_toffoli_like/4096
        assert sampled==118
        checks.append(dict(seed=seed,shots=4096,all4096_model_roots=True,status='PASS',sampled_mean_Toffolis=sampled))
    return checks


def main():
    began=time.monotonic();out=HERE/'top_transfer_native';out.mkdir(exist_ok=False)
    row=row_fixture();row_text=generated_text(row)
    row.to_file(str(out/'row.kmb'),format='kmb');(out/'row.kmx').write_text(row_text)
    row_functions=functions(range(16384),14)
    row_proof=prove_native_text(row_text,row_functions,16384)
    rows=[]
    for v in range(4096):
        a=v>>5;R=((v>>8)^(v>>7)^(((v>>6)&1)*(((v>>7)^(v>>10))&1)))&1
        roots=(v&31)|(R<<5);H=MODEL['stored_slope'][a];A=MODEL['A'][a]
        rows.append(roots|(H<<6)|(A<<11))
    c,original,spectators,prefix,prefix_wires=full_fixture();text=generated_text(c)
    c.to_file(str(out/'coefficient_two_forward_inverse.kmb'),format='kmb');(out/'coefficient_two_forward_inverse.kmx').write_text(text)
    proof=prove_native_text(text,functions(rows,24),4096)
    negatives=[]
    for missing in('wrap','saved'):
        for kind,builder,truths,count in [('row',row_fixture,row_functions,16384),('two_forward',lambda x:full_fixture(x)[0],functions(rows,24),4096)]:
            bad=generated_text(builder(missing))
            try:prove_native_text(bad,truths,count)
            except AssertionError as e:
                assert 'phase' in str(e).lower(),str(e)
                negatives.append(dict(case=kind,omitted=missing,status='REJECTED_PHASE_WITH_DATA_AND_SCRATCH_PRESERVED',message=str(e)))
            else:raise AssertionError('Negative phase control unexpectedly passed')
    checks=run_native(c,original,spectators,prefix,prefix_wires,rows)
    result=dict(status='PASS_NATIVE_COEFFICIENT_TOP_COMPONENT_ALL_HMR_NOT_FULL_INVSQRT',
        complete_paper_receipt_sha256=auth['paper_sha256'],root_authorization_sha256=hashlib.sha256(AUTH.read_bytes()).hexdigest(),
        adapter_sha256=hashlib.sha256((HERE/'native_transfer.py').read_bytes()).hexdigest(),
        checker_sha256=hashlib.sha256((HERE/'component_text_proof.py').read_bytes()).hexdigest(),
        proof_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        native_row_proof=row_proof,native_two_forward_inverse_proof=proof,
        two_independent_forward_transcripts_preserved=True,all_12_paired_debts_consumed_once=True,
        original_model_source_sha256=common.MODEL_SHA,negative_tests=negatives,native_runtime_checks=checks,
        fixture_peak=61,fixture_extra_original_A_anchor_wires=13,production_arithmetic_peak=48,
        inverse_production_peak_bound=45,expected_Toffolis=118,baseline_Toffolis=123,saving_E=5,T=0,R=0,
        original_accuracy_unchanged=True,endpoint_loaders_and_external_cleanups_unchanged=True,
        full_native_qualification=False,official_verified=False,
        elapsed_seconds=time.monotonic()-began,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    result['files']=[dict(path=p.name,bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())for p in sorted(out.iterdir())]
    (out/'PROOF.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
