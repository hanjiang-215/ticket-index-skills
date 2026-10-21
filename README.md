# Ticket Index Skills

English | [简体中文](README.zh-CN.md)

**Author / 作者:** hanjiang-215

A ticket-driven workflow for AI coding agents working in large repositories.

The centrepiece is **ticket-index**: a skill that maintains a generated, three-level
index over Markdown tickets. It lets an agent answer "what work exists, who owns it,
and what can start now" without opening every ticket. The other skills help create,
split, sequence, implement, and review that work.

## 中文简介

Ticket Index Skills 为大型代码仓库中的 AI 编程代理提供基于 Markdown 任务票据的工作流。核心技能 `ticket-index` 会从票据生成确定性的三级索引，帮助代理快速找到现有工作、负责人和当前可开始的任务，而无需逐一打开所有票据。

项目仅依赖 Python 3.11+ 标准库，并提供安装脚本、可选的 Cursor 自动同步钩子和完整示例。完整中文说明见 [README.zh-CN.md](README.zh-CN.md)。

The core is Markdown files and one dependency-free Python script. The installer and the
optional hook are standard-library Python as well.

- Works with any agent that reads `SKILL.md` skills (Cursor, Claude Code, Codex, and
  others following the same convention).
- Scales from a handful of tickets to several hundred.
- Keeps facts in one place: ticket frontmatter is the source of truth, the index is a
  deterministic projection, and `check` fails when they drift.

## The problem

A repo with a hundred tickets is expensive for an agent to navigate. Reading the
backlog to find one executable item burns context before any work starts, and a
hand-maintained summary is stale within a day.

Ticket Index splits the job in three:

```text
docs/tickets/INDEX.md          overview: stats, modules, frontier, blocked, relations
docs/tickets/modules/<id>.md   one page per module, tickets arranged by parent
.tickets/<id>.md               the ticket itself: the only full copy
```

A reader locates a candidate in the overview, narrows it in one module page, then opens
exactly one ticket. Status, type, owner, priority, dependencies, hierarchy, and counts
are read from ticket frontmatter. Humans write only two judgements per ticket in
`ticket-index.toml`: which module it belongs to, and a one-line summary.

Because the output is deterministic, `diff` shows exactly what a render would change,
`check` detects stale or hand-edited output, and generated files cannot silently drift.

## Quickstart

Requirements: Python 3.11 or newer (for `tomllib`). No packages to install.

```bash
git clone <repo-url> ticket-index-skills
cd ticket-index-skills

# Copy the skills into your repository and install the Cursor auto-sync hook
python scripts/install.py --target /path/to/your/repo --install-hooks
```

`--install-hooks` is Cursor-only. For Claude Code, use `--agent claude`; for any other
agent, point `--skills-dir` at the directory it reads. Omit the hook flag to skip it.

Then, in the target repository:

1. Run `/setup-ticket-workflow`. It writes `ticket-index.toml`, `.tickets/README.md`,
   `docs/agents/issue-tracker.md`, and `docs/agents/domain.md`, after confirming the
   ticket id prefix and module list with you.
2. Add tickets under `.tickets/<id>.md` with the frontmatter contract.
3. Add one `[tickets]` entry per ticket to `ticket-index.toml`.
4. Render and verify:

```bash
python .cursor/skills/ticket-index/scripts/ticket_index.py render
python .cursor/skills/ticket-index/scripts/ticket_index.py check
```

`check` exits `0` with `OK: ...` when the index matches the tickets.

See [`examples/demo`](examples/demo) for a complete six-ticket project with its
generated index committed. Run the demo end to end from that directory:

```bash
cd examples/demo
python ../../skills/ticket-index/scripts/ticket_index.py check
```

## The skills

Three layers: navigation (the core), planning and the ticket lifecycle, and the
disciplines that make each step reliable.

| Skill | Layer | What it does |
| --- | --- | --- |
| **ticket-index** | Core | Generates and validates the layered index over `.tickets/*.md` |
| setup-ticket-workflow | Lifecycle | Configures a repo once: ticket store, index config, domain docs |
| to-spec | Lifecycle | Creates a spec in `docs/specs/` and its tracking ticket |
| to-tickets | Lifecycle | Breaks a spec into tracer-bullet tickets with blocking edges |
| implement-spec | Lifecycle | Works a whole spec as a task graph on one integration branch |
| implement | Lifecycle | Implements one ticket or a small piece of work, driving TDD |
| code-review | Lifecycle | Reviews a diff along two axes: repo standards and the originating spec |
| pr | Lifecycle | Writes a PR body with evidence and a merge-danger call |
| wayfinder | Planning | Maps a large effort as decision tickets and resolves them one at a time |
| grilling | Planning | Interviews the user until every branch of a design tree is settled |
| prototype | Planning | Builds a disposable logic or UI prototype to settle a design question |
| domain-modeling | Discipline | Sharpens `GLOSSARY.md` and ADRs while designing |
| codebase-design | Discipline | Provides shared vocabulary for module depth, interfaces, seams, and adapters |
| tdd | Discipline | Red-green-refactor loop with guidance on tests worth keeping |
| diagnosing-bugs | Discipline | Builds a tight feedback loop to diagnose hard bugs and regressions |
| writing-for-agents | Discipline | Writes skills, `AGENTS.md`, and docs that agents navigate predictably |
| handoff | Discipline | Compacts a session into a handoff document for the next agent |

