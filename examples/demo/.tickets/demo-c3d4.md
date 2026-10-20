---
id: demo-c3d4
status: open
type: task
priority: 2
assignee: bob
parent: demo-a1b2
deps: [demo-b2c3]
links: []
tags: [core]
created: 2026-01-06T09:00:00Z
---
# Persist execution state

Implement the record lifecycle agreed in the storage decision.

## Acceptance criteria

- [ ] A submitted command creates one execution record.
- [ ] Restarting the scheduler keeps every record readable.
- [ ] Duplicate submissions with the same idempotency key return the first result.
