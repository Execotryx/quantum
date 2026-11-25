#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0
# Credits: Opus and Astra.
"""Tiny static/source-only handoff audit; no native import or heavy job."""
from pathlib import Path
from fractions import Fraction
import ast,hashlib,json,resource,time

HERE=Path(__file__).resolve().parent;NARROW=HERE.parents[1]


def main():
    resource.setrlimit(resource.RLIMIT_AS,(128*1024**2,128*1024**2));started=time.monotonic()
    pins=json.loads((HERE/'INPUTS.json').read_text())['files']
    for row in pins:
        raw=(NARROW/row['path']).read_bytes()
        assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'],row['path']
    for path in HERE.glob('*.py'):compile(path.read_text(),str(path),'exec')
    bound=json.loads((NARROW/'research/postgate_angle_refit/quantize50_bound.json').read_text())
    coefficients=tuple((1<<i)+((1<<27) if i==0 else 0) for i in range(27))+(-(1<<27),)+tuple(1<<(27+j) for j in range(1,7))
    sites=tuple(f'base_i{i}' for i in range(27))+('threshold_j0',)+tuple(f'overflow_j{j}' for j in range(1,7))
    new=tuple(bound['new_generic_turn_units50']);delta=tuple(v//16384 for v in bound['delta_turn_units64'])
    assert all(bound['delta_turn_units64'])
    assert tuple((a<<13)+d for a,d in zip(coefficients,delta))==new
    tree=ast.parse((HERE/'variant.py').read_text())
    selected=[node for node in tree.body if isinstance(node,(ast.FunctionDef,ast.ClassDef)) and node.name in ('angle_class','AngleProxy')]
    assert len(selected)==2
    env=dict(Fraction=Fraction,COEFFICIENTS37=coefficients,NEW_TURN_UNITS50=new,SITES=sites)
    exec(compile(ast.Module(body=selected,type_ignores=[]),'candidate04_proxy_static','exec'),env)
    angle_class=env['angle_class'];Proxy=env['AngleProxy']

    class BuilderStub:
        def __init__(self):self.angles=[]
        def z_pow(self,target,angle):self.angles.append((target,Fraction(angle)))

    builder=BuilderStub();proxy=Proxy(builder)
    for i,a in enumerate(coefficients):proxy.z_pow('q'+str(i),Fraction(2*a,1<<37))
    for a in (Fraction(1,4),Fraction(1,4),Fraction(1,4),Fraction(-1,4),Fraction(1)):
        proxy.z_pow('q_test',a)
    record=proxy.finish();assert len(record)==34 and len(builder.angles)==39
    assert tuple(a for _,a in builder.angles[:34])==tuple(Fraction(2*v,1<<50) for v in new)
    for text in ('wrong generic order','extra generic site','wrong number of T calls'):
        trial=Proxy(BuilderStub())
        try:
            if text=='wrong generic order':trial.z_pow('q',Fraction(2*coefficients[1],1<<37))
            else:
                for a in coefficients:trial.z_pow('q',Fraction(2*a,1<<37))
                if text=='extra generic site':trial.z_pow('q',Fraction(1,1<<49))
                else:trial.finish()
        except AssertionError:pass
        else:raise AssertionError('Proxy accepted '+text)

    # Native text is only read, never executed. Its prior full proof pins it.
    text=(NARROW/'native/candidate03/candidate03.kmx').read_text()
    oldproof=json.loads((NARROW/'native/candidate03/whole_native_text_all.json').read_text())
    assert hashlib.sha256(text.encode()).hexdigest()==oldproof['native_text_sha256']
    oldangles=[Fraction(line.split()[2]) for line in text.splitlines() if line.startswith('Z_POW ')]
    generic=[a for a in oldangles if angle_class(a)=='generic']
    assert generic==[Fraction(2*v,1<<37)%2 for v in coefficients]
    assert sum(angle_class(a)=='T' for a in oldangles)==4
    assert sum(angle_class(a)=='Clifford' for a in oldangles)==1
    assert all(angle_class(Fraction(2*v,1<<50))=='generic' for v in new)
    assert max(Fraction(v,1<<50).denominator for v in new)==1<<50

    cases=0
    for k in range(11):
        for extra in [0]+[1<<i for i in range(1,26)]:
            p=1|(1<<26)|extra;word=((p<<k)+(p>>(27-k)))&((1<<37)-1);z=word&((1<<27)-1)
            features=[(z>>i)&1 for i in range(27)]+[int(k==0)]+[((z>>j)&1)*int(k>j) for j in range(1,7)]
            fixed=sum(((z>>j)&1)*int(k>j)*(1<<(40+j)) for j in (7,8,9))
            direct=(sum(f*a for f,a in zip(features,new))+fixed)&((1<<50)-1)
            perturbed=((word<<13)+sum(f*d for f,d in zip(features,delta)))&((1<<50)-1)
            assert direct==perturbed,(k,extra)
            cases+=1
    result=dict(status='PASS_STATIC_SOURCE_AND_PROXY_AUDIT_NO_NATIVE_EXECUTION',source_pins=len(pins),
        proxy_generic_replacements=34,proxy_unchanged_T=4,proxy_unchanged_Clifford=1,proxy_negative_tests=3,
        native03_text_source_pin_verified=True,native03_signed_to_canonical_angles_verified=True,
        direct_delta_identity_affine_basis_cases=cases,all_new_angle_classes_generic=True,phase_modulus=1<<50,
        syntax_sources=len(list(HERE.glob('*.py'))),native_imported=False,native_emitted=False,
        full_domain_scan_performed=False,seconds=time.monotonic()-started)
    (HERE/'STATIC_AUDIT.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))


if __name__=='__main__':main()
