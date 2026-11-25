# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0
# Credits: Opus and Astra.
"""Bounded AST-bound Boolean/owner/phase audit, without native imports.

Executes the actual adapter/decoder function ASTs with a 128-row bitset
builder and the pinned pure-Python codebook gate emitter. Every HMR phase
generator is symbolic; no kickmix, CircuitBuilder, simulator or KMB is used.
"""
from pathlib import Path
from dataclasses import dataclass
from types import SimpleNamespace,ModuleType
import ast
import hashlib
import importlib.util
import json
import resource
import signal
import sys
import time

HERE=Path(__file__).resolve().parent;NARROW=HERE.parents[1]
FULL=(1<<128)-1
PINS={}


def read(path,digest=None):
    raw=path.read_bytes();actual=hashlib.sha256(raw).hexdigest()
    if digest is not None:assert actual==digest,(str(path),actual,digest)
    PINS[str(path.relative_to(NARROW))]=actual
    return raw


def data(path,digest=None):return json.loads(read(path,digest))


def functions(path,names,environment,module_name):
    tree=ast.parse(read(path).decode());selected=[node for node in tree.body
        if isinstance(node,(ast.FunctionDef,ast.ClassDef))and node.name in names]
    assert {node.name for node in selected}==set(names)
    module=ModuleType(module_name);module.__dict__.update(environment);sys.modules[module_name]=module
    exec(compile(ast.Module(body=selected,type_ignores=[]),str(path),'exec'),module.__dict__)
    return module


@dataclass(frozen=True)
class Q:
    index:int


@dataclass(frozen=True)
class B:
    index:int


class Builder:
    def __init__(self,cap=48):
        self.cap=cap;self.values={};self.bits=set();self.nextq=0;self.nextb=0
        self.phase={};self.conditions=[];self.Toffolis=0;self.peak=0;self.HMR=0;self.touched=set()
    @property
    def num_allocated_qubits(self):return len(self.values)
    def alloc_qubits(self,n):
        out=[]
        for _ in range(n):
            q=Q(self.nextq);self.nextq+=1;self.values[q]=0;out.append(q)
        self.peak=max(self.peak,len(self.values));assert self.peak<=self.cap
        return out
    def alloc_bits(self,n):
        out=[]
        for _ in range(n):
            b=B(self.nextb);self.nextb+=1;self.bits.add(b);out.append(b)
        return out
    def free(self,value):
        if isinstance(value,(list,tuple)):
            for item in value:self.free(item)
        elif isinstance(value,Q):
            assert self.values[value]==0,('FREE_NONZERO',value);del self.values[value]
        else:
            assert isinstance(value,B)and value in self.bits
            assert not any(value in key for key in self.phase),('FREE_UNREPAID_PHASE',value)
            self.bits.remove(value)
    def _data(self,*wires):
        assert not self.conditions,'This component unexpectedly uses classical data control.'
        assert all(isinstance(q,Q)and q in self.values for q in wires)
        self.touched.update(wires)
    def x(self,q):self._data(q);self.values[q]^=FULL
    def cx(self,a,b):
        self._data(a,b);assert a!=b;self.values[b]^=self.values[a]
    def ccx(self,a,b,c):
        self._data(a,b,c);assert len({a,b,c})==3
        self.values[c]^=self.values[a]&self.values[b];self.Toffolis+=1
    def swap(self,a,b):
        self._data(a,b);assert a!=b;self.values[a],self.values[b]=self.values[b],self.values[a]
    def _phase(self,key,truth):
        key=frozenset(key);new=self.phase.get(key,0)^truth
        if new:self.phase[key]=new
        else:self.phase.pop(key,None)
    def hmr(self,q,b):
        self._data(q);assert b in self.bits
        self._phase([b],self.values[q]);self.values[q]=0;self.HMR+=1
    def push_condition(self,b):assert b in self.bits;self.conditions.append(b)
    def pop_condition(self):assert self.conditions;self.conditions.pop()
    def z(self,q):
        if isinstance(q,B):
            assert q in self.bits;self._phase(self.conditions+[q],FULL)
        else:
            assert q in self.values;self.touched.add(q);self._phase(self.conditions,self.values[q])
    def cz(self,a,b):
        assert a in self.values and b in self.values and a!=b
        self.touched.update((a,b));self._phase(self.conditions,self.values[a]&self.values[b])


