# Whole-repository checks

Run `bash tests/verify_whole_tests.sh` with Python 3, Bash, Git and Chrome or Chromium
(`CHROME` may select the binary). No package installation or external test data.
The caller sets scratch/browser profiles under `.test-output/tmp`, or
`/mnt/models/fleet-offload/tmp` on fleet hosts. Chrome singleton sockets exceed
Unix path limits under the resolved fleet worktree path; use the short scratch
root there (failure: Chrome exits -6 with `Socket path too long`).

`whole_tests.py:INVENTORY` maps every tracked file individually. Unknown additions
of any language and stale entries fail; executable additions need behavior tests
and coverage integration before classification. There are no application executable
modules: both HTML files are declarative pages, CSS is declarative styling, and
CNAME is hosting configuration. No vendor/generated application files are excluded.

The real browser loads both pages at mobile and desktop sizes, checking arm-specific
content, protocol payload, required fields individually, invalid email, consent,
valid synthetic submission, serialized form values, stylesheet loading, responsive
layout, overflow and focus. Submission is intercepted locally; the `/interest`
backend is outside this repository and is not claimed tested.

Python stdlib trace enumerates every Python module independently of imports and
fails on entirely unexercised modules. Its line report includes missing lines;
coverage is not claimed to be 100%. The shell entrypoint executes in local proof
and CI, checks syntax, and propagates failures via `set -euo pipefail`. CI YAML is
configuration exercised by the PR run. No JavaScript ships in the application;
browser assertions are injected only by the loopback fixture server.

CI uploads inventory, browser/static coverage, Python line reports and summary,
even on failure. Coverage is distinct from executable-code coverage for HTML/CSS:
all three static assets are loaded and their behavior checked in each scenario.

Browser result parsing must inspect the rendered `pre#result` node. Searching dump
text for a PASS literal can match unexecuted injected script source; regression
checks reject script literals, missing result IDs and explicit failures.
