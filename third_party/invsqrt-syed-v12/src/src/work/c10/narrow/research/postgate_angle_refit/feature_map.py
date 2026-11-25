#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0
# Credits: Opus and Astra.
"""Formal feature-site identity for all11 exponent classes; no native emission."""
import hashlib,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;NARROW=HERE.parents[1]
sys.path.insert(0,str(NARROW/'native/candidate01'))
import divider
assert hashlib.sha256((NARROW/'native/candidate01/divider.py').read_bytes()).hexdigest()=='d0dbaf6fe4227da988c9cb9e9dee847624992c7c5cce7ab347990d5b0a116c05'


def poly(v,terms):
 out=0
 for mask in terms:
  value=1
  for i in range(len(v)):
   if mask>>i&1:value&=v[i]
  out^=value
 return out


def normalized_label(i):return 'one'if i in (0,26)else f'p{i}'
rows=[]
for k in range(11):
 flags=[k>>i&1 for i in range(4)]
 variables=flags+[poly(flags,(6,10)),poly(flags,(10,))]
 values=list(range(27));route_controls=[]
 for centre,terms in zip(divider.CENTRES,divider.CONTROLS):
  control=poly(variables,terms);route_controls.append(control)
  if control:
   for i in range(27):
    j=(centre-i)%27
    if i<j:values[i],values[j]=values[j],values[i]
 slots=[values[i]for i in divider._slots()]
 expected=[(i-k)%27 for i in range(27)]
 assert [normalized_label(i)for i in slots]==[normalized_label(i)for i in expected],k
 assert 1-poly(variables,divider.THRESHOLDS[1])==int(k==0)
 for j in range(1,7):
  control=poly(variables,divider.THRESHOLDS[j+1]);assert control==int(k>j),(k,j,control)
 assert variables[-1]==int(k==10)
 rows.append(dict(k=k,route_controls=route_controls,formal_generic_data_labels=[normalized_label(i)for i in slots],overflow_predicates=[int(k>j)for j in range(1,7)]))
result=dict(status='PASS_FORMAL_GENERIC_FEATURE_IDENTITY',exponent_classes=11,arbitrary_unshifted_variable_bits=25,generic_sites=34,T_sites_unchanged=4,all_classes=rows,divider_sha256='d0dbaf6fe4227da988c9cb9e9dee847624992c7c5cce7ab347990d5b0a116c05',native_emission=False,phase_fit_authorized=False)
(HERE/'feature_map.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items()if k!='all_classes'},indent=2))
