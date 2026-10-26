#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONDONTWRITEBYTECODE=1
printf 'Audit date (UTC): %s\n' "$(date -u +%F)"
bash --version | head -n 1
python3 --version
# This repository has no package ecosystem. The allowlist fails closed when
# any manifest, lockfile, vendored library, workspace or new source is added.
python3 -B -m unittest discover -s tests -p 'test_*.py' -v
