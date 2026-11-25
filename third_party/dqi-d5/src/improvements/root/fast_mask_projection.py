"""Exact sparse mixed-radix DFT for the classical round12 mask projection.

Only classical masks are transformed. Quantum syndrome words participate in
exactly the incumbent's trace phase. This changes no Toffolis or qubit width.
"""
from functools import cache

RADICES=(3,3,5,7,13)

@cache
def mul_columns(coefficient):
    import mask_projection as M
    return tuple(M.GF.mul(coefficient,1<<bit) for bit in range(12))


def linear_word(b,terms):
    """Create a classical word holding a public linear combination."""
    import mask_projection as M
    combined={}
    for word,coefficient in terms:
        if word is None or not coefficient:continue
        key=tuple(word)
        if key in combined:combined[key][1]^=coefficient
        else:combined[key]=[word,coefficient]
    terms=[(word,c)for word,c in combined.values()if c]
    if not terms:return None,[]
    if len(terms)==1 and terms[0][1]==1:return terms[0][0],[]
    target=b.alloc_bits(12);b.bit_store(target,False)
    for word,c in terms:M.xor_linear(b,word,target,mul_columns(c))
    return target,[target]


def sparse_dft(b,words,root,radices=RADICES):
    """Return values of sum_i words[i]*x^i at x=root^j.

    None denotes the compile-time zero polynomial coefficient. Every gate
    and radix choice depends only on public coefficients and array lengths.
    The ownership list contains just newly allocated result words.
    """
    import mask_projection as M
    gf=M.GF;n=len(words);active=[i for i,w in enumerate(words)if w is not None]
    if not active:return [None]*n,[]
    if n==1:return list(words),[]
    if len(active)==1 and active[0]==0:return [words[0]]*n,[]
    r=radices[0];assert n%r==0;m=n//r
    children=[];child_owned=[]
    for s in range(r):
        vals,owned=sparse_dft(b,words[s::r],gf.pow(root,r),radices[1:])
        children.append(vals);child_owned.extend(owned)
    result=[None]*n;created=[]
    for k in range(m):
        for ell in range(r):
            j=k+m*ell
            terms=[(children[s][k],gf.pow(root,s*j))for s in range(r)]
            result[j],new=linear_word(b,terms);created.extend(new)
    keep={tuple(w)for w in result if w is not None}
    kept=[]
    for w in child_owned:
        if tuple(w)in keep:kept.append(w)
        else:b.bit_store(w,False);b.free(w)
    return result,created+kept


def projected_record(builder,syndromes,outcomes):
    import mask_projection as M
    b=builder;gf=M.GF
    assert len(syndromes)==70 and len(outcomes)==4095
    basis=M.dual_basis()
    vandermonde=[[gf.pow(gf.primitive_element,(i+1)*j%4095)for i in range(70)]for j in range(70)]
    inverse=M.inverse_matrix(vandermonde)
    lambdas=[b.alloc_bits(12)for _ in range(70)]
    for i,row in enumerate(inverse):
        b.bit_store(lambdas[i],False)
        for j,c in enumerate(row):
            if c:M.xor_linear(b,outcomes[j],lambdas[i],[gf.mul(c,d)for d in basis])
    for i,word in enumerate(lambdas):
        for s in range(12):
            for t in range(12):
                if M.trace(gf.mul(1<<s,1<<t)):b.cz(word[s],syndromes[i][t])
    coefficients=[None]+lambdas+[None]*(4095-71)
    values,owned=sparse_dft(b,coefficients,gf.primitive_element)
    residual=[]
    mask_columns=tuple(M.field_to_mask(1<<i)for i in range(12))
    for j,original in enumerate(outcomes):
        changed=b.alloc_bits(12);b.bit_store(changed,False)
        if j>=70:
            b.cx(original,changed)
            if values[j] is not None:M.xor_linear(b,values[j],changed,mask_columns)
        residual.append(changed)
    for w in owned:b.bit_store(w,False);b.free(w)
    for w in lambdas:b.bit_store(w,False);b.free(w)
    return residual


def install():
    import mask_projection as M
    M.projected_record=projected_record
    return {'mask_projection':'exact sparse mixed-radix4095 DFT','radices':list(RADICES),'changes_quantum_arithmetic':False}
