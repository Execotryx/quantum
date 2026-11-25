# Source-derived paper callback adaptation; not a native variant.
# Copyright 2026 Syed Asad Ali. Apache-2.0. Credits Opus and Astra.
def cleanup_divider_disposable(builder,token):
    """Reverse all rows, pay every CarryDebt, then clear direct u12."""
    assert not token.consumed;token.consumed=True
    v=token.v
    for j,k,debt in reversed(token.rows):
        u=token.u
        if j<=24:
            low=u[0];target=u[1:];sign=token.history[j]
            cur=token.P[23-j]if j<24 else None
            if j<24:assert cur is not None
            carry=_feed_carry(builder,v,low,cur,sign)
            _frame(builder,sign,target);_leading_offset(builder,target,inverse=True)
            released_input = inverse_add(builder,v[1:],target,debt,carry_in=carry,dirty_wires=_dirty(token),
                carry_lifecycle=(
                    lambda value: _feed_erase(builder,value,v,low,cur,sign),
                    lambda: _feed_carry(builder,v,low,cur,sign)))
            _frame(builder,sign,target)
            if not released_input:
                _feed_erase(builder,carry,v,low,cur,sign)
            if cur is not None:builder.cx(cur,low)
            builder.cx(sign,low);builder.cx(v[0],low)
            token.P[24-j]=low;token.u=target+[sign];del token.history[j]
        else:
            builder.cx(v[0],u[0]);sign=u[0];target=u[k+1:]
            _frame(builder,sign,target);_leading_offset(builder,target,inverse=True)
            inverse_add(builder,v[k+1:],target,debt,carry_in=v[k],dirty_wires=_dirty(token))
            _frame(builder,sign,target);token.u=u[1:]+u[:1]
        assert debt.consumed and not debt.measurements
        assert builder.num_allocated_qubits==43
    assert tuple(token.u)==token.initial_u and not token.history
    token.P=cleanup_u12(builder,v,token.P,token.u)
    assert builder.num_allocated_qubits==31 and all(q is not None for q in token.P)
    return list(token.P)
