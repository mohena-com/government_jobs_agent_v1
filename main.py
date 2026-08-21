import argparse
from src.pipeline import run
p=argparse.ArgumentParser();p.add_argument('--report-only',action='store_true');a=p.parse_args();run(a.report_only)
