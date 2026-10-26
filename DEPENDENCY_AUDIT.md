# Dependency audit — 2026-10-26

The complete repository is a static site: `index.html`, `arm_risk.html`,
`assets/venture-page-v1.css`, and `CNAME`. Both pages load only the first-party
stylesheet and an empty data favicon. CSS uses system fonts, with no imports,
URLs, bundled libraries, or external fonts. No JavaScript executes.

There are no package manifests, lockfiles, workspaces, production dependencies,
development dependencies, vendored packages, or existing test/build suites.
Thus npm audit, pip-audit, cargo audit, and govulncheck are not applicable.
There are no package versions to compare against upstream releases or query for
advisories. No advisory suppressions or version holds exist.

The new verifier uses only Bash and Python's standard library. CI uses the
GitHub-hosted Ubuntu runner's Bash, Python, and GitHub CLI; it downloads the
exact commit through GitHub's API, without third-party actions or package
installation. Runner tools are platform-managed, not repository dependencies;
versions are printed on every run. Platform/runtime vulnerabilities remain
outside this package audit's coverage.

`bash tests/verify_whole_deps.sh` inventories all files, including hidden and
nested files, rejects any unreviewed addition (including manifests/lockfiles),
parses both HTML pages to verify their asset and form contracts, checks the
fingerprint of the reviewed CSS, and actually serves both arms and the CSS over
loopback HTTP. It never submits the form or contacts the deployed site.
Coverage is the complete static asset set, not browser rendering, the externally
implemented `/interest` endpoint, or a Python line-coverage percentage.

When adding an ecosystem, replace the zero-dependency inventory gate with actual
upstream version checks and its full audit including development dependencies;
run its entire suite and document exact advisory/version holds with rationale,
risk, and mitigation. Do not merely add a manifest to the allowlist.
