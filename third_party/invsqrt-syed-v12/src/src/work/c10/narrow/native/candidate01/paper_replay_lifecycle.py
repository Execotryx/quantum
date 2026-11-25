#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0
# Credits: Opus and Astra.
"""Actual native-emitter API replay using only a small source counter.

No CircuitBuilder, simulator, native circuit, or native-lock bypass. This is
an ownership/count check of the new code before its serial native proof.
"""
import resource
resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,512*1024**2))
from common import *
sys.path.insert(0,str(NARROW/'research/stream_phase'))
from drive_paper_ledger import PaperCounter
import lifecycle,tables,root_decode


class Counter(PaperCounter):
    def swap(self,*args):pass


class NoDivider:
    @staticmethod
    def compute_phase_cleanup(builder,v,P,flags):return list(P)


def main():
    verify_gate_sources();b=Counter(49);v=list(b.alloc_qubits(12));h=list(b.alloc_qubits(10));flags=list(b.alloc_qubits(4));trace=[]
    counts={}
    def hook(label,builder,owners):counts[label]=float(builder.count)
    lifecycle.CUT_HOOK=hook
    try:vv,hh=lifecycle.emit_body(b,v,h,flags,tables,NoDivider,root_decode.decode_root,trace=trace)
    finally:lifecycle.CUT_HOOK=None
    assert float(b.count)==543.5,(float(b.count),counts)
    assert len(set(vv+hh+flags))==26 and b.num_allocated_qubits==26 and b.peak==49
    result=dict(status='PASS_ACTUAL_EMITTER_SOURCE_COUNTER_NOT_NATIVE',expected_E=float(b.count),peak=b.peak,
        final_live=26,cut_counts=counts,trace=trace,
        source_sha256=hashlib.sha256((HERE/'lifecycle.py').read_bytes()).hexdigest())
    (HERE/'lifecycle_paper_replay.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':main()
