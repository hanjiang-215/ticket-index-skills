# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-10-21

### Added

- `prototype`, `codebase-design`, and `diagnosing-bugs` companion skills, adapted from
  Matt Pocock's MIT-licensed set, with attribution in `THIRD-PARTY-NOTICES.md`.
- `README.zh-CN.md` and `docs/DEPENDENCIES.md`, both linked from the English README.
- A cross-process and cross-thread lock around `render`, so concurrent renders cannot
  interleave writes or stale module cleanup.
- Cached module memberships and sorted ticket order, so large module pages render each
  ticket's membership once instead of rescanning the whole store.
- Guidance on rebasing when the generated index conflicts.

### Changed

- `scripts/install.py` stages every skill and the hook file first, then commits them,
  restoring the previous tree if any step fails.

### Fixed

- The auto-sync hook now compares resolved paths, so editing `ticket-index.toml`
  triggers a render when the config path passes through a symlink or a short name
  (macOS and Windows temporary directories).

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
