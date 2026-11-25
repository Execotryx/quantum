# SPDX-License-Identifier: Apache-2.0
"""Exact-domain HMR+conditioned-CZ: phucthaiv02 description, own implementation.

If target == control1 & control2 on every legal input, CCX erases it.
HMR followed by CZ conditioned on that result does the same on BOTH outcomes.
The underlying bitset/affine compiler is credited to Kozykorpesh/anazemcev.
"""
from pathlib import Path
import re,inspect
ROOT=Path(__file__).resolve().parent
def compile(source,destination):
 import port_pipeline as P
 D=P.module('ports6_hmr_domain',ROOT/'domain_compile.py')
 code=inspect.getsource(D.compile)
 code=code.replace('    full=(1<<max_x)-1',"    next_bit=1+max([-1]+[int(v) for v in re.findall(r'\\bb(\\d+)\\b',open(source).read())])\n    full=(1<<max_x)-1")
 before='                values[t]=vs[2]^prod'
 after=before+'''
                if not stack and t not in protected and vs[2]==prod and prod not in (0,full):
                    for q in (a,b,t):materialize(q)
                    out.write(f'HMR q{mapping[t]} b{next_bit}\\nCZ q{mapping[a]} q{mapping[b]} if b{next_bit}\\n')
                    next_bit+=1;changes['CCX->HMR_CZ_BOTH_OUTCOMES']+=1
                    ops['HMR']+=1;ops['CZ']+=1;release();continue
'''
 assert code.count(before)==1
 code=code.replace(before,after)
 anchor="            if new!=op:changes[op+'->'+str(new)]+=1"
 affine='''            if op=='CCX' and new==op and not stack and qs[-1] not in protected:
                a,b,t=qs
                sol=solve(values[t],{t})
                if sol is not None:
                    constant,sources=sol
                    for q in [a,b,t]+sources:materialize(q)
                    prepare=[]
                    if constant:prepare.append(f'X q{mapping[t]}\\n')
                    prepare.extend(f'CX q{mapping[q]} q{mapping[t]}\\n' for q in sources)
                    out.writelines(prepare)
                    out.write(f'HMR q{mapping[t]} b{next_bit}\\nCZ q{mapping[a]} q{mapping[b]} if b{next_bit}\\n')
                    out.writelines(prepare)
                    next_bit+=1;changes['CCX->AFFINE_HMR_CZ_BOTH_OUTCOMES']+=1
                    ops['HMR']+=1;ops['CZ']+=1;release();continue
'''
 assert code.count(anchor)==1
 code=code.replace(anchor,affine+anchor)
 exec(__import__('builtins').compile(code,'<round6-exact-hmr>','exec'),D.__dict__)
 return D.compile(source,destination,max_x=3133452,linear=True)
