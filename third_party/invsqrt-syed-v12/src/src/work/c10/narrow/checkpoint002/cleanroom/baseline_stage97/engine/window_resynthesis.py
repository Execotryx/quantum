# Copyright 2026 Syed Asad Ali (team syed3000)
# SPDX-License-Identifier: Apache-2.0
"""Exact small-window product reuse on a freshly generated in-memory circuit.

No file reader is provided. The compiler accepts the Circuit just emitted by
our from-math generator. Every accepted rewrite agrees on all input bitstrings
and on its exact sign; measurement and fractional-phase gates are barriers.
The search minimizes over a specified family of quadratic product bases, not
all reversible circuits. Every window is at most twelve wires.
"""
from __future__ import annotations
from dataclasses import dataclass
from functools import lru_cache
from itertools import combinations,permutations
import hashlib
import kickmix as km

ARITY={'X':1,'CX':2,'CCX':3,'SWAP':2,'CSWAP':3,'Z':1,'CZ':2,'CCZ':3,'NEG':0}
NONLINEAR={'CCX','CSWAP','CCZ'}

@dataclass(frozen=True)
class Gate:
    name:str
    wires:tuple[int,...]
    def text(self):return self.name+(' '+' '.join(f'q{x}' for x in self.wires) if self.wires else '')

def parse(line):
    parts=line.strip().split()
    if not parts or parts[0] not in ARITY or len(parts)!=ARITY[parts[0]]+1:return None
    if any(not x.startswith('q') or not x[1:].isdigit() for x in parts[1:]):return None
    return Gate(parts[0],tuple(int(x[1:]) for x in parts[1:]))