### How they compose

```text
grilling ──┐
           ├─> to-spec ──> to-tickets ──> ticket-index ──> implement-spec ──> code-review ──> pr
wayfinder ─┘        (spec)      (tickets)      (navigation)      (execution)       (review)
                                                        │
                                                        └─> implement (single ticket)
```

`wayfinder` and `to-spec` are alternative entry points: use `wayfinder` when the way to
the destination is still foggy, and `to-spec` when the conversation already settled the
design. Both publish to the same ticket store. `to-tickets` gives every ticket its
blocking edges, `ticket-index` renders the frontier, and `implement-spec` consumes that
frontier one ready ticket at a time.

Use `prototype` before committing to a design when a small interactive logic demo or UI
variation can answer an open question. Record the validated decision and a pointer to the
throwaway prototype on its ticket; keep prototype-only code out of the production branch.

The disciplines are optional but recommended: `grilling` before committing to a design,
`codebase-design` when the shape of an interface or seam is in question, `tdd` inside each
ticket, `diagnosing-bugs` for hard failures and regressions, `domain-modeling` when
terminology settles, `code-review` before the PR, and `writing-for-agents` when you adapt
any of these skills to your repo.

### What is intentionally not bundled

- **Triage**: the upstream triage skill assumes GitHub or GitLab labels and a role state
  machine. This kit uses three statuses on local files, so triage would add a second,
  conflicting vocabulary.
- **Issue-tracker sync**: the index reads local files only. If your source of truth is a
  remote tracker, export tickets to `.tickets/<id>.md` first; the script stays out of
  network calls by design.

## Generated-index conflicts

Ticket files and `ticket-index.toml` are the source of truth; `docs/tickets/**` is
regenerated output. Before opening a PR, rebase on the latest target branch. If the rebase
conflicts, resolve `.tickets/*.md` and `ticket-index.toml` first; never hand-merge the
generated index. Then run `render` and `check`, stage the merged sources and regenerated
files, and continue the rebase. After the rebase finishes, run `render` and `check` again.

```bash
python .cursor/skills/ticket-index/scripts/ticket_index.py render
python .cursor/skills/ticket-index/scripts/ticket_index.py check
```

## Command reference

Run from the repository root; the script searches upward for `ticket-index.toml` and
also accepts the legacy `docs/tickets/index.toml`.

| Command | Effect |
| --- | --- |
| `check` | Validate config, references, and generated files. Exit `1` on problems |
| `diff` | Print unified diffs for files that would change. Writes nothing |
| `render` | Write `INDEX.md` and `modules/*.md`, remove obsolete module files |
| `facts` | Print a compact tab-separated fact sheet for a human decision |

Pass `--config PATH` to any command to use a specific config file instead of searching
upward.

## Repository layout

```text
skills/
  ticket-index/          the core skill, its script, and the optional hook
  setup-ticket-workflow/ repo scaffolding, with the local tracker contract
  ...                    other companion skills
examples/demo/           a runnable six-ticket project and its generated index
.tickets/                this repository's own tickets
docs/                    concepts and reference, plus the index generated from .tickets/
scripts/                 install.py and verify.py
tests/                   stdlib unittest suite for the index script, hook, and installer
```

## Documentation

- [Dependencies](docs/DEPENDENCIES.md): supported Python version, dependency inventory, and verification commands.
- [Concepts](docs/concepts.md): why the index is derived, module ownership, determinism,
  maps.
- [Ticket contract](docs/ticket-contract.md): frontmatter fields, status semantics,
  validation rules, migration from another tracker.
- [Configuration](docs/configuration.md): every setting, module and entry rules, legacy
  layout, common errors.
- [Workflow](docs/workflow.md): the end-to-end sequence, artifacts, and multi-agent rules.

## Development

```bash
python scripts/verify.py      # unit tests + demo check/render/check/diff
python -m unittest discover -s tests -v
```

`verify.py` also asserts that rendering the demo twice is a no-op and that no generated
file is left stale. The unit suite runs `check` against this repository's own index as
well, so editing a ticket or `ticket-index.toml` without re-rendering fails CI.

## Adapting the kit

- **Different agent directory**: `install.py --skills-dir .claude/skills`.
- **Different ticket id style**: change `id_pattern` in `ticket-index.toml`; the script
  only requires that the filename stem matches the frontmatter `id`.
- **Different document language**: generated scaffolding is English, but summaries and
  ticket bodies may be written in any language.
- **No auto-sync hook**: the hook is a safety net. `diff` and `check` remain the
  authoritative workflow.

## License

MIT. See [LICENSE](LICENSE).

The bundled `codebase-design`, `diagnosing-bugs`, and `prototype` skills are adapted from
Matt Pocock's MIT-licensed [skills](https://github.com/mattpocock/skills), pinned to
commit `5beb35b040e3de97e54fa9e386d7e42d15c295c2`. The `pr` skill also credits Dex
Horthy's `show-me` skill from HumanLayer. See [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md)
for source paths and license notices, and [CONTRIBUTING.md](CONTRIBUTING.md) for how to
propose changes.
