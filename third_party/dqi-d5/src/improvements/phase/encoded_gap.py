"""Encode the phase's first-gap pointer with an explicit active bit.

Code k is represented by 2*k-1, and empty is zero. At each recursion's
prefix-scalings the pointer can only name an ancestor/current gap, so its
least-significant bit is exactly the required prefix predicate. The global
central middle map keeps a general prefix comparison. No approximation is
added; all pointer states are uncomputed before phase completion.
"""

def encode(code):return 2*code-1

def init(self,b,degree,vectors,counts):
    self.b,self.degree,self.counts=b,degree,counts
    self.pointer=b.alloc_qubits(max(1,encode(degree-1).bit_length()))
    self.vectors=vectors;self.constants=[None]*degree

def predicate(self,d,flag):
    import central_circuit as C
    b=self.b
    top,next_zero,conjunction=[b.alloc_qubits(1)[0]for _ in range(3)]
    b.flip_if_equal(d[-1],0,target=top)
    b.flip_if_equal(d[-2],0,target=next_zero);b.x(next_zero)
    b.init_and(top,next_zero,conjunction)
    b.x(self.pointer[0]);b.ccx(conjunction,self.pointer[0],flag);b.x(self.pointer[0])
    b.del_and(top,next_zero,conjunction)
    b.x(next_zero);b.flip_if_equal(d[-2],0,target=next_zero)
    b.flip_if_equal(d[-1],0,target=top)
    b.free(C.km.array([top,next_zero,conjunction]))
    self.counts['gap_predicates']+=1

def xor_code(self,flag,code):
    for bit,wire in enumerate(self.pointer):
        if encode(code)>>bit&1:self.b.cx(flag,wire)

def push(self,d,code):
    b=self.b;flag=b.alloc_qubits(1)[0]
    self.predicate(d,flag);self.xor_code(flag,code)
    b.flip_if_equal(self.pointer,encode(code),target=flag);b.free(flag)

def pop(self,d,code):
    b=self.b;flag=b.alloc_qubits(1)[0]
    b.flip_if_equal(self.pointer,encode(code),target=flag);self.xor_code(flag,code)
    self.predicate(d,flag);b.free(flag)

def read(self,code):
    flag=self.b.alloc_qubits(1)[0]
    self.b.flip_if_equal(self.pointer,encode(code),target=flag)
    return flag

def unread(self,code,flag):
    self.b.flip_if_equal(self.pointer,encode(code),target=flag);self.b.free(flag)

def prefix_xor(self,code,flag):
    if code>=self.degree-1:self.b.cx(self.pointer[0],flag)
    else:
        self.b.flip_if_less_than(self.pointer,2*code,target=flag)
        self.b.flip_if_equal(self.pointer,0,target=flag)

def active(self,code):return self.pointer[0]
def unactive(self,code,flag):assert flag==self.pointer[0]

_originals=None

def install():
    global _originals
    import central_circuit as C
    names=('__init__','predicate','xor_code','push','pop','read','unread','prefix_xor','run','base')
    if _originals is None:_originals={n:getattr(C.CentralGap,n)for n in names}
    methods={'__init__':init,'predicate':predicate,'xor_code':xor_code,'push':push,'pop':pop,'read':read,'unread':unread,'prefix_xor':prefix_xor,'run':run,'base':base}
    for n,f in methods.items():setattr(C.CentralGap,n,f)
    C.CentralGap.active=active;C.CentralGap.unactive=unactive

def uninstall():
    if _originals is not None:
        import central_circuit as C
        for n,f in _originals.items():setattr(C.CentralGap,n,f)