@lru_cache(maxsize=12)
def inputs(n):
    full=(1 << (1 << n))-1
    return full,tuple((full//((1 << (1 << bit))+1)) << (1 << bit) for bit in range(n))

def simulate(gates,wires):
    full,initial=inputs(len(wires));values=dict(zip(wires,initial));phase=0
    for gate in gates:
        name=gate.name;q=gate.wires
        if name=='X':values[q[0]]^=full
        elif name=='CX':values[q[1]]^=values[q[0]]
        elif name=='CCX':values[q[2]]^=values[q[0]]&values[q[1]]
        elif name=='SWAP':values[q[0]],values[q[1]]=values[q[1]],values[q[0]]
        elif name=='CSWAP':
            change=values[q[0]]&(values[q[1]]^values[q[2]])
            values[q[1]]^=change;values[q[2]]^=change
        elif name=='Z':phase^=values[q[0]]
        elif name=='CZ':phase^=values[q[0]]&values[q[1]]
        elif name=='CCZ':phase^=values[q[0]]&values[q[1]]&values[q[2]]
        elif name=='NEG':phase^=full
        else:raise ValueError(name)
    return tuple(values[x] for x in wires),phase

def quadratic(truth,n):
    full,variables=inputs(n);constant=truth&1;linear=0;quad=0
    recovered=full if constant else 0
    singles=[(truth >> (1 << i))&1 for i in range(n)]
    for i in range(n):
        if singles[i]^constant:
            linear|=1 << i;recovered^=variables[i]
    for k,(i,j) in enumerate(combinations(range(n),2)):
        if ((truth >> ((1 << i)|(1 << j)))&1)^singles[i]^singles[j]^constant:
            quad|=1 << k;recovered^=variables[i]&variables[j]
    return (constant,linear,quad) if recovered==truth else None

def cubic(truth,n):
    full,variables=inputs(n);values={0:truth&1};terms=[];recovered=0
    for degree in range(4):
        for indices in combinations(range(n),degree):
            mask=sum(1 << i for i in indices)
            coefficient=(truth >> mask)&1
            sub=(mask-1)&mask if mask else 0
            if mask:
                while True:
                    coefficient^=values[sub]
                    if sub==0:break
                    sub=(sub-1)&mask
            values[mask]=coefficient
            if coefficient:
                terms.append(mask);column=full
                for i in indices:column&=variables[i]
                recovered^=column
    return tuple(terms) if recovered==truth else None

def span_basis(rows):
    pivots={};basis=[]
    for original in rows:
        row=original
        while row:
            bit=row.bit_length()-1
            if bit not in pivots:
                pivots[bit]=row;basis.append(original);break
            row^=pivots[bit]
    return basis

def coefficients(basis,target):
    pivots={}
    for i,row in enumerate(basis):
        expr=1 << i
        while row:
            bit=row.bit_length()-1
            if bit not in pivots:pivots[bit]=(row,expr);break
            old,mask=pivots[bit];row^=old;expr^=mask
    expr=0
    while target:
        bit=target.bit_length()-1
        if bit not in pivots:return None
        old,mask=pivots[bit];target^=old;expr^=mask
    return expr

def invert(rows):
    n=len(rows);a=list(rows);inv=[1 << i for i in range(n)]
    for col in range(n):
        pivot=next((j for j in range(col,n) if a[j] >> col&1),None)
        if pivot is None:return None
        a[col],a[pivot]=a[pivot],a[col];inv[col],inv[pivot]=inv[pivot],inv[col]
        for j in range(n):
            if j!=col and a[j] >> col&1:a[j]^=a[col];inv[j]^=inv[col]
    return inv

def image(rows,vector):return sum(((row&vector).bit_count()&1) << i for i,row in enumerate(rows))

def linear_gates(rows,wires):
    """Emit the invertible row map by reversing its Gaussian elimination."""
    n=len(rows);a=list(rows);ops=[]
    for col in range(n):
        pivot=next((j for j in range(col,n) if a[j] >> col&1),None)
        if pivot is None:raise ValueError('Singular affine frame')
        if pivot!=col:
            a[col],a[pivot]=a[pivot],a[col];ops.append(Gate('SWAP',(wires[col],wires[pivot])))
        for j in range(n):
            if j!=col and a[j] >> col&1:
                a[j]^=a[col];ops.append(Gate('CX',(wires[col],wires[j])))
    return list(reversed(ops))

@lru_cache(maxsize=8192)
def factor(n,quad):
    edges={edge for k,edge in enumerate(combinations(range(n),2)) if quad >> k&1}
    products=[];linear=0
    while edges:
        i,j=min(edges);left=1 << i;right=1 << j
        for k in range(n):
            if k in (i,j):continue
            if tuple(sorted((j,k))) in edges:left|=1 << k
            if tuple(sorted((i,k))) in edges:right|=1 << k
        for a in range(n):
            if not (left >> a&1):continue
            for b in range(n):
                if not (right >> b&1):continue
                if a==b:linear^=1 << a
                else:edges.symmetric_difference_update((tuple(sorted((a,b))),))
        products.append((left,right))
    return tuple(products),linear

def product_gates(n,left,right,direction,wires):
    if (left&direction).bit_count()%2 or (right&direction).bit_count()%2:return None
    # Two control rows, one target row, then an annihilator basis.
    pivot=(direction&-direction).bit_length()-1
    rows=[left,right,1 << pivot]
    if len(span_basis(rows))!=3:return None
    for j in range(n):
        candidate=(1 << j)^(((direction >> j)&1) << pivot)
        if len(span_basis(rows+[candidate]))>len(rows):rows.append(candidate)
    if len(rows)!=n:return None
    before=linear_gates(rows,wires)
    return before+[Gate('CCX',(wires[0],wires[1],wires[2]))]+list(reversed(before))

def phase_gates(phase,n,wires):
    """Factor a cubic sign through masked minimum-rank quadratic forms."""
    terms=cubic(phase,n)
    if terms is None:return None
    full,variables=inputs(n)
    triples={t for t in terms if t.bit_count()==3};body=[];remaining=phase;count=0
    while triples:
        choices=[]
        for pivot in range(n):
            selected=[t for t in triples if t >> pivot&1]
            if not selected:continue
            quad=0
            for k,(i,j) in enumerate(combinations(range(n),2)):
                if ((1 << i)|(1 << j)|(1 << pivot)) in selected and pivot not in (i,j):quad|=1 << k
            products,_=factor(n,quad)
            choices.append((len(products)/len(selected),len(products),-len(selected),pivot,products,selected))
        _,_,_,pivot,products,selected=min(choices)
        for left,right in products:
            rows=[1 << pivot,left,right]
            if len(span_basis(rows))!=3:raise AssertionError('Cubic factors must be independent')
            for j in range(n):
                if len(span_basis(rows+[1 << j]))>len(rows):rows.append(1 << j)
            before=linear_gates(rows,wires)
            body+=before+[Gate('CCZ',tuple(wires[:3]))]+list(reversed(before));count+=1
            a=0;b=0
            for j in range(n):
                if left >> j&1:a^=variables[j]
                if right >> j&1:b^=variables[j]
            remaining^=variables[pivot]&a&b
        triples.difference_update(selected)
    affine=quadratic(remaining,n)
    if affine is None:raise AssertionError('Cubic cancellation left a nonquadratic phase')
    constant,linear,quad=affine
    if constant:body.append(Gate('NEG',()))
    body += [Gate('Z',(wires[i],)) for i in range(n) if linear >> i&1]
    body += [Gate('CZ',(wires[i],wires[j])) for k,(i,j) in enumerate(combinations(range(n),2)) if quad >> k&1]
    if simulate(body,wires)!=(inputs(n)[1],phase):raise AssertionError('Cubic sign certificate failed')
    return body,count

def synthesize(gates,wires,max_products=3):
    n=len(wires);old_count=sum(g.name in NONLINEAR for g in gates)
    original,phase=simulate(gates,wires)
    polys=[quadratic(t,n) for t in original];phase_plan=phase_gates(phase,n,wires)
    if any(p is None for p in polys) or phase_plan is None:return None
    phase_body,phase_cost=phase_plan
    if phase_cost>=old_count:return None
    basis=span_basis([p[2] for p in polys]);d=len(basis)
    if d>max_products or d>=old_count:return None
    variants=[]
    if not d:variants=[()]
    else:
        space=[]
        for mask in range(1,1 << d):
            value=0
            for i,b in enumerate(basis):
                if mask >> i&1:value^=b
            if len(factor(n,value)[0])<=min(max_products,old_count-1):space.append(value)
        variants=[b for b in combinations(space,d) if len(span_basis(b))==d]
    best=None
    for chosen in variants:
        combos=[coefficients(chosen,p[2]) for p in polys]
        products=[];rows=[p[1] for p in polys]
        for j,q in enumerate(chosen):
            factors,lin=factor(n,q)
            direction=sum(((mask >> j)&1) << i for i,mask in enumerate(combos))
            for i in range(n):
                if direction >> i&1:rows[i]^=lin
            products.extend((a,b,direction) for a,b in factors)
        if len(products)+phase_cost>=old_count or len(products)>max_products:continue
        inverse=invert(rows)
        if inverse is None:continue
        transformed=[(a,b,image(inverse,v)) for a,b,v in products]
        for order in permutations(transformed):
            previous=[];valid=True;body=[]
            for left,right,direction in order:
                if any((left&w).bit_count()%2 or (right&w).bit_count()%2 for w in previous):valid=False;break
                ops=product_gates(n,left,right,direction,wires)
                if ops is None:valid=False;break
                body+=ops;previous.append(direction)
            if not valid:continue
            emitted=list(phase_body)
            emitted+=body+linear_gates(rows,wires)
            emitted += [Gate('X',(wires[i],)) for i,p in enumerate(polys) if p[0]]
            if simulate(emitted,wires)!=(original,phase):raise AssertionError('All-input/sign window certificate failed')
            key=(len(products)+phase_cost,len(emitted),tuple(g.text() for g in emitted))
            if best is None or key<best[0]:best=(key,emitted)
    if best is None:return None
    packed=b''.join(t.to_bytes((1 << n)//8+1,'little') for t in (*original,phase))
    return best[1],dict(wires=wires,inputs=1 << n,phase_exact=True,
        old_toffolis=old_count,new_toffolis=best[0][0],old_operations=len(gates),
        new_operations=len(best[1]),truth_sha256=hashlib.sha256(packed).hexdigest())

def optimize(circuit,*,max_wires=12,max_gates=128,max_nonlinear=4,passes=2):
    """Optimize only coherent, sign-valued small windows; preserve all barriers."""
    if not 3<=max_wires<=12:raise ValueError('This compiler certifies at most12 wires')
    lines=str(circuit).splitlines();certificates=[];attempts=0
    for round_index in range(passes):
        parsed=[parse(line) for line in lines];i=0;changed=False;out=[]
        while i<len(lines):
            # Beginning at a nonlinear gate is enough: all preceding affine
            # transformations become the independently free window inputs.
            if parsed[i] is None or parsed[i].name not in NONLINEAR:
                out.append(lines[i]);i+=1;continue
            wires=set();nonlinear=0;ends=[]
            for j in range(i,min(len(lines),i+max_gates)):
                gate=parsed[j]
                if gate is None:break
                wires.update(gate.wires)
                if len(wires)>max_wires:break
                nonlinear+=gate.name in NONLINEAR
                if nonlinear>max_nonlinear:break
                if nonlinear>=2 and (j+1==len(lines) or parsed[j+1] is None or parsed[j+1].name in NONLINEAR):
                    ends.append((j+1,tuple(sorted(wires))))
            best=None
            for end,used in reversed(ends):
                attempts+=1;result=synthesize(parsed[i:end],used,max_products=max_nonlinear-1)
                if result is None:continue
                gates,proof=result;saving=proof['old_toffolis']-proof['new_toffolis']
                key=(-saving,proof['new_toffolis'],len(gates),end)
                if best is None or key<best[0]:best=(key,end,gates,proof)
            if best is None:out.append(lines[i]);i+=1;continue
            _,end,gates,proof=best
            proof.update(pass_index=round_index,start_operation=i,end_operation=end)
            certificates.append(proof);out.extend(g.text() for g in gates);i=end;changed=True
        lines=out
        if not changed:break
    optimized=km.Circuit('\n'.join(lines))
    before=int(circuit.operation_statistics().num_toffoli_like)
    after=int(optimized.operation_statistics().num_toffoli_like)
    if before-after!=sum(p['old_toffolis']-p['new_toffolis'] for p in certificates):
        raise AssertionError('Resource accounting differs from exact rewrites')
    if optimized.num_qubits>circuit.num_qubits:raise AssertionError('Window pass increased width')
    return optimized,dict(status='PROVED',family='quadratic_product_basis',max_wires=max_wires,
        attempted_windows=attempts,accepted_windows=len(certificates),
        before_static_toffolis=before,after_static_toffolis=after,certificates=certificates)
