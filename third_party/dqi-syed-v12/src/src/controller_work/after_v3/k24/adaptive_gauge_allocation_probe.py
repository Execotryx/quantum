#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Root-only tiny allocation diagnostic; no simulation or gauge construction.

The unchanged point cell is repeated at most64 times, with and without the
same selector allocation/free topology. This records native classical high
water separately from explicitly owned live workspace. It emits no decoder,
does not run the selector, and does not modify the failed component packet.
"""
from pathlib import Path
import argparse
import hashlib
import json
import sys

HERE = Path(__file__).resolve().parent
PROJECT,WORK,ROOT = HERE.parent,HERE.parents[1],HERE.parents[2]
for path in (ROOT/'pro1_controller_bundle/1_task/official',
             WORK/'work/round2/milestone152/source',WORK/'night_schedule',
             WORK/'night_root',WORK/'night_converter',WORK/'night_c27/arithmetic',
             WORK/'night_c27/synthesis',WORK/'after_c5/arithmetic_t',PROJECT/'scan'):
    sys.path.insert(0,str(path))

import kickmix as km
import zero_mask_scan as Cell

PINS = {
 'controller_work/after_v3/scan/zero_mask_scan.py':'cacf6f97a639ff6b89d500e9cb9e2d427819ba461635cd6407a573d1668b53f1',
 'controller_work/night_schedule/scan10.py':'14a4e8e90dcc3b5f4b0dc3cc4ad5e306ebe55c87ca4185bc583f1ed9311f8b21',
 'controller_work/work/round2/milestone152/source/narrow_field130.py':'f021152bc598f334d854bfba13b9f228cd6a0b751010dde10c9341203bd49bf6',
}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Trace:
    def __init__(self,builder):
        self.builder=builder
        self.live=0
        self.peak=0
        self.allocations=[]
        self.del_and_rows=[]
        self.cell=-1

    def __getattr__(self,name):
        return getattr(self.builder,name)

    def alloc_bits(self,count):
        value=self.builder.alloc_bits(count)
        self.live+=count
        self.peak=max(self.peak,self.live)
        if self.cell < 2:
            self.allocations.append(dict(cell=self.cell,action='alloc_bits',count=count,live=self.live))
        return value

    def free(self,wires):
        if all(isinstance(wire,km.b) for wire in wires):
            self.live-=len(wires)
            assert self.live>=0
            if self.cell < 2:
                self.allocations.append(dict(cell=self.cell,action='free_bits',count=len(wires),live=self.live))
        return self.builder.free(wires)

    def del_and(self,*args,**kwargs):
        result=self.builder.del_and(*args,**kwargs)
        if self.cell < 2:
            self.del_and_rows.append(dict(cell=self.cell,
                                         explicit_live_bits=self.live,return_type=type(result).__name__))
        return result


def build(mode):
    b=km.CircuitBuilder()
    D=b.create_quantum_register(12,'D')
    K=b.create_quantum_register(12,'K')
    masks=b.create_classical_register(49140,'masks')
    t=Trace(b)
    stages=[]
    def mark(label):
        c=b.finish_circuit()
        stages.append(dict(stage=label,num_bits=c.num_bits,instructions=len(c),
                           explicit_live_workspace=t.live,explicit_workspace_peak=t.peak))
    mark('declared_inputs')
    label=None
    if mode.startswith('pool_'):
        dirty=t.alloc_bits(322);t.bit_store(dirty,True);t.free(dirty)
        counters=t.alloc_bits(192);decoder=t.alloc_bits(127);work=t.alloc_bits(3)
        t.bit_store(counters,False);t.bit_store(decoder,False);t.bit_store(work,False)
        t.free(decoder)
        label=t.alloc_bits(12);comparison=t.alloc_bits(3)
        t.bit_store(label,False);t.bit_store(comparison,False)
        t.free(comparison);t.free(counters);t.free(work)
        assert t.live==12 and t.peak==322
        mark('selector_topology_only_label_live')
    ladder=t.alloc_qubits(10)
    point=Cell.point_cell if mode.endswith('conditional') else Cell.Base.point_cell
    for i in range(64):
        t.cell=i
        point(t,D,K,masks[12*i:12*(i+1)],ladder)
        if i+1 in (1,2,4,8,16,32,64):
            mark('point_'+str(i+1))
    t.free(ladder)
    if label is not None:
        t.bit_store(label,False);t.free(label)
    mark('all_explicit_workspace_retired')
    assert t.live==0 and b.num_allocated_qubits==24
    c=b.finish_circuit()
    assert c.operation_statistics().num_toffoli_like==64*11
    allocated_bits=getattr(b,'num_allocated_bits',None)
    return dict(mode=mode,point_cells=64,stages=stages,
                explicit_allocation_trace_first_two=t.allocations,
                native_del_and_trace_first_two=t.del_and_rows,
                Q=c.num_qubits,static_T=c.operation_statistics().num_toffoli_like,
                num_bits=c.num_bits,instructions=len(c),
                num_allocated_bits_attribute=allocated_bits if type(allocated_bits) is int else None,
                num_allocated_bits_attribute_type=type(allocated_bits).__name__)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    assert __debug__ and sys.version_info[:2]==(3,13)
    target=a.output.resolve()
    assert target.is_relative_to(HERE/'runs') and not target.exists()
    for name,wanted in PINS.items():
        assert digest(ROOT/name)==wanted,name
    rows=[build(mode) for mode in ('plain_baseline','plain_conditional','pool_baseline','pool_conditional')]
    result=dict(status='OBSERVED_TINY_NATIVE_POINT_ALLOCATION_ONLY',rows=rows,
                source_sha256=digest(__file__),input_sources=PINS,
                native_simulations=0,selector_executed=False,decoder_builds=0,
                component_correctness_claim=False,changed_existing_files=False)
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps(result,sort_keys=True),flush=True)


if __name__=='__main__':
    main()
