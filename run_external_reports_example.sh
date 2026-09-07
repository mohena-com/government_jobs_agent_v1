#!/bin/bash
set -e

REPORTS_DIR="${1:?Usage: ./run_external_reports_example.sh /path/to/external/job_reports}"

exec ./run.sh --reports-dir "$REPORTS_DIR"
