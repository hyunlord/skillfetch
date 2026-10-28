#!/bin/sh
# The independent scan-accuracy set (numbers.md §30), scanned once under the code of each rules
# version: v6 (c8cf328), v7 (e5014ad), v8 (e71139e). Each version's src/ is taken from git into
# a temporary folder and put first on PYTHONPATH; results go to
# evals/scan-accuracy/independent/results-vN.json.
#
#   sh scripts/scan_accuracy_versions.sh <set dir> [frozen file] [out dir]
set -eu
SET=${1:?the independent set folder}
ROOT=$(cd "$(dirname "$0")/.." && pwd)
FROZEN=${2:-$ROOT/evals/scan-accuracy/independent/FROZEN.sha256}
OUT=${3:-$ROOT/evals/scan-accuracy/independent}
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
for pair in v6:c8cf328 v7:e5014ad v8:e71139e; do
  v=${pair%%:*}
  c=${pair#*:}
  mkdir -p "$WORK/$v"
  git -C "$ROOT" archive "$c" src | tar -x -C "$WORK/$v"
  PYTHONPATH="$WORK/$v/src" "$ROOT/.venv/bin/python" -c \
    "import skillfetch, sys; sys.exit(0 if skillfetch.__file__.startswith('$WORK') else 1)" \
    || { echo "skillfetch did not load from $WORK/$v/src" >&2; exit 1; }
  PYTHONPATH="$WORK/$v/src" "$ROOT/.venv/bin/python" "$ROOT/scripts/scan_accuracy.py" \
    independent --set "$SET" --rules "$v" --frozen "$FROZEN" --out "$OUT/results-$v.json"
done
