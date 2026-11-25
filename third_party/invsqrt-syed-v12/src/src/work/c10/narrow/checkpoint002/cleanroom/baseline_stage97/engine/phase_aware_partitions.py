# Copyright 2026 Syed Asad Ali (team syed3000)
# SPDX-License-Identifier: Apache-2.0
"""Choose inverse carry partitions using the conditioned-terminal cost.

Only the schedule changes: each segment is an existing exact arithmetic
kernel. The default source selector's ordinary-versus-dirty comparison does
not include the quarter-Toffoli benefit of the opt-in terminal fusion.
"""
from contextlib import contextmanager
import kickmix as km
import paired_arithmetic as paired
import virtual_lsb


def _cost(a,incoming,sizes,pool,*,release_input,overflow_phase):
    start=sum(sizes[:-1]);length=sizes[-1]
    prefix=sum(n+0.5*(n-1) for n in sizes[:-1])
    release=0.5 if release_input and len(sizes)>1 else 0.0
    if pool is not None:
        real=next((i for i,w in enumerate(a[start:]) if w is False),length)
        terminal=paired.terminal_cost(length,real)
        if overflow_phase:terminal+=0.5*paired.dirty_mcz_cost(length-real+1)
    else:
        terminal=length-1+(0.5 if overflow_phase and length>=2 else 0)
        if (overflow_phase and length>=4 and a[-2] is False and a[-1] is False and
                (isinstance(incoming,km.q) or any(w is not False for w in a[:-3]))):
            terminal-=0.25
    return prefix+terminal+release


@contextmanager
def use_phase_aware_partitions(*,enable_overflow_search=False):
    """Use with the proved conditioned-terminal pass.

    enable_overflow_search enables the existing proved ordinary/dirty
    terminal comparison for every overflow-phase inverse adder. It only
    changes in-memory bindings during this context; source defaults remain
    untouched. No additional clean or dirty allocation is requested.
    """
    original=paired._terminal_partition
    original_inverse=paired.inverse_add;original_virtual=virtual_lsb.inverse_add
    def choose(a,b,incoming,clean,external_dirty,*,release_input=False,
               ordinary_final=False,allow_dirty_terminal=True,overflow_phase=False):
        sizes,pool=original(a,b,incoming,clean,external_dirty,
            release_input=release_input,ordinary_final=ordinary_final,
            allow_dirty_terminal=allow_dirty_terminal,overflow_phase=overflow_phase)
        if not ordinary_final or not overflow_phase:return sizes,pool
        best=(_cost(a,incoming,sizes,pool,release_input=release_input,
                    overflow_phase=overflow_phase),tuple(sizes),pool)
        width=len(b);states={(0,0):()}
        for used in range(clean+1+int(release_input)):
            for (start,count),prefix in list(states.items()):
                if count!=used:continue
                capacity=clean-used+int(release_input and used>0)
                if width-start<=capacity+2:
                    trial=prefix+(width-start,)
                    score=_cost(a,incoming,trial,None,release_input=release_input,overflow_phase=True)
                    if (score,trial)<best[:2]:best=(score,trial,None)
                if used==clean+int(release_input):continue
                for length in range(1,min(capacity,width-start-1)+1):
                    key=(start+length,used+1);trial=prefix+(length,)
                    if key not in states or trial<states[key]:states[key]=trial
        return list(best[1]),best[2]
    paired._terminal_partition=choose
    if enable_overflow_search:
        def inverse(builder,source,target,debt,**kwargs):
            if kwargs.get('overflow_phase') is not None:kwargs['allow_dirty_overflow']=True
            return original_inverse(builder,source,target,debt,**kwargs)
        paired.inverse_add=inverse;virtual_lsb.inverse_add=inverse
    try:yield
    finally:
        paired._terminal_partition=original
        paired.inverse_add=original_inverse;virtual_lsb.inverse_add=original_virtual
