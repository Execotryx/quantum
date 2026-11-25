#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0
# Credits: Opus and Astra.
"""Independent finite algebra checks for the new consuming row interfaces."""
import hashlib,json,resource
from pathlib import Path
resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,512*1024**2))
HERE=Path(__file__).resolve().parent


def main():
    feed=0;tail=0;inverse=0;carrychecks=0
    for v in range(4096):
        V=4096+v
        for sig in (0,1):
            for prev in (0,1):
                for cur in (0,1):
                    c=(v&1)^((cur^prev)*((v&1)^sig^prev))
                    low=(v&1)^sig^cur^prev
                    c_after=(v&1)^((cur^low)*((v&1)^sig^low))
                    assert c==c_after;carrychecks+=1
                    for t in (0,1,8191):
                        old=t-8192*sig
                        framed=t^(8191*(1-sig))
                        target=(framed+(v>>1)+c+2048)&8191
                        target^=8191*(1-sig)
                        actual=2*target+low
                        wanted=(2*old+(2*sig-1)*V+sig+cur-prev)&16383
                        assert actual==wanted,(v,sig,prev,cur,t,actual,wanted)
                        restored=((target^(8191*(1-sig)))-(v>>1)-c-2048)&8191
                        restored^=8191*(1-sig)
                        restored_prev=low^(v&1)^sig^cur
                        assert restored==t and restored_prev==prev
                        feed+=1;inverse+=1
            for k in (0,2,3,4,5,6,7,8,9):
                for t in (0,1,8191):
                    old=t-8192*sig
                    rotated=((old<<1)+sig)&16383
                    width=13-k;mask=(1<<width)-1
                    high=rotated>>(k+1)
                    framed=high^(mask*(1-sig))
                    nxt=(framed+(v>>(k+1))+((v>>k)&1)+(1<<(11-k)))&mask
                    nxt^=mask*(1-sig)
                    actual=(rotated&((1<<(k+1))-1))|(nxt<<(k+1))
                    actual^=v&1
                    A=(((V>>(k+1))+((V>>k)&1))<<(k+1))-(V&1)
                    wanted=(2*old+sig+(2*sig-1)*A)&16383
                    assert actual==wanted,(v,sig,k,t,actual,wanted)
                    tail+=1
    out=dict(status='PASS_EXACT_ROW_ALGEBRA_AND_OWNER_PERMUTATION_NOT_NATIVE',
             feed_checks=feed,inverse_feed_checks=inverse,tail_checks=tail,
             carry_phase_function_checks=carrychecks,
             whole_word_quantifier='The remainder-low word appears only as2*t modulo2^14 on both sides; checking the constant term proves all8192 t values for each certified v/sign/input case. Additional t=1,8191 checks verify the explicit wrap implementation.',
             ownership='Forward feed replaces (u14,prev,cur) by ([prev]+u[:13],cur,old_u13); inverse uses these current owners to reconstruct every original value.',
             feed_carry_phase='c(v0,prev,cur,sigma)=c(v0,L,cur,sigma), degree2 in live output bits.',
             source_sha256=hashlib.sha256((HERE/'divider.py').read_bytes()).hexdigest())
    p=HERE/'divider_local_math.json';p.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out,indent=2))


if __name__=='__main__':main()