def main():
    _,hard=resource.getrlimit(resource.RLIMIT_AS)
    cap=128*1024**2 if hard==resource.RLIM_INFINITY else min(hard,128*1024**2)
    resource.setrlimit(resource.RLIMIT_AS,(cap,cap));signal.alarm(12);started=time.monotonic()
    assert 'kickmix'not in sys.modules
    accepted=data(NARROW/'PAPER_GATE_RECEIPT_022_VARIANT.json',
        'f8cfe4331b37a5184a4aab17ee85b4ac892c08c2cfb863fc4b1c1b3c9978262e')
    code=NARROW/'checkpoint002/cleanroom/baseline_stage97/engine/codebook.py'
    read(code,'9c6073d78becea467d37805131fdcc572e530c72acef5664b08057ef883f17be')
    spec=importlib.util.spec_from_file_location('_candidate07_static_codebook',code)
    cb=importlib.util.module_from_spec(spec);sys.modules[spec.name]=cb;spec.loader.exec_module(cb)
    model=data(NARROW/'research/recompute_root/models/phasefit_z1_K7_G4_m37_virtual_quadS2_36_12c0.json',
        '24fff823faa911afe93d02afc3ded0bbd156a210a85f1265c989a087f8fd1219')
    raw=cb.word_functions(range(128),7);Atruth=cb.word_functions(model['A'],13)
    Htruth=cb.word_functions(model['stored_slope'],5)
    truth=dict(address=tuple(raw),A=tuple(Atruth),H=tuple(Htruth))
    frozen=NARROW/'research/joint_loader/frozen'
    first=data(frozen/'loader16_first61_Q48.json','4857688e595af50828d7bedf0bc745eaaed8d10767e2e6ca6f77802887e1ad48')
    second=data(frozen/'loader16_second79_delay_Q48.json','5276e10525e98c6dbf6dc215e2a525441ba36ce0342e3f2dd937a2720e085da1')
    cleanup=data(frozen/'retained_table_cleanup9.json','6a48b472433918d2c51f30e6eeb1d9933fdf1aa4ae9f83b93129fd8ac103b6b5')
    def plan(p):return cb.QuadraticCodePlan(p['width'],p['constant'],p['linear'],tuple(map(tuple,p['edges'])),tuple(map(tuple,p['products'])),p['product_linear'])
    fakekm=SimpleNamespace(q=Q,b=B,array=list)
    env=dict(dataclass=dataclass,Any=object,FULL=FULL,km=fakekm,cb=cb,array=list,
             plan_from_json=plan,model_truths=lambda:truth,certificate=lambda key:cleanup)
    basepath=NARROW/'native/candidate01/tables.py'
    read(basepath,'cf2c83b6db5d1b1e2a63f4fe6e84976192a49eabb74e370ee2376fc4300659d3')
    base=functions(basepath,['TableDebt','TableDebts','_row_matrix_inverse_operations','_swap',
        '_affine_xor','emit_affine_frame','cleanup_joint16'],env,'_candidate07_static_base')
    resources={'first':dict(Toffolis=61,new_zero_owners=22,HMR_debts=45),
               'second':dict(Toffolis=79,new_zero_owners=17,HMR_debts=65)}
    inherited_frame=functions(HERE.parent/'candidate06/tables06.py',['emit_affine_frame'],dict(_BASE=base),'_candidate07_static_inherited_frame')
    adapter=functions(HERE/'tables07.py',['load_joint16'],
        dict(km=fakekm,cb=cb,_BASE=base,TableDebts=base.TableDebts,plan_from_json=plan,array=list,emit_affine_frame=inherited_frame.emit_affine_frame,
             certificate=lambda name:{'first':first,'second':second}[name],RESOURCES=resources,
             SECOND_RETIRED_ADDRESS_SLOTS=(0,1,2,4)), '_candidate07_static_adapter')
    decoder_cert=data(NARROW/'research/quantized_producer/framed_retained5_best21_snapshot.json',
        '3b6fa7059bee77bb9abe6c7395cd8ff2f2899843523188c60d513e6c5d381def')
    decoder=functions(HERE.parent/'candidate06/decoder06.py',['decode_root'],dict(km=fakekm,cb=cb,_BASE=base,
        plan_from_json=plan,CERT=decoder_cert,MISSING=(0,1,2,4,6),EARLY_TABLE_DEBT=(0,1,2,4)),
        '_candidate07_static_decoder')
    metadata=data(NARROW/'research/lifecycle_schedule/slope_h3_h4_retirement_v3.json',
        '1e5afe12bc0a9005bb3705afdc564f30c0861d99970d31f71d9b7c2556e17721')['certificate']
    h3plan=plan(metadata['H3_initial']['plan']);h4plan=plan(metadata['H4']['plan'])
    records=[]
    # First complete table load/cleanup with19 untouched spectator owners.
    b=Builder();address=b.alloc_qubits(7);spectators=b.alloc_qubits(19)
    for q,t in zip(address,raw):b.values[q]=t
    for i,q in enumerate(spectators):b.values[q]=raw[i%7]^(FULL if i%2 else 0)
    initial=dict(b.values);debts=base.TableDebts()
    A,H=adapter.load_joint16(b,address,variant='first',debts=debts)
    assert b.Toffolis==61 and b.num_allocated_qubits==42 and debts.total_recorded==45
    assert [b.values[q]for q in A+H]==Atruth+Htruth[:3]
    assert not set(spectators)&b.touched
    base.cleanup_joint16(b,address,A,H,debts)
    assert b.values==initial and not b.phase and not b.bits and not debts.pending
    assert b.Toffolis==70 and b.peak==48
    records.append(dict(name='first61_then_cleanup9',Toffolis=b.Toffolis,loader_Toffolis=61,
        peak=b.peak,final_owners=len(b.values),HMR_generators=b.HMR,all_symbolic_HMR_phases_zero=True))
    # Second chart:5 unused zero spectators model the P15->residual10 owner
    # reduction. Removing these spectators is a fixture boundary, not a free
    # arithmetic operation or a complete lifecycle proof.
    b=Builder();v=b.alloc_qubits(12);spectators=b.alloc_qubits(19);padding=spectators[-5:]
    for i,q in enumerate(v[:5]):b.values[q]=raw[(i+2)%7]^FULL
    for q,t in zip(v[5:],raw):b.values[q]=t
    for i,q in enumerate(spectators[:-5]):b.values[q]=raw[(i+4)%7]
    wanted_v=[b.values[q]for q in v];wanted_spectators={q:b.values[q]for q in spectators[:-5]}
    def Rframe(inverse=False):
        operations=[('cx',v[7],v[8]),('cx',v[7],v[10]),('ccx',v[6],v[10],v[8]),('cx',v[7],v[10])]
        if inverse:operations.reverse()
        for name,*wires in operations:getattr(b,name)(*wires)
    Rframe();assert b.Toffolis==1
    debts=base.TableDebts();A,H=adapter.load_joint16(b,v[5:],variant='second',debts=debts)
    assert b.Toffolis==80 and b.num_allocated_qubits==43 and debts.total_recorded==65
    assert [b.values[q]for q in A+H]==Atruth+Htruth[:3]
    for a in(0,1,2,4):v[5+a]=None
    h3=b.alloc_qubits(1)[0];cb.emit_xor(b,[A[i]for i in(10,11,12)]+[H[2],v[10],v[11]],h3,h3plan);H.append(h3)
    assert b.num_allocated_qubits==44 and b.values[h3]==Htruth[3]
    m=b.alloc_bits(1)[0];b.hmr(v[11],m);b.free(v[11]);v[11]=None
    retired={0:None,1:None,2:None,4:None,6:m}
    h4=b.alloc_qubits(1)[0];cb.emit_xor(b,[A[11],A[12],H[3]],h4,h4plan);H.append(h4)
    assert b.num_allocated_qubits==44 and b.values[h4]==Htruth[4]
    assert not set(spectators)&b.touched
    b.free(padding);assert b.num_allocated_qubits==39
    # Negative API check: do not accept a fabricated direct early-input sign.
    invalid=dict(retired);invalid[0]=m
    try:decoder.decode_root(b,v,A,H,invalid)
    except AssertionError:pass
    else:raise AssertionError('Decoder accepted a duplicate early-input phase outcome.')
    before=b.Toffolis;v=decoder.decode_root(b,v,A,H,retired)
    assert b.Toffolis-before==21 and b.num_allocated_qubits==44 and m not in b.bits
    Rframe(inverse=True);assert [b.values[q]for q in v]==wanted_v
    for q,variables,polynomial in[(H[4],[A[11],A[12],H[3]],h4plan),
        (H[3],[A[i]for i in(10,11,12)]+[H[2],v[10],v[11]],h3plan)]:
        outcome=b.alloc_bits(1)[0];b.hmr(q,outcome);cb.emit_phase(b,variables,outcome,polynomial)
        b.free(outcome);b.free(q)
    base.cleanup_joint16(b,v[5:],A,H[:3],debts)
    assert b.Toffolis==113 and b.peak==48 and b.num_allocated_qubits==26
    assert not b.phase and not b.bits and not debts.pending
    assert [b.values[q]for q in v]==wanted_v
    assert {q:b.values[q]for q in spectators[:-5]}==wanted_spectators
    assert not set(spectators)&b.touched
    records.append(dict(name='second79_H3H4_decoder21_Rframes_cleanup9',Toffolis=b.Toffolis,
        loader_Toffolis=79,decoder_Toffolis=21,peak=b.peak,final_owners=len(b.values),
        HMR_generators=b.HMR,all_symbolic_HMR_phases_zero=True,
        zero_spectator_fixture_boundary=5,early_four_direct_phase_rejected=True))
    source_ast=ast.parse(read(HERE/'tables07.py').decode())
    aliases={node.targets[0].id:ast.unparse(node.value) for node in source_ast.body
        if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name)}
    for name in('TableDebt','TableDebts','model_values','model_truths','cleanup_joint16','emit_affine_frame'):
        assert aliases[name]=='_OLD.'+name,(name,aliases[name])
    assert aliases['_OLD']=="inherited_module('tables06')"
    assert 'kickmix'not in sys.modules
    for path in(HERE/'tables07.py',HERE.parent/'candidate06/tables06.py',HERE.parent/'candidate06/decoder06.py',Path(__file__).resolve()):ast.parse(read(path).decode())
    result=dict(status='PASS_STATIC_AST_BOUND_128_ROW_COMPONENT_OWNER_AND_SYMBOLIC_PHASE_AUDIT_NO_NATIVE',
        source_pins=PINS,rows_per_case=128,records=records,
        exact_physical_gates_from_pinned_codebook=True,shared_class_and_cleanup_aliases_structurally_verified=True,native_module_imported=False,
        native_builder_or_simulator_used=False,native_circuit_emitted=False,
        interpretation='Static component gate-emitter mock, not a native or whole-arithmetic proof. Every HMR phase generator is symbolic over all128 raw addresses; spectator IDs are never touched.',
        memory_guard_MiB=cap//1024**2,hard_alarm_seconds=12,seconds=time.monotonic()-started,
        official_verifier=False,no_submission=True)
    path=HERE/'tables07_static_audit.json';tmp=path.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(result,indent=2)+'\n');tmp.replace(path)
    print(json.dumps({k:v for k,v in result.items()if k!='source_pins'},indent=2))


if __name__=='__main__':main()
