"""Exact zero-scratch x**17 over GF(4096) through GF(16) coordinates."""
from functools import cache
@cache
def data():
 from common import km
 from tower import elimination_gates,xor_columns
 f,g=km.GF2Field(12),km.GF2Field(4)
 def evalmod(x):
  v=0
  for i in range(5):
   if g.modulus>>i&1:v^=f.pow(x,i)
  return v
 beta=next(x for x in range(2,4096)if evalmod(x)==0)
 embed=[f.pow(beta,i)for i in range(4)];theta=next(x for x in range(2,4096)if f.pow(x,16)!=x)
 cols=[f.mul(f.pow(theta,j),a)for j in range(3)for a in embed]
 assert len({xor_columns(cols,i)for i in range(4096)})==4096
 gates=tuple(elimination_gates(cols))
 weights=[(i,j,f.mul(f.pow(theta,i),f.pow(theta,16*j))^f.mul(f.pow(theta,j),f.pow(theta,16*i)))for i in range(3)for j in range(i+1,3)]
 return f,g,cols,gates,weights

def transform(b,w,gates,inverse=False):
 for op,i,j in reversed(gates)if inverse else gates:getattr(b,op)(w[i],w[j])

def xor_gold17(b,source,target):
 f,g,cols,gates,weights=data()
 transform(b,source,gates)
 for bit,col in enumerate(cols):
  val=f.pow(col,17)
  for j in range(12):
   if val>>j&1:b.cx(source[bit],target[j])
 for i,j,weight in weights:
  b.gf2_idiv(weight,target=target,field=f)
  transform(b,target,gates)
  b.ixor_gf2_mul(source[4*i:4*i+4],source[4*j:4*j+4],target=target[:4],field=g)
  transform(b,target,gates,inverse=True)
  b.gf2_imul(weight,target=target,field=f)
 transform(b,source,gates,inverse=True)