# The two methods below are source-preserving copies of the supplied
# Apache-2.0 CentralGap methods, with only recursion-local prefix readers
# changed to active/unactive. The field helpers are resolved dynamically so
# the existing norm-guard and quotient-interpolation patches remain active.
def run(self, b, p, d, vectors, counts, *, reverse=False, monic=False):
    from central_circuit import Scaling, product, divide_locator, controlled_scale, rotate
    n = len(d)
    if n == 1:
        assert not monic
        return self.base(b, p, d, vectors, counts, reverse=reverse)
    code = self.degree-n+1
    self.constants[n-1] = p[n-1]
    self.push(d, code)
    flag = self.read(code)
    rotate(b, d, flag)
    counts["controlled_word_swaps"] += n-1
    self.unread(code, flag)

    def low_update():
        for v in vectors:
            for i in range(n-1):
                product(b, d[i], v[n-1], v[i], counts)

    def high_update():
        for v in vectors:
            for i in range(n-1):
                product(b, d[i], v[i], v[n-1], counts)

    def enter(inv):
        scale = Scaling(b, d[-1], counts)
        if not inv:
            for v in vectors:
                scale.apply(v[-1], divide=True)
            low_update()
            divide_locator(b, p, d, scale, counts, monic=monic)
            if monic:
                for v in vectors:
                    scale.apply(v[-1], divide=False)
        else:
            if monic:
                for v in vectors:
                    scale.apply(v[-1], divide=True)
            divide_locator(b, p, d, scale, counts, reverse=True, monic=monic)
            low_update()
            for v in vectors:
                scale.apply(v[-1], divide=False)
        scale.close()

    def first(inv):
        if monic:
            return
        scale = Scaling(b, p[n], counts)
        for v in vectors:
            scale.apply(v[-1], divide=not inv)
        scale.close()

    def descend(inv):
        self.run(b, d, p[:n-1], [v[:n-1] for v in vectors], counts, reverse=inv)

    def extra(inv):
        if monic:
            return
        flag = self.active(code)
        scale = Scaling(b, p[n], counts)
        for v in vectors:
            controlled_scale(scale, v[-1], flag, divide=not inv)
        scale.close()
        self.unactive(code, flag)

    def leave(inv):
        flag = self.active(code) if monic else None
        scale = Scaling(b, d[-1], counts)
        if not inv:
            if monic:
                for v in vectors:
                    controlled_scale(scale, v[-1], flag, divide=False)
            high_update()
            for v in vectors:
                scale.apply(v[-1], divide=True)
            divide_locator(b, p, d, scale, counts, reverse=True, monic=monic)
        else:
            divide_locator(b, p, d, scale, counts, monic=monic)
            for v in vectors:
                scale.apply(v[-1], divide=False)
            high_update()
            if monic:
                for v in vectors:
                    controlled_scale(scale, v[-1], flag, divide=True)
        scale.close()
        if monic:
            self.unactive(code, flag)

    actions = [enter, first, descend, extra, leave]
    for action in reversed(actions) if reverse else actions:
        action(reverse)
    flag = self.read(code)
    rotate(b, d, flag, reverse=True)
    counts["controlled_word_swaps"] += n-1
    self.unread(code, flag)
    self.pop(d, code)

def base(self, b, p, d, vectors, counts, *, reverse):
    from central_circuit import Scaling, product, divide_locator, controlled_scale, rotate
    assert len(p) == 2 and len(d) == 1
    self.constants[0] = p[0]

    def enter(inv):
        scale = Scaling(b, d[0], counts)
        if not inv:
            scale.apply(p[0], divide=True)
            scale.apply(p[1], divide=True)
        for v in vectors:
            scale.apply(v[0], divide=not inv)
        if inv:
            scale.apply(p[1], divide=False)
            scale.apply(p[0], divide=False)
        scale.close()

    def first(inv):
        scale = Scaling(b, p[1], counts)
        for v in vectors:
            scale.apply(v[0], divide=not inv)
        scale.close()

    def middle(inv):
        self.middle(reverse=inv)

    def extra(inv):
        flag = self.active(self.degree)
        scale = Scaling(b, p[1], counts)
        for v in vectors:
            controlled_scale(scale, v[0], flag, divide=not inv)
        scale.close()
        self.unactive(self.degree, flag)

    def leave(inv):
        scale = Scaling(b, d[0], counts)
        if inv:
            scale.apply(p[0], divide=True)
            scale.apply(p[1], divide=True)
        for v in vectors:
            scale.apply(v[0], divide=not inv)
        if not inv:
            scale.apply(p[1], divide=False)
            scale.apply(p[0], divide=False)
        scale.close()

    actions = [enter, first, middle, extra, leave]
    for action in reversed(actions) if reverse else actions:
        action(reverse)

