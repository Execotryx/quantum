# Copyright2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
# Credits: Opus and Astra.
"""Exact emitted-text proof on a finite care set, arbitrary spectators and HMRs.

This uses the same explicit GF(2) semantics as the frozen whole/native-table
checkers, with a supplied finite mathematical input chart. No checks are
disabled: every reset, restored input, scratch value and phase is checked.
"""
import hashlib,time
from common import ENGINE
assert hashlib.sha256((ENGINE/'branch_prover.py').read_bytes()).hexdigest()=='3d009334f8d4f37e10368ea5d46b21fa67eace7c3076f476a0b83f166cc769c2'
from branch_prover import Program


def prove_native_text(text,functions,count):
    began=time.monotonic();program=Program(text)
    original=list(program.registers['inputs']);spectators=list(program.registers.get('spectators',()))
    assert len(original)==len(functions) and 1<=count<=65536
    full=(1<<count)-1;one={0:full}
    assert all(isinstance(t,int)and 0<=t<=full for t in functions)
    def add(*values):
        result={}
        for value in values:
            for m,c in value.items():
                c^=result.get(m,0)
                if c:result[m]=c
                else:result.pop(m,None)
        return result
    def multiply(*values):
        result=one
        for value in values:
            new={}
            for a,ca in result.items():
                for b,cb in value.items():
                    c=(ca&cb)^new.get(a|b,0)
                    if c:new[a|b]=c
                    else:new.pop(a|b,None)
            result=new
            assert len(result)<=20000,'Bounded exact-polynomial limit; split required'
            if not result:break
        return result
    state={wire:{}for wire in program.wires};state.update({'0':{},'1':one,'False':{},'True':one})
    expected={}
    for wire,truth in zip(original,functions):
        state[wire]={0:truth}if truth else{};expected[wire]=state[wire]
    for i,wire in enumerate(spectators):
        state[wire]={1<<i:full};expected[wire]=state[wire]
    phase={};stack=[one];maximum=0;resets=0
    for index,op in enumerate(program.operations):
        k,args=op.kind,op.arguments;cond=stack[-1]
        if op.condition is not None:cond=multiply(cond,state[op.condition])
        if k=='PUSH_CONDITION':stack.append(cond);continue
        if k=='POP_CONDITION':assert len(stack)>1;stack.pop();continue
        if not cond:continue
        if k in('X','BIT_INVERT'):state[args[0]]=add(state[args[0]],cond)
        elif k=='CX':state[args[1]]=add(state[args[1]],multiply(cond,state[args[0]]))
        elif k=='CCX':state[args[2]]=add(state[args[2]],multiply(cond,state[args[0]],state[args[1]]))
        elif k in('SWAP','CSWAP'):
            if k=='CSWAP':cond=multiply(cond,state[args[0]]);a,b=args[1:]
            else:a,b=args
            delta=multiply(cond,add(state[a],state[b]));state[a]=add(state[a],delta);state[b]=add(state[b],delta)
        elif k in('Z','CZ','CCZ','NEG','Z_POW'):
            if k=='Z_POW':
                assert op.half_turns.denominator==1,'Unexpected fractional component phase'
                if not op.half_turns.numerator&1:continue
            phase=add(phase,multiply(cond,*(state[q]for q in args)))
        elif k=='HMR':
            target,out=args;m={1<<(len(spectators)+op.event):full}
            phase=add(phase,multiply(cond,m,state[target]))
            state[target]=add(state[target],multiply(cond,state[target]))
            state[out]=add(state[out],multiply(cond,add(state[out],m)))
        elif k=='R':
            assert not multiply(cond,state[args[0]]),('Dirty reset',index,args[0]);resets+=1
        elif k in('BIT_STORE0','BIT_STORE1'):
            value=one if k=='BIT_STORE1'else{}
            state[args[0]]=add(state[args[0]],multiply(cond,add(state[args[0]],value)))
        else:raise AssertionError(('Unsupported operation',k))
        terms=len(phase)+sum(len(p)for p in state.values())+sum(len(p)for p in stack)
        maximum=max(maximum,terms);assert terms<=50000,'Bounded full-state limit; split required'
    assert len(stack)==1
    for wire in program.quantum_wires:
        assert state[wire]==expected.get(wire,{}),('Data/scratch mismatch',wire)
    assert not phase,('Unpaid exact HMR/integral phase',len(phase),[hex(m)for m in list(phase)[:6]])
    return dict(status='PROVED_EMITTED_NATIVE_TEXT_ALL_CARE_INPUTS_SPECTATORS_AND_HMR',
        native_text_sha256=hashlib.sha256(text.encode()).hexdigest(),care_inputs=count,input_functions=len(functions),
        spectator_variables=len(spectators),HMR_variables=program.measurements,native_operations=len(program.operations),
        all_original_inputs_restored=True,all_spectators_preserved=True,all_scratch_zero=True,all_resets_zero=True,
        resets_checked=resets,final_phase_terms=0,maximum_polynomial_terms=maximum,seconds=time.monotonic()-began,
        full_invsqrt_native_proof=False,official_verifier=False)
