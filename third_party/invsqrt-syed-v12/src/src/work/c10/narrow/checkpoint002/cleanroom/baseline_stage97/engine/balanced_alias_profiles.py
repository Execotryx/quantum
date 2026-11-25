# Copyright 2026 Syed Asad Ali (team syed3000)
# SPDX-License-Identifier: Apache-2.0
"""Fit a balanced profile with genuine affine address/output aliases.

This entry point recomputes residue certificates, solves the affine frame,
selects coefficients, and fits phase angles from benchmark parameters. No
coefficient, phase, or circuit file is an input. The decoder's own original
`affine_labels` module must be importable alongside the numerical modules.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
from pathlib import Path

from affine_labels import search_affine_labels
from balanced_alias_search import search_residue_rows, assemble_residue_model
from balanced_model import fit_balanced, fit_angles, validate_balanced
from numerical_core import Parameters
from profiles import canonical_bytes, phase_angle_table, profile_resources


def generate_balanced_alias_profile(*, verbose=False):
    search=search_residue_rows(radius_b=12,radius_c=32,
                               curvature_storage_shift=3,
                               required_margin_turns=1e-12,verbose=verbose)
    # Record the exhaustive negative result for a third affine alias, then
    # construct the supported two-bit frame. Both solver calls are exact.
    three=search_affine_labels(search['masks'],alias_bits=3)
    two=search_affine_labels(search['mod4_masks'],alias_bits=2)
    if two is None:
        raise ArithmeticError('No two-bit affine address frame satisfies these residue certificates.')
    frame=dict(status='FOUND',exhaustive=True,plan=asdict(two),labels=list(two.labels))
    p=Parameters(output_fraction_bits=26,derivative_fraction_bits=25,
                 address_sharing=False)
    # This ordinary fit supplies the common model metadata. Its rows are
    # replaced by the independently certified residue selections below.
    template=fit_balanced(p,radius_b=12,radius_c=32,curvature_storage_shift=3,
                          derivative_storage_shift=1,verbose=verbose)
    model=assemble_residue_model(template,search,frame)
    raw=validate_balanced(model)
    if raw['status']!='PASS':
        raise ArithmeticError('The selected affine coefficient model failed its full-input certificate.')
    angles=fit_angles(model,verbose=verbose)
    if angles['status']!='PASS':
        raise ArithmeticError('The frozen affine-profile phase angles have no positive margin.')
    result=dict(profile_name='g25_r17_balanced_c8_A_alias2',model=model,angles=angles,
                phase_angles=phase_angle_table(angles),extra_phase_features=[],
                resources=profile_resources(model,angles),raw_arithmetic_certificate=raw,
                affine_address_frame=frame,
                residue_search_certificate=dict(
                    required_raw_margin_turns=search['required_raw_margin_turns'],
                    radius_b=search['radius_b'],radius_c=search['radius_c'],
                    masks_mod8=search['masks'],masks_mod4=search['mod4_masks'],
                    three_affine_aliases_infeasible=(three is None)))
    result['profile_sha256']=hashlib.sha256(canonical_bytes(result)).hexdigest()
    return result


