# Copyright 2026 Syed Asad Ali (team syed3000)
# SPDX-License-Identifier: Apache-2.0
"""Deterministic exact finite synthesis from the six C5 rotation targets.

The circuit generator imports only this mathematical search; there is no
compiled-circuit, saved-plan, fixture-file or wall-clock input.
"""
import itertools
import json


def screen():
    permutations = tuple(itertools.permutations(range(5)))
    index = {p:i for i, p in enumerate(permutations)}
    pairs = tuple(itertools.combinations(range(5), 2))
    swaps = []
    for i,j in pairs:
        row=[]
        for p in permutations:
            q=list(p); q[i],q[j]=q[j],q[i]; row.append(index[tuple(q)])
        swaps.append(tuple(row))
    # r=0 is always identity because all linear controls vanish. The other
    # five permutations are packed in five seven-bit coordinates.
    actions = tuple((mask, pair, tuple(7*(r-1) for r in range(1,6)
                     if (mask&r).bit_count()&1))
                    for mask in range(1,8) for pair in range(10))
    goal = sum(index[tuple((i-r)%5 for i in range(5))] << (7*(r-1))
               for r in range(1,6))

    def step(state, action):
        _mask, pair, shifts=actions[action]; table=swaps[pair]
        new=state
        for shift in shifts:
            old=(state>>shift)&127
            new ^= (old^table[old])<<shift
        return new

    def expand(frontier, seen, depth):
        nxt=[]
        for state in frontier:
            _prior_depth, path=seen[state]
            for action in range(len(actions)):
                other=step(state,action)
                if other not in seen:
                    seen[other]=(depth,(path<<7)|(action+1)); nxt.append(other)
        return nxt

    left={0:(0,0)}; front=[0]; counts_left=[1]
    for depth in range(1,4):
        front=expand(front,left,depth); counts_left.append(len(front))
        print(json.dumps(dict(side='left',depth=depth,states=len(left))),flush=True)
    right={goal:(0,0)}; front=[goal]; counts_right=[1]
    best=None
    for depth in range(4):
        for state in front:
            if state in left:
                ld,lp=left[state]; rd,rp=right[state]
                candidate=(ld+rd,lp,rp,ld,rd)
                if best is None or candidate<best:best=candidate
        if depth<3:
            front=expand(front,right,depth+1);counts_right.append(len(front))
            print(json.dumps(dict(side='right',depth=depth+1,states=len(right))),flush=True)

    def decode(path,count):
        out=[]
        for _ in range(count):out.append((path&127)-1);path>>=7
        if path:raise AssertionError('Path encoding overflow.')
        return list(reversed(out))

    seventh_transitions=0
    if best is None:
        # Extend only one step beyond the already stored depth-three ball.
        # The fourth layer is streamed, so it cannot allocate millions of
        # expression/state objects. A first match is optimal because both
        # complete depth-three balls already excluded every length<=six.
        for state in front:
            _rd,rp=right[state]
            for action in range(len(actions)):
                other=step(state,action);seventh_transitions+=1
                if other in left:
                    ld,lp=left[other]
                    best=(ld+4,lp,(rp<<7)|(action+1),ld,4)
                    break
            if best is not None:break
    report=dict(status='EXACT_FINITE_ROUTING_SCREEN', action_count=len(actions),
        states_left=len(left), states_right=len(right), layer_sizes_left=counts_left,
        layer_sizes_right=counts_right, complete_length_bound=7,
        streamed_seventh_transitions=seventh_transitions,
        no_wall_clock_selection=True, source_input='r in0..5 and five-wire cyclic permutation',
        complete_circuit_built=False, official_verified=False)
    if best is None:
        report.update(outcome='NO_NETWORK_OF_LENGTH_AT_MOST_SEVEN_IN_THIS_FAMILY',
            scope='Linear controls on three bits; no claim about longer or nonlinear-control networks.')
        return report
    length,lp,rp,ld,rd=best
    path=decode(lp,ld)+list(reversed(decode(rp,rd)))
    state=0
    for a in path:state=step(state,a)
    if state!=goal:raise AssertionError('Meet-in-the-middle path is invalid.')
    checked=0
    for r in range(6):
        for value in range(32):
            word=[(value>>i)&1 for i in range(5)];old=word[:]
            for a in path:
                mask,pair,_=actions[a];i,j=pairs[pair]
                if (mask&r).bit_count()&1:word[i],word[j]=word[j],word[i]
            if word != [old[(i-r)%5] for i in range(5)]:
                raise AssertionError('Exact Boolean truth certificate failed.')
            checked+=1
    report.update(outcome='FOUND_EXACT_NETWORK', minimum_length=length,
        network=[dict(control_mask=actions[a][0],swap=list(pairs[actions[a][1]])) for a in path],
        exhaustive_boolean_rows=checked,
        permutation_only_C10_cost=5+2*length,
        previous_C10_cost=21,
        warning='Control generation/erasure and the57-qubit schedule are not yet accounted.')
    return report
