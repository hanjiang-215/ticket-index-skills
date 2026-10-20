---
id: demo-a1b2
status: open
type: epic
priority: 1
assignee: alice
deps: []
links: []
tags: [map, core]
created: 2026-01-05T09:00:00Z
---
# First release decision map

Decide the smallest path from a submitted command to a visible execution
result. This map owns the decisions; the child tickets own the delivery slices.

## Decisions so far

- One process may own scheduling; workers stay short-lived.
- Execution state must survive a scheduler restart.

## Out of scope

- Multi-region deployment.
- Billing.
