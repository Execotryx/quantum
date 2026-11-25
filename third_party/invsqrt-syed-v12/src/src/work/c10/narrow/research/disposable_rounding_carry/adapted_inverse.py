# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0
# Credits: Opus and Astra.
# Source-derived paper adaptation; evaluated only in the isolated lifecycle module namespace.
def product_inverse_disposable(builder,D,word,token,dirty):
    word=list(word);C=[False]+list(D);builder.x(word[15])
    for i in reversed(range(10)):
        q=word[6+i];target=word[:6+i];source=C[9-i:]if i<9 else C
        for t in target:builder.cx(q,t)
        carry=_product_carry(builder,C,q,i)
        released_input=product_ar.inverse_add(builder,source,target,token.rows[i],carry_in=carry,
            dirty_wires=dirty+word[6:],carry_lifecycle=(
                lambda value: _clear_product_carry(builder,C,q,i,value),
                lambda: _product_carry(builder,C,q,i)) if i<8 else None)
        if not released_input:
            _clear_product_carry(builder,C,q,i,carry)
        for t in target:builder.cx(q,t)
    builder.x(word[15])
    assert all(d.consumed and not d.measurements for d in token.rows)
    return word[:6],word[6:]


def coefficient_inverse_disposable(builder,v,D,H,token,dirty):
    S=[v[8]]+list(H)
    ar._deferred_overflow(builder,v[:5],S,D,token,inverse=True)
    saved=ar.release_saved_bit(builder,token.saved_bit);token.saved_bit=None
    for i in reversed(range(5)):
        k=4-i;carry=_coefficient_carry(builder,S,v[i],k)
        for q in D[:7]:builder.cx(v[i],q)
        released_input=ar.inverse_add(builder,S[k+1:],D[:7],token.row_debts[i],carry_in=carry,
            dirty_wires=dirty,carry_lifecycle=(
                lambda value: _clear_coefficient_carry(builder,S,v[i],k,value),
                lambda: _coefficient_carry(builder,S,v[i],k)))
        for q in D[:7]:builder.cx(v[i],q)
        if not released_input:
            _clear_coefficient_carry(builder,S,v[i],k,carry)
    ar.repay_saved_bit(builder,D[6],saved)
    assert all(d.consumed and not d.measurements for d in token.row_debts)
    assert token.overflow_debt.consumed and not token.overflow_debt.measurements

