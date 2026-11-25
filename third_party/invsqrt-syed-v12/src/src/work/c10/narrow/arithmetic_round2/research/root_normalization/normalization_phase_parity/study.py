#!/usr/bin/env python3
# Copyright2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Exact normalization-only HMR parity sharing; no native construction."""
from pathlib import Path
import hashlib,importlib.util,json,resource,sys,time
HERE=Path(__file__).resolve().parent;PARENT=HERE.parent;NARROW=HERE.parents[3]
resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,512*1024**2))
for pin in json.loads((HERE/'INPUTS.json').read_text())['files']:
    path=NARROW/pin['path'];raw=path.read_bytes()
    assert len(raw)==pin['bytes']and hashlib.sha256(raw).hexdigest()==pin['sha256'],pin['path']
spec=importlib.util.spec_from_file_location('_rn2d_pinned_forward',PARENT/'leading_one_normalization_v2.py')
baseline=importlib.util.module_from_spec(spec);sys.modules[spec.name]=baseline;spec.loader.exec_module(baseline)
old=baseline.old;km=old.km;cb=old.cb
from thermometer_cleanup import thermometer_matrix

ROWS=thermometer_matrix(10)
CUBIC_ROWS=tuple(j for j,row in enumerate(ROWS,1)if(row>>(7-1))&1)
assert CUBIC_ROWS==(1,3,5,7)
assert all(mask.bit_count()<=2 or mask==7 for row in ROWS for mask in range(1,11)if(row>>(mask-1))&1)


def forward(builder,x,flags):
    x=list(x);flags=list(flags);P=[]
    assert len(x)==22 and len(flags)==4
    for length in range(1,21):
        q=builder.alloc_qubits(1)[0];data=x[22-length]
        if length==1:builder.x(q);builder.cx(data,q)
        elif length==2:builder.cx(P[-1],q);builder.cx(data,q)
        else:builder.x(data);builder.ccx(P[-1],data,q);builder.x(data)
        P.append(q)
    T=P[1::2]
    for bit,flag in enumerate(flags):
        for j in range(1<<bit,11,1<<bit):builder.cx(T[j-1],flag)
    for position in range(2,22):
        for prefix in(21-position,22-position):
            if prefix==0:builder.x(x[position])
            else:builder.cx(P[prefix-1],x[position])
    builder.x(x[21])
    for q in P:builder.cx(q,x[21])
    builder.x(x[1]);builder.ccx(T[-1],x[1],x[21]);builder.x(x[1])
    for target,prefixes in((x[0],P),(x[1],P[:-1])):
        builder.x(target);builder.cx(x[21],target)
        for q in prefixes:builder.cx(q,target)
    baseline.route_lane(builder,x[0::2],T);baseline.route_lane(builder,x[1:21:2],T)
    builder.x(x[20]);builder.cx(x[21],x[20])
    for j in range(1,11):
        q=P[2*j-2];m=builder.alloc_bits(1)[0];builder.hmr(q,m)
        if j==1:cb.emit_phase(builder,[T[0],x[21]],m,old.ODD_FIRST)
        else:cb.emit_phase(builder,[T[j-2],T[j-1],x[21]],m,old.ODD_OTHER)
        builder.free(m);builder.free(q)
    parity=builder.alloc_bits(1)[0];builder.bit_store(parity,False)
    for q,row in zip(T,ROWS):
        outcome=builder.alloc_bits(1)[0];builder.hmr(q,outcome)
        builder.push_condition(outcome)
        for mask in range(1,11):
            if ((row>>(mask-1))&1)==0 or mask==7:continue
            controls=[flags[i]for i in range(4)if(mask>>i)&1]
            if len(controls)==1:builder.z(controls[0])
            else:assert len(controls)==2;builder.cz(*controls)
        builder.pop_condition()
        if(row>>(7-1))&1:builder.cx(outcome,parity)
        builder.free(outcome);builder.free(q)
    builder.push_condition(parity);builder.ccz(*flags[:3]);builder.pop_condition();builder.free(parity)


class TranscriptBuilder(old.TruthPhaseBuilder):
    """Expand every classical parity into independent original HMR symbols."""
    def __init__(self,cap,full,valid):
        super().__init__(cap,full,valid);self.classical={};self.classical_xors=0;self.charged_condition_masks=[]
    def alloc_bits(self,n):
        bits=super().alloc_bits(n)
        for bit in bits:self.classical[bit]=0
        return bits
    def bit_store(self,bit,value):
        assert not self.stack and isinstance(bit,km.b)and value is False
        self.classical[bit]=0
    def free(self,value):
        if isinstance(value,km.b):self.classical.pop(value,None)
        return super().free(value)
    def cx(self,a,target):
        if isinstance(target,km.b):
            assert not self.stack and isinstance(a,km.b)
            self.classical[target]^=self.classical[a];self.classical_xors+=1
        else:super().cx(a,target)
    def hmr(self,q,outcome):
        assert not self.stack
        symbol=self.measurements;self.measurements+=1
        self.classical[outcome]=1<<symbol
        self.phases[symbol]=self.phases.get(symbol,0)^self.value(q);self.values[q]=0
    def _phase(self,value,extra=None):
        active=set(self.stack)
        if extra is not None:active.add(extra)
        assert len(active)<=1,'Only one affine classical condition is in this component.'
        if not active:self.phases[None]=self.phases.get(None,0)^value;return
        mask=self.classical[next(iter(active))]
        while mask:
            low=mask&-mask;symbol=low.bit_length()-1
            self.phases[symbol]=self.phases.get(symbol,0)^value;mask^=low
    def _charge(self,n=1):
        conditions=set(self.stack);assert len(conditions)<=1
        if conditions:
            mask=self.classical[next(iter(conditions))]
            assert mask,'A charged condition must be a nonzero affine combination of independent outcomes.'
            self.charged_condition_masks.append(mask)
        return super()._charge(n)


