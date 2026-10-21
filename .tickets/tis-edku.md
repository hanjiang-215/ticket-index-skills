---
id: tis-edku
status: closed
deps: []
links: []
created: 2026-10-21T03:14:55Z
type: task
priority: 1
assignee: 寒江
---
# Make skill installation transactional

Validate hook configuration before modifying skills and restore previous files if install or hook merge fails.

## Acceptance Criteria

Malformed hook config or copy failures do not leave partial skill installs or modify pre-existing files.


## Notes

**2026-10-21T03:31:32Z**

Installer now stages copies and hook updates before commit, validates hook JSON before copying, and rolls back replacements on commit errors. Installer regression tests and python scripts/verify.py pass.
