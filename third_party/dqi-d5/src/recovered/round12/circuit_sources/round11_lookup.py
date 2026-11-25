# SPDX-License-Identifier: Apache-2.0
"""Exact multioutput decision/Davio lookup; source-only, measured erasure.

Optimizes AND count by shared cofactors/XOR cofactors and variable choice.
Davio identity f=f0 XOR x*(f0 XOR f1); source QROM lineage remains credited.
"""
from functools import lru_cache

def planner(table):
 @lru_cache(None)
 def plan(rows,bits,controlled):
  if len(set(rows))==1:return (0,('const',rows[0]))
  best=None
  for pos,bit in enumerate(bits):
   lo=tuple(v for i,v in enumerate(rows) if not(i>>pos&1));hi=tuple(v for i,v in enumerate(rows) if i>>pos&1);remain=bits[:pos]+bits[pos+1:]
   if lo==hi:
    cost,p=plan(lo,remain,controlled);candidate=(cost,('skip',p))
    if best is None or cost<best[0]:best=candidate
    continue
   if len(bits)==1:
    candidate=(int(controlled),('leaf',bit,lo[0],lo[0]^hi[0]))
    if best is None or candidate[0]<best[0]:best=candidate
    continue
   delta=tuple(a^b for a,b in zip(lo,hi))
   # XOR/Davio form keeps the base under the existing parent.
   for polarity,base in [(1,lo),(0,hi)]:
    cb,pb=plan(base,remain,controlled);cd,pd=plan(delta,remain,True)
    candidate=(cb+cd+int(controlled),('davio',bit,polarity,pb,pd))
    if best is None or candidate[0]<best[0]:best=candidate
   ca,pa=plan(lo,remain,True);cb,pb=plan(hi,remain,True)
   candidate=(ca+cb+int(controlled),('shannon',bit,pa,pb))
   if best is None or candidate[0]<best[0]:best=candidate
  return best
 cost,p=plan(tuple(map(int,table)),tuple(range((len(table)-1).bit_length())),False)
 return cost,p,plan.cache_info()._asdict()

def lookup(b,address,target,table,*,last=False):
 import kickmix as km
 expected,p,info=planner(table);stats=dict(ands=0,expected=expected,planner=info)
 address=list(address);target=list(target)
 def word(value,parent):
  selected=[q for i,q in enumerate(target) if value>>i&1]
  if not selected:return
  if parent is None:b.x(km.array(selected))
  else:
   for q in selected:b.cx(parent,q)
 def product(parent,bit,value):
  if not value:return
  if parent is None:word(value,bit);return
  selected=[q for i,q in enumerate(target) if value>>i&1];pivot=selected[-1] if last else selected[0]
  others=[q for q in selected if q!=pivot]
  for q in others:b.cx(pivot,q)
  b.ccx(parent,bit,pivot);stats['ands']+=1
  for q in reversed(others):b.cx(pivot,q)
 def walk(node,parent):
  kind=node[0]
  if kind=='const':word(node[1],parent);return
  if kind=='skip':walk(node[1],parent);return
  if kind=='leaf':word(node[2],parent);product(parent,address[node[1]],node[3]);return
  bit=address[node[1]]
  if kind=='davio':
   _,_,polarity,base,delta=node;walk(base,parent)
   if not polarity:b.x(bit)
   if parent is None:walk(delta,bit)
   else:
    t=b.alloc_qubits(1)[0];b.init_and(parent,bit,t);stats['ands']+=1
    walk(delta,t);b.del_and(parent,bit,t);b.free(km.array([t]))
   if not polarity:b.x(bit)
  else:
   _,_,lo,hi=node
   if parent is None:
    b.x(bit);walk(lo,bit);b.x(bit);walk(hi,bit)
   else:
    t=b.alloc_qubits(1)[0];b.x(bit);b.init_and(parent,bit,t);b.x(bit);stats['ands']+=1
    walk(lo,t);b.cx(parent,t);walk(hi,t);b.cx(parent,t)
    b.x(bit);b.del_and(parent,bit,t);b.x(bit);b.free(km.array([t]))
 walk(p,None);assert stats['ands']==expected,stats
 return stats
