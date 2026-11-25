"""Pack the two 6-bit gap pointers into a 10-bit rank only across Forney.

All pairs with zero, one or two gaps are supported. Forney never queries
history, so relatively expensive coherent encoding is paid only twice.
No additional approximation beyond the two-pointer overflow is introduced.
"""
from functools import cache


@cache
def tables():
    triangle=tuple(b*(b-1)//2 if b<=35 else 0 for b in range(64))
    decode=[0]*1024
    for b in range(1,36):
        for a in range(b):decode[b*(b-1)//2+a]=a|(b<<6)
    decode[630]=0
    return triangle,tuple(decode)


def walk_lookup(b,address,table,emit,*,parent=True):
    """An explicit unary tree with free MBU deletion of prefix ANDs."""
    if not any(table):return
    if len(set(table))==1:
        emit(parent,table[0]);return
    bit=address[-1];half=len(table)//2
    low,high=table[:half],table[half:]
    have_low,have_high=any(low),any(high)
    if parent is True:
        if have_low:
            b.x(bit);walk_lookup(b,address[:-1],low,emit,parent=bit);b.x(bit)
        if have_high:walk_lookup(b,address[:-1],high,emit,parent=bit)
        return
    flag=b.alloc_qubits(1)[0]
    if have_low:
        b.x(bit);b.init_and(parent,bit,flag);b.x(bit)
        walk_lookup(b,address[:-1],low,emit,parent=flag)
        if have_high:
            b.cx(parent,flag)
            walk_lookup(b,address[:-1],high,emit,parent=flag)
            b.del_and(parent,bit,flag)
        else:
            b.x(bit);b.del_and(parent,bit,flag);b.x(bit)
    else:
        b.init_and(parent,bit,flag)
        walk_lookup(b,address[:-1],high,emit,parent=flag)
        b.del_and(parent,bit,flag)
    b.free(flag)


def xor_lookup(b,address,target,table):
    def emit(flag,value):
        for i in range(len(target)):
            if value>>i&1:b.cx(flag,target[i])
    walk_lookup(b,address,table,emit)


def phase_lookup(b,address,mask,table):
    def emit(flag,value):
        for i in range(len(mask)):
            if value>>i&1:b.cz(mask[i],flag)
    walk_lookup(b,address,table,emit)


def orient(b,pointers,*,inverse=False):
    a,c=pointers
    flag=b.alloc_qubits(1)[0]
    b.flip_if_equal(a if inverse else c,0,target=flag)
    b.cswap(flag,a,c)
    b.flip_if_equal(c if inverse else a,0,target=flag)
    b.free(flag)


def empty_toggle(b,right,code):
    flag=b.alloc_qubits(1)[0]
    b.flip_if_equal(right,0,target=flag)
    for i in range(10):
        if 630>>i&1:b.cx(flag,code[i])
    b.flip_if_equal(right,0,target=flag)
    b.free(flag)


def compute_rank(b,pointers,code):
    triangle,_=tables()
    b.init_lookup(table=triangle,address=pointers[1],target=code)
    b.iadd(pointers[0],target=code)
    empty_toggle(b,pointers[1],code)


def uncompute_rank(b,pointers,code):
    triangle,_=tables()
    empty_toggle(b,pointers[1],code)
    b.isub(pointers[0],target=code)
    xor_lookup(b,pointers[1],code,triangle)


def pack(b,pointers):
    from common import km
    _,decode=tables()
    orient(b,pointers)
    code=b.alloc_qubits(10)
    compute_rank(b,pointers,code)
    pair=km.array([*pointers[0],*pointers[1]])
    measured=b.alloc_bits(12)
    b.hmr(pair,measured)
    b.free(pair)
    phase_lookup(b,code,measured,decode)
    b.free(measured)
    return code


def unpack(b,code):
    _,decode=tables()
    pair=b.alloc_qubits(12)
    b.init_lookup(table=decode,address=code,target=pair)
    pointers=[pair[:6],pair[6:]]
    measured=b.alloc_bits(10)
    b.hmr(code,measured)
    compute_rank(b,pointers,code)
    b.cz(measured,code)
    uncompute_rank(b,pointers,code)
    b.free(measured+code)
    orient(b,pointers,inverse=True)
    return pointers
