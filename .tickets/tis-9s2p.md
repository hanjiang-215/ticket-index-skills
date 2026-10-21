---
id: tis-9s2p
status: closed
deps: []
links: []
created: 2026-10-21T03:14:55Z
type: task
priority: 2
assignee: 寒江
---
# Serialize concurrent index renders

Prevent concurrent render processes from interleaving writes and stale module cleanup.

## Acceptance Criteria

Two simultaneous render processes complete successfully and leave a check-clean index.


## Notes

**2026-10-21T03:31:32Z**

Added process and thread render locking; concurrent process regression test and full python scripts/verify.py pass.
