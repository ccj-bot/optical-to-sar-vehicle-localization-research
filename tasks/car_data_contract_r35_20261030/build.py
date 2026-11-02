"""Build an independently checked release in a new directory."""
import argparse,sys
from pathlib import Path
import normalize,enhance,verify,document,seal

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    out=args.output.resolve();expected=(normalize.ROOT/'output').resolve()
    if not out.is_relative_to(expected):raise ValueError('Use a dedicated workspace/output subdirectory')
    if out.exists():raise FileExistsError('Use a new output directory; existing releases are not overwritten')
    normalize.OUT=out
    normalize.main();enhance.main(out);verify.main(out);document.main(out);seal.main(out)
if __name__=='__main__':main()