def transcript_selftest():
    records=[]
    for omit_second in(False,True):
        b=TranscriptBuilder(4,3,3);source,t0,t1=list(b.alloc_qubits(3));b.values[source]=2
        b.cx(source,t0);b.cx(source,t1)
        m0,m1,parity=list(b.alloc_bits(3));b.hmr(t0,m0);b.hmr(t1,m1)
        b.bit_store(parity,False);b.cx(m0,parity)
        if not omit_second:b.cx(m1,parity)
        assert b.classical[parity]==(1 if omit_second else 3)
        b.push_condition(parity);b.z(source);b.pop_condition()
        nonzero=[symbol for symbol,value in b.phases.items()if value&b.valid]
        if omit_second:assert nonzero==[1]
        else:b.check_phase()
        records.append(dict(omitted_second_outcome=omit_second,unpaid_symbols=nonzero))
    return dict(status='PASS_POSITIVE_AND_NEGATIVE_CLASSICAL_XOR_SYMBOL_TEST',records=records)


def certify():
    began=time.monotonic();size=1<<22;full=(1<<size)-1;valid=(1<<(old.MAX_X+1))-2
    source=old.input_truths();b=TranscriptBuilder(48,full,valid)
    x=list(b.alloc_qubits(22));flags=list(b.alloc_qubits(4))
    for q,value in zip(x,source):b.values[q]=value
    expected=[0]*22;expected_flags=[0]*4
    for k in range(11):
        lo=1<<(20-2*k);hi=min(old.MAX_X+1,1<<(22-2*k));mask=((1<<hi)-(1<<lo))if hi>lo else 0
        for i in range(2*k,22):expected[i]^=mask&source[i-2*k]
        for bit in range(4):
            if(k>>bit)&1:expected_flags[bit]^=mask
    forward(b,x,flags)
    assert all((b.value(q)^wanted)&valid==0 for q,wanted in zip(x,expected))
    assert all((b.value(q)^wanted)&valid==0 for q,wanted in zip(flags,expected_flags))
    assert b.num_allocated_qubits==26 and b.measurements==20;b.check_phase()
    f=float(b.count);fp=b.peak;fm=b.measurements;forward_masks=list(b.charged_condition_masks)
    assert len(forward_masks)==1 and forward_masks[0].bit_count()==4
    b.peak=26;old.inverse(b,x,flags)
    assert all((b.value(q)^wanted)&valid==0 for q,wanted in zip(x,source))
    assert all(b.value(q)&valid==0 for q in flags)
    assert b.num_allocated_qubits==26 and b.measurements==30;b.check_phase()
    assert(f,float(b.count),fp,b.peak)==(51.5,96,46,32)
    return dict(status='PASS_PURE_BOOLEAN_ALL_ORIGINAL_INPUTS_ALL_ORIGINAL_HMR_SYMBOLS_NOT_NATIVE',
                original_inputs=old.MAX_X,forward_E=f,unchanged_inverse_E=float(b.count)-f,total_E=float(b.count),
                modeled_forward_peak=fp,modeled_inverse_peak=b.peak,forward_HMR_symbols=fm,total_HMR_symbols=b.measurements,
                forward_charged_condition_HMR_masks=forward_masks,all_charged_conditions_nonzero_affine=True,
                cubic_outcomes_merged=4,all_original_owners_restored=True,all_scratch_flags_zero=True,
                every_independent_HMR_coefficient_zero=True,mathematical_phase_error=0,T=0,R=0,
                seconds=time.monotonic()-began,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)


def main():
    result=dict(status='NORMALIZATION_SHARED_CUBIC_PAPER_GATE',selftest=transcript_selftest(),certificate=certify(),
                cubic_thresholds=CUBIC_ROWS,threshold_ANF_rows=ROWS,native_execution=False,official_execution=False,
                source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                inputs_sha256=hashlib.sha256((HERE/'INPUTS.json').read_bytes()).hexdigest(),
                complete_delta=dict(relative_to_native_RN2B=-0.5,full_Q=48,full_Toffolis_vs_frozen08=1568.0,
                    full_expected_cost_vs_frozen08=48*(1568.0+1+230.84805946161188),
                    RN2C_combination_not_executed_or_credited=True))
    path=HERE/'study.json'
    with path.open('x')as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
