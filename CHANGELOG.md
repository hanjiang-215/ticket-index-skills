# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-10-20

### Added

- `ticket-index` skill: layered Markdown index generated from ticket frontmatter, with
  `check`, `diff`, `render`, and `facts` commands.
- Multi-module membership, parent-based hierarchy, cross-module relations, frontier,
  blocked, and missing-owner views.
- Optional Cursor auto-sync hook for ticket edits and ticket-CLI mutations.
- `setup-ticket-workflow`, the repo scaffolding skill and local tracker contract.
- Companion skills for planning, splitting, implementing, reviewing, and handing off
  work: `to-spec`, `to-tickets`, `implement`, `implement-spec`, `code-review`, `pr`,
  `wayfinder`, `grilling`, `domain-modeling`, `tdd`, `writing-for-agents`, `handoff`.
- `scripts/install.py` for installing skills into a target repository, with optional hook
  installation.
- `scripts/verify.py`, a stdlib test suite, and a runnable six-ticket demo.
