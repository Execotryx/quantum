#!/usr/bin/env python3
# Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0
# Credits: Opus and Astra.
"""Bounded static source/pin/mock-route audit, without importing native code."""
from pathlib import Path
from contextlib import contextmanager
from types import SimpleNamespace
import ast,hashlib,json,resource,time

HERE=Path(__file__).resolve().parent;NARROW=HERE.parents[1]


def main():
    resource.setrlimit(resource.RLIMIT_AS,(128*1024**2,128*1024**2));began=time.monotonic()
    pins=json.loads((HERE/'INPUTS.json').read_text())['files']
    for row in pins:
        raw=(NARROW/row['path']).read_bytes();assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'],row['path']
    for path in HERE.glob('*.py'):compile(path.read_text(),str(path),'exec')
    accepted=json.loads((NARROW/'PAPER_GATE_RECEIPT_016_VARIANT.json').read_text())
    assert sum(accepted['Toffoli_components'].values())==1560.5
    assert accepted['complete_predicted_cost']==49*(1560.5+1+accepted['rotation_charge'])
    proof=json.loads((NARROW/'native/candidate04/whole_native_text_all.json').read_text())
    quant=json.loads((NARROW/'research/postgate_angle_refit/quantize50.json').read_text())
    assert proof['phase_units50_sha256']==quant['quantized_phase50_sha256']
    assert proof['proved_inputs']==3133452 and proof['every_HMR_transcript_proved']
    assert quant['exact_statistics']['quantized50']['minimum_margin_units']==124372027
    certificate=json.loads((NARROW/'research/postgate_route_constants/offsets.json').read_text())
    assert certificate['selected_centres']==accepted['centres'] and certificate['selected_omissions']==[[0,0,26]]
    controls=((2,4,8),(0,4,16),(0,2,4,16),(0,1,4,8),(0,1))
    @contextmanager
    def affine(builder,variables,terms):
        stage=controls.index(terms);builder.log.append(('frame_in',stage))
        try:yield f'control{stage}'
        finally:builder.log.append(('frame_out',stage))
    divider=SimpleNamespace(CENTRES=tuple(accepted['centres']),CONTROLS=controls,_affine_control=affine)
    env=dict(divider=divider,NEW_CENTRES=tuple(accepted['centres']),OLD_CENTRES=(0,-2,-6,0,-1),
             ROUTE_TRACE=[],operation_count=lambda builder:len(builder.log))
    tree=ast.parse((HERE/'variant.py').read_text());node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='route')
    exec(compile(ast.Module(body=[node],type_ignores=[]),'candidate05_mock_route','exec'),env)
    class Builder:
        def __init__(self):self.log=[]
        def cswap(self,*args):self.log.append(('CSWAP',args))
    for inverse in(False,True):
        builder=Builder();env['route'](builder,[f'word{i}' for i in range(27)],[],inverse=inverse)
        row=env['ROUTE_TRACE'][-1]
        assert len(row['old_cswap_arguments'])==65 and len(row['new_cswap_arguments'])==64
        assert row['omissions']==[dict(stage=0,positions=[0,26],control='control0',owners=['word0','word26'])]
        assert sum(gate[0]=='CSWAP' for gate in builder.log)==64
        assert sum(gate[0].startswith('frame') for gate in builder.log)==10
    result=dict(status='PASS_STATIC_CANDIDATE05_SOURCE_PIN_AND_ROUTE_AUDIT_NO_NATIVE',
        inherited_source_pins=len(pins),syntax_sources=len(list(HERE.glob('*.py'))),
        mock_directions=2,CSWAP_per_direction=64,unchanged_affine_frames_per_direction=5,
        exact_omission=[0,0,26],unchanged_quantized_full_domain_digest=True,
        parent_gate_component_sum=1560.5,complete_expected_cost=accepted['complete_predicted_cost'],
        native_imported=False,native_emitted=False,native_executed=False,seconds=time.monotonic()-began)
    (HERE/'STATIC_AUDIT.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))


if __name__=='__main__':main()
