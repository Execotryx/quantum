"""Load the installed competition helpers without vendoring competition data."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT / 'data/comp/kickmix'), str(ROOT / 'data/comp/verifiers/dqi')]

import kickmix as km  # noqa: E402
import dqi_reference_circuit as ref  # noqa: E402
import verify_submission_dqi as verifier  # noqa: E402


def build(builder, *, iterations=None, decoder_type=None):
    """Build the official decoder, allowing a builder with alternative arithmetic."""
    syndromes = [builder.create_quantum_register(12, name=f'S{i}') for i in range(70)]
    outcomes = [builder.create_classical_register(12, name=f'E{j}') for j in range(4095)]
    decoder_type = ref.ProosAndZalkaDecoder if decoder_type is None else decoder_type
    decoder_type(70, km.GF2Field(12)).build_syndrome_decoding_mbuc(
        builder, syndromes=syndromes, error_mbuc=outcomes,
        n_iters=ref.default_n_iters(70) if iterations is None else iterations)
    return builder.finish_circuit()
