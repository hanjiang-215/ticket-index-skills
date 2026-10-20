---
id: demo-f6a7
status: closed
type: task
priority: 3
assignee: team
deps: []
links: []
tags: [api]
created: 2026-01-04T09:00:00Z
---
# Standardise failure codes

## Decision

Every failure carries a stable code, a retryable flag, and a human message.
Clients must branch on the code, never on the message text.

## Acceptance criteria

- [x] Codes cover validation, dependency, timeout, and internal failures.
- [x] Each code documents whether retrying is safe.
