#!/usr/bin/env python3
"""Read-only package, lineage and ordering check before external app shutdown."""
import argparse
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/p) for p in ('runtime','diagnostic','scripts','analysis','slo')]
import local_supplement


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--application',choices=['Go','NGINX'],required=True)
    parser.add_argument('--amendment-accepted',action='store_true')
    parser.add_argument('--allocation-confirmed',action='store_true')
    args=parser.parse_args()
    local_supplement.prelaunch(ROOT,args.application,args.amendment_accepted,args.allocation_confirmed)
    print('Supplement source, original evidence and next allocation verify. External runtime qualification remains pending.')
