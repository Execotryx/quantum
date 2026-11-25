# SPDX-License-Identifier: Apache-2.0
"""Ten-bit exact history for zero/one/two nonadjacent gaps among35 slots.

Gluzdov: exploit unused upper-triangle states of two5-bit fields; four late
columns and six escape diagonals. Extends our earlier11-bit late escape.
More than two gaps retains the decoder's inherited approximation policy.
"""
from contextlib import contextmanager

ESCAPES={1:(31,34),2:(32,34),3:(30,35),4:(31,35),5:(32,35),6:(33,35)}

def encode(events):
 if not events:return (0,0)
 new=events[-1];old=events[-2] if len(events)>1 else 0
 if new<=31:return new,old
 if new==32:return old,31
 if new==33:return old,30
 if new==34:return (old,29) if old<=30 else (old-30,old-30)
 return (old,28) if old<=29 else (old-27,old-27)

def membership(a,o,index):
 result=int(a==index) if index<=31 else int(o==63-index) if index in (32,33) else int(o==63-index) if index in (34,35) else 0
 if index<=27:result^=int(o==index)
 if index in (28,35):result^=int((a,o)==(30,28))^int((a,o)==(31,28))
 if index in (29,34):result^=int((a,o)==(31,29))
 for code,pair in ESCAPES.items():
  if index in pair:result^=int(a==o==code)
 return result

def classical_fixture():
 states=[()]+[(a,) for a in range(1,36)]+[(a,b) for b in range(1,36) for a in range(1,b-1)]
 codes=[encode(x) for x in states];assert len(set(codes))==len(states)
 for events,(a,o) in zip(states,codes):
  for i in range(1,36):assert membership(a,o,i)==int(i in events),(events,(a,o),i)
 return dict(status='PASS',histories=len(states),bits=10,distinct_codes=len(set(codes)),queries=35*len(states))

class Rank10Stack:
 def __init__(self,b):self.b=b;self.a=b.alloc_qubits(5);self.old=b.alloc_qubits(5)
 def code(self,a,o,target):
  from common import km
  self.b.flip_if_equal(km.array(list(self.a)+list(self.old)),a|(o<<5),target=target)
 def xor_read(self,index,target):
  k=index+1;b=self.b
  if k<=31:b.flip_if_equal(self.a,k,target=target)
  if k<=27:b.flip_if_equal(self.old,k,target=target)
  if k in (28,35):self.code(30,28,target);self.code(31,28,target)
  if k in (29,34):self.code(31,29,target)
  if k>=32:b.flip_if_equal(self.old,63-k,target=target)
  for code,pair in ESCAPES.items():
   if k in pair:self.code(code,code,target)
 def transposition(self,p,q,control):
  from common import km
  b=self.b;word=list(self.a)+list(self.old);delta=p^q;pivot=(delta&-delta).bit_length()-1
  others=[i for i in range(10) if i!=pivot];changed=[i for i in others if delta>>i&1]
  for i in changed:b.cx(word[pivot],word[i])
  transformed=p
  if p>>pivot&1:
   for i in changed:transformed^=1<<i
  code=sum((transformed>>i&1)<<j for j,i in enumerate(others))
  b.flip_if_equal(km.array([word[i] for i in others]),code,target=word[pivot],control=control)
  for i in reversed(changed):b.cx(word[pivot],word[i])
 def late_exceptions(self,k,flag,reverse=False):
  pairs={34:[((31,29),(1,1)),((0,2),(2,2))],35:[((30,28),(3,3)),((31,28),(4,4)),((0,3),(5,5)),((0,2),(6,6))]}.get(k,[])
  for (a,o),(c,d) in reversed(pairs) if reverse else pairs:self.transposition(a|(o<<5),c|(d<<5),flag)
 def push(self,index,flag):
  k=index+1;b=self.b
  if k<=31:
   b.cswap(flag,self.a,self.old)
   for i in range(5):
    if k>>i&1:b.cx(flag,self.a[i])
  else:
   for i in range(5):
    if (63-k)>>i&1:b.cx(flag,self.old[i])
   self.late_exceptions(k,flag)
  self.xor_read(index,flag)
 def pop(self,index,flag):
  k=index+1;b=self.b;self.xor_read(index,flag)
  if k<=31:
   for i in range(5):
    if k>>i&1:b.cx(flag,self.a[i])
   b.cswap(flag,self.a,self.old)
  else:
   self.late_exceptions(k,flag,True)
   for i in range(5):
    if (63-k)>>i&1:b.cx(flag,self.old[i])
 @contextmanager
 def access(self,indices):
  indices=sorted(set(indices));q=self.b.alloc_qubits(len(indices))
  for i,t in zip(indices,q):self.xor_read(i,t)
  try:yield dict(zip(indices,q))
  finally:
   for i,t in reversed(list(zip(indices,q))):self.xor_read(i,t)
   self.b.free(q)
 def release(self):self.b.free(self.a+self.old)
