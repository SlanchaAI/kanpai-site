#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export TMPDIR="$PWD/.test-output/tmp"
if [[ -d /mnt/models/fleet-offload/tmp ]]; then
  export TMPDIR=/mnt/models/fleet-offload/tmp
fi
mkdir -p "$TMPDIR"
python3 --version
bash --version | head -n 1
export CHROME="${CHROME:-$(command -v google-chrome || command -v chromium)}"
"$CHROME" --version
bash -n tests/verify_whole_tests.sh
python3 tests/whole_tests.py
