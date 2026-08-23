import argparse
from src.pipeline import run as run_upsc
from src.sarkariresult.run import run as run_sarkari

p=argparse.ArgumentParser(description="UPSC Deep Recruitment Agent + SarkariResult discovery")
p.add_argument("--source",choices=["upsc","sarkariresult","both"],default="upsc")
p.add_argument("--advt",choices=["09","51"],default="09")
p.add_argument("--deep-sarkariresult",action="store_true",help="Follow retained SarkariResult detail pages and inspect candidate official links")
a=p.parse_args()
if a.source in ("upsc","both"):
    run_upsc(a.advt)
if a.source in ("sarkariresult","both"):
    run_sarkari(deep=a.deep_sarkariresult)
