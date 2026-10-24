# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- The installer now configures conflict-free merging of generated index files:
  it adds `docs/tickets/** merge=ours` to the repository's `.gitattributes` and
  registers the `ours` merge driver in the local git config. During a merge or rebase,
  git keeps the branch-local index, so parallel branches no longer conflict on
  `docs/tickets/**`; the integrator runs `render` and `check` once to fold both sides in.
- `ticket_index.py new-id`: prints one ticket id that matches the configured pattern and
  is not already used in the ticket store. The coordination guard for parallel ticket
  creation: two sessions can no longer silently pick the same filename.
- `install.py --install-git-hooks`: writes `post-merge` and `post-checkout` git hooks
  that re-render the index after every merge and branch switch, keeping the frontier
  fresh as other developers' work lands. Installer hooks never overwrite an existing
  user hook and never block the git operation.
- Unit tests covering the installer's merge-driver setup and git-hook installation
  (gitattributes rule, driver registration, idempotency, configured output dir, worktree
  `gitdir:` pointers, user-hook preservation), and tests for `new-id`.
- Documented scale: independent benchmark shows `render` and `check` complete in about
  one second on a 2,000-ticket, 10-module store.

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
