# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0
# Credits: Opus and Astra.
"""Exact native-text Boolean/phase proof over all addresses and transcripts.

Truth coefficients are128-bit vectors over the raw table address. Monomials
are square-free products of every spectator input and syntactic HMR outcome.
All arithmetic is exact GF(2); the table circuit uses only integral half-turn
phases. A zero polynomial proves every assignment simultaneously.
"""
import hashlib
from common import ENGINE
assert hashlib.sha256((ENGINE/'branch_prover.py').read_bytes()).hexdigest()=='3d009334f8d4f37e10368ea5d46b21fa67eace7c3076f476a0b83f166cc769c2'
from branch_prover import Program

FULL=(1<<128)-1
ONE={0:FULL}


def add(*values):
    result={}
    for value in values:
        for monomial,coefficient in value.items():
            coefficient^=result.get(monomial,0)
            if coefficient:result[monomial]=coefficient
            else:result.pop(monomial,None)
    return result


def multiply(*values):
    result=dict(ONE)
    for value in values:
        new={}
        for a,ca in result.items():
            for b,cb in value.items():
                coefficient=(ca&cb)^new.get(a|b,0)
                if coefficient:new[a|b]=coefficient
                else:new.pop(a|b,None)
        result=new
        if not result:break
    return result


def prove_native_text(text,*,address_name='address',spectator_name='spectators'):
    program=Program(text)
    address=program.registers[address_name];spectators=program.registers[spectator_name]
    assert len(address)==7
    state={wire:{} for wire in program.wires}
    state.update({'0':{},'1':dict(ONE),'False':{},'True':dict(ONE)})
    expected={}
    for bit,wire in enumerate(address):
        truth=sum(((row>>bit)&1)<<row for row in range(128))
        state[wire]={0:truth};expected[wire]={0:truth}
    for bit,wire in enumerate(spectators):
        state[wire]={1<<bit:FULL};expected[wire]={1<<bit:FULL}
    phase={};stack=[dict(ONE)];maximum_terms=0;phase_gate_count=0
    for index,operation in enumerate(program.operations):
        kind,args=operation.kind,operation.arguments
        condition=stack[-1]
        if operation.condition is not None:condition=multiply(condition,state[operation.condition])
        if kind=='PUSH_CONDITION':stack.append(condition);continue
        if kind=='POP_CONDITION':
            assert len(stack)>1
            stack.pop();continue
        if not condition:continue
        if kind=='X' or kind=='BIT_INVERT':
            state[args[0]]=add(state[args[0]],condition)
        elif kind=='CX':
            state[args[1]]=add(state[args[1]],multiply(condition,state[args[0]]))
        elif kind=='CCX':
            state[args[2]]=add(state[args[2]],multiply(condition,state[args[0]],state[args[1]]))
        elif kind in ('SWAP','CSWAP'):
            if kind=='CSWAP':condition=multiply(condition,state[args[0]]);a,b=args[1:]
            else:a,b=args
            delta=multiply(condition,add(state[a],state[b]));state[a]=add(state[a],delta);state[b]=add(state[b],delta)
        elif kind in ('Z','CZ','CCZ','NEG','Z_POW'):
            if kind=='Z_POW':
                assert operation.half_turns.denominator==1,'A fractional phase needs a different exact coefficient ring.'
                if not operation.half_turns.numerator&1:continue
            phase=add(phase,multiply(condition,*(state[wire] for wire in args)));phase_gate_count+=1
        elif kind=='HMR':
            target,outcome_wire=args
            outcome={1<<(len(spectators)+operation.event):FULL}
            phase=add(phase,multiply(condition,outcome,state[target]))
            state[target]=add(state[target],multiply(condition,state[target]))
            state[outcome_wire]=add(state[outcome_wire],multiply(condition,add(state[outcome_wire],outcome)))
        elif kind=='R':
            assert not multiply(condition,state[args[0]]),f'Dirty reset at native instruction{index}'
        elif kind in ('BIT_STORE0','BIT_STORE1'):
            desired=ONE if kind=='BIT_STORE1' else{}
            state[args[0]]=add(state[args[0]],multiply(condition,add(state[args[0]],desired)))
        else:raise AssertionError(f'Unsupported native instruction{kind}')
        maximum_terms=max(maximum_terms,len(phase)+sum(len(value) for value in state.values())+sum(len(value) for value in stack))
    assert len(stack)==1
    for wire in program.quantum_wires:
        assert state[wire]==expected.get(wire,{}),(wire,state[wire],expected.get(wire,{}))
    assert not phase,('Nonzero exact phase polynomial',[(hex(m),hex(c)) for m,c in list(phase.items())[:8]])
    return dict(status='PROVED_NATIVE_TEXT_ALL_ADDRESSES_SPECTATORS_AND_HMR_TRANSCRIPTS',
                native_text_sha256=hashlib.sha256(text.encode()).hexdigest(),native_operations=len(program.operations),
                addresses=128,spectator_variables=len(spectators),HMR_variables=program.measurements,
                assignments_per_address_power_of_two=len(spectators)+program.measurements,
                phase_gate_count=phase_gate_count,maximum_total_polynomial_terms=maximum_terms,
                final_quantum_outputs='Exact address/spectators; every other physical qubit zero.',
                final_phase_polynomial_terms=0,coefficient_ring='GF(2) with128-bit exact address truth coefficients',
                dirty_resets_rejected=True)


def selftest():
    # Use disjoint, ordinary q integer names; the parser never infers a wire
    # identity from the position in a register declaration.
    header='\n'.join([f'APPEND_TO_REGISTER q{i} 0' for i in range(7)]+[
        'REGISTER 0 address','APPEND_TO_REGISTER q7 1','APPEND_TO_REGISTER q8 1','REGISTER 1 spectators'])+'\n'
    positive=[header+'CX q0 q9\nHMR q9 b0\nZ q0 if b0\nR q9\n',
              header+'X q9\nHMR q9 b0\nZ b0\nR q9\n']
    for text in positive:prove_native_text(text)
    for text in [header+'X q9\nHMR q9 b0\n',header+'X q9\nR q9\n']:
        try:prove_native_text(text)
        except AssertionError:pass
        else:raise AssertionError('The exact text checker accepted a deliberately wrong circuit.')
    return dict(status='PASS',positive_cases=2,negative_cases=2)


if __name__=='__main__':
    print(selftest())
