#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
node --version
npm --version
npm ls --depth=0
"${SHELLCHECK:-shellcheck}" --version
bash -n tests/verify_whole_lint.sh
npm run lint
npm run typecheck
