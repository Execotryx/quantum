"""Build the source-only Q880 candidate with the accepted patch sequence."""
from pathlib import Path
import argparse,os,subprocess,sys
ROOT=Path(__file__).resolve().parent
PATCHES=[
 'round13/extraction/norm_guard_scaling.py',
 'round13/phase/top_quotient.py',
 'round13/conversion/banded_conversion.py',
 'improvements/conversion/gap_polynomial_conversion.py',
 'improvements/phase/encoded_gap.py',
 'improvements/extraction/extraction_improvements.py',
 'improvements/root/fast_mask_projection.py',
]
def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--output',type=Path,default=ROOT/'build/dqi.kmb')
 a=p.parse_args();env=dict(os.environ,DQI_WORKSPACE=str(ROOT),PYTHONDONTWRITEBYTECODE='1')
 command=[sys.executable,str(ROOT/'round13/root/build_candidate.py')]
 for patch in PATCHES:command.extend(['--patch',str(ROOT/patch)])
 command.extend(['--output',str(a.output.resolve())])
 subprocess.run(command,env=env,check=True)
if __name__=='__main__':main()
