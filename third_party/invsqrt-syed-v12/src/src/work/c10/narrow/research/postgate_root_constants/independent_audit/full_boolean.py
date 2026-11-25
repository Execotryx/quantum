#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0
# Credits: Opus and Astra.
"""All normalized inputs and all local HMR signs of the specialized root.

Pure bit-parallel source execution, no native CircuitBuilder or simulator.
Each adder fits a single segment at Q49; every del_and measurement is checked
against its complete Clifford correction before resetting/releasing its owner.
"""
from audit import *
import numpy as np,time


class BooleanBuilder:
    def __init__(self,count):
        self.max_qubits=49;self.full=(1<<count)-1;self.live=set();self.pool=[]
        self.nextq=0;self.values={};self.peak=0;self.Toffolis=0;self.HMR=0
    @property
    def num_allocated_qubits(self):return len(self.live)
    def alloc_qubits(self,n):
        assert len(self.live)+n<=self.max_qubits
        out=[]
        for _ in range(n):
            if self.pool:q=self.pool.pop()
            else:q=km.q(self.nextq);self.nextq+=1
            self.live.add(q);self.values[q]=0;out.append(q)
        self.peak=max(self.peak,len(self.live));return km.array(out)
    def free(self,wires):
        if isinstance(wires,km.q):
            assert wires in self.live and self.values[wires]==0,('nonzero owner release',str(wires))
            self.live.remove(wires);self.pool.append(wires)
        else:
            for q in wires:self.free(q)
    def value(self,q):return self.full if q is True else 0 if q is False else self.values[q]
    def x(self,wires):
        if isinstance(wires,km.q):self.values[wires]^=self.full
        else:
            for q in wires:self.x(q)
    def cx(self,control,target):
        if isinstance(target,km.q):self.values[target]^=self.value(control)
        else:
            for q in target:self.cx(control,q)
    def ccx(self,a,b,t):self.values[t]^=self.value(a)&self.value(b);self.Toffolis+=1
    def del_and(self,a,b,t):
        assert self.values[t]==self.value(a)&self.value(b),('unpaid HMR sign',str(a),str(b),str(t))
        self.values[t]=0;self.HMR+=1
    def alloc_bits(self,n):raise AssertionError('Unexpected segmented adder: all HMR phases must be proved explicitly.')


def pack(values):return int.from_bytes(np.packbits(np.asarray(values,dtype=np.uint8),bitorder='little').tobytes(),'little')


def main():
    began=time.monotonic();checked=0;sign_checks=0;rows=[]
    for first in range(1<<20,1<<22,65536):
        values=np.arange(first,min(1<<22,first+65536),dtype=np.int64)
        b=BooleanBuilder(len(values));norm=list(b.alloc_qubits(22));flags=list(b.alloc_qubits(4))
        for i,q in enumerate(norm):b.values[q]=pack((values>>i)&1)
        for i,q in enumerate(flags):b.values[q]=pack((values>>(i+1))&1)
        original=[b.values[q]for q in norm];flag_values=[b.values[q]for q in flags]
        indices=iter(range(1,13))
        def intercept(builder,remainder,older,sign,*,initial=False,inverse=False):
            j=next(indices)
            if j>=11:
                expected=builder.full if inverse else 0
                assert builder.values[remainder[0]]==builder.values[remainder[1]]==expected,('known low pair',j,inverse)
                specialized(builder,remainder,older,sign,initial=initial,inverse=inverse)
            else:ORIGINAL(builder,remainder,older,sign,initial=initial,inverse=inverse)
        root._root_step=intercept
        result=root.forward(b,norm)
        Q=np.sqrt(values<<4).astype(np.int64)
        assert np.all(Q*Q<=values<<4)and np.all((Q+1)*(Q+1)>values<<4)
        expected_v=Q-4096;expected_h=((values<<6)-(2*Q+1)**2)//64
        for i,q in enumerate(result['root']):assert b.values[q]==pack((expected_v>>i)&1),('root',first,i)
        for i,q in enumerate(result['residual']):assert b.values[q]==pack((expected_h>>i)&1),('residual',first,i)
        assert [b.values[q]for q in flags]==flag_values
        assert b.num_allocated_qubits==26 and b.Toffolis==99
        indices=iter(reversed(range(1,13)))
        root.inverse(b,norm);root._root_step=ORIGINAL
        assert [b.values[q]for q in norm]==original and [b.values[q]for q in flags]==flag_values
        assert b.num_allocated_qubits==26 and b.Toffolis==198 and b.peak==41
        checked+=len(values);sign_checks+=len(values)*b.HMR
        rows.append(dict(first=first,stop=int(values[-1])+1,inputs=len(values),HMR_symbols=b.HMR,Toffolis=b.Toffolis,peak=b.peak))
        if len(rows)%12==0:print(json.dumps(dict(progress='source_boolean_root',inputs=checked,seconds=time.monotonic()-began)),flush=True)
    assert checked==3145728
    result=dict(status='PASS_ALL_NORMALIZED_SOURCE_VALUES_AND_ALL_HMR_SIGNS_NOT_NATIVE',
                normalized_inputs=checked,input_interval=[1<<20,1<<22],end_exclusive=True,
                root_formula='v=isqrt(16*n)-4096',residual_formula='h=(64*n-(8193+2*v)^2)//64',
                Toffolis_roundtrip=198,peak_including_exponent_flags4=41,
                all_known_pair_conditions_checked=True,all_original_data_restored=True,all_scratch_released_zero=True,
                all_HMR_sign_functions_checked=sign_checks,
                measurement_outcomes='Every individual HMR coefficient vanishes on every normalized input; linearity proves all joint outcomes.',
                chunks=rows,seconds=time.monotonic()-began,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                native_builder_or_simulator=False)
    path=HERE/'full_boolean.json';path.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items()if k!='chunks'},indent=2))


if __name__=='__main__':main()
