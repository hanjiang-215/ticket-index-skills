---
id: demo-b2c3
status: closed
type: task
priority: 1
assignee: alice
parent: demo-a1b2
deps: []
links: []
tags: [core]
created: 2026-01-05T10:00:00Z
---
# Choose the storage boundary

## Decision

Execution records live in a single embedded database owned by the scheduler.
Workers never write state directly; they return results to the scheduler.

## Acceptance criteria

- [x] State survives a scheduler restart.
- [x] Workers can be replaced without migrating data.
