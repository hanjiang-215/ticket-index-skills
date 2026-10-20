---
name: setup-ticket-workflow
description: "Configure a repository for the ticket workflow: the local Markdown ticket store, its ticket-index configuration, and the domain-doc pointers the other skills read. Run once per repo before /to-spec, /to-tickets, /wayfinder, or /implement-spec."
disable-model-invocation: true
metadata:
  credits:
    based_on:
      skill: setup-matt-pocock-skills
      author: Matt Pocock
      url: "https://github.com/mattpocock/skills/blob/main/skills/engineering/setup-matt-pocock-skills/SKILL.md"
---

# Setup Ticket Workflow

Scaffold the per-repo configuration that the bundled skills assume:

- **Ticket store**: `.tickets/<id>.md` plus `ticket-index.toml`
- **Tracker operations**: `docs/agents/issue-tracker.md`, the file `to-spec`, `to-tickets`,
  `wayfinder`, `implement`, and `implement-spec` read before touching tickets
- **Domain docs**: `docs/agents/domain.md`, the pointer to `GLOSSARY.md` and ADRs
- **Agent pointer**: an `## Agent skills` block in `AGENTS.md` or `CLAUDE.md`

This is a prompt-driven skill, not a deterministic script. Explore, present findings,
confirm with the user, then write.

## 1. Explore

Read the repo before proposing anything:

- `.tickets/` and existing ticket files: is there already a ticket store?
- `ticket-index.toml` at the root, or the legacy `docs/tickets/index.toml`
- `docs/tickets/INDEX.md`: does a generated index already exist?
- `docs/agents/`: did a previous setup already run?
- `GLOSSARY.md`, `GLOSSARY-MAP.md`, `docs/adr/`: which domain docs exist?
- `AGENTS.md` and `CLAUDE.md`: which one exists, and does it already have an
  `## Agent skills` section?
- Top-level source directories: candidate module boundaries
- Is the `ticket-index` skill installed? Find its `scripts/ticket_index.py`; every
  command below needs the real path.

If a ticket store already exists, do not replace it. Adopt it: keep the files, add the
missing index entries, and only write the docs that are absent.

## 2. Confirm the layout

Ask in one round. Lead each question with the recommended answer so the user can accept
it in a word.

**Ticket ids.** Propose a short prefix and the standard four-character suffix, for
example `app-a1b2`. The regex is
`<prefix>-[0-9a-z]{4}`; the prefix must start with a letter.

**Directories.** Recommend `.tickets/` for the files and `docs/tickets/` for the
generated index. Both are configurable.

**Modules.** Look at the repo and propose a first module list: one module per domain
where a ticket's conclusion lands. Use source areas, deployment boundaries, or product
surfaces, not team names or task types. Two to six modules is normal; a brand-new repo
can start with one. Every module needs an `id` (lowercase letters, digits, hyphens), a
`title`, and a one-line `scope`.

Present the proposed `[[modules]]` table and the prefix. Let the user edit it before
writing.

## 3. Write

### `ticket-index.toml`

Create it at the repository root when absent. Start with no tickets:

```toml
[settings]
title = "Ticket Index"
tickets_dir = ".tickets"
output_dir = "docs/tickets"
id_pattern = "<prefix>-[0-9a-z]{4}"
summary_max_chars = 160
placeholder_assignees = ["", "-", "team", "tbd", "todo", "unassigned"]

[[modules]]
id = "core"
title = "Core Platform"
scope = "Runtime, storage, and deployment boundaries"

[tickets]
```

If the user named different modules, use theirs instead of `core`.

### `.tickets/README.md`

Create it so the directory is tracked and the convention is visible. The index script
ignores a file named `readme.md`:

```markdown
# Tickets

One file per ticket: `<id>.md`, with YAML frontmatter. See
[`docs/agents/issue-tracker.md`](../docs/agents/issue-tracker.md) for the contract and
operations.
```

### `docs/agents/issue-tracker.md`

Write it from [issue-tracker-tickets.md](./issue-tracker-tickets.md), replacing every
`<PREFIX>` with the confirmed prefix and every `<TICKETS_DIR>` / `<OUTPUT_DIR>` with the
confirmed paths. Keep the operations section: it is the adapter the other skills rely
on.

### `docs/agents/domain.md`

Copy [domain.md](./domain.md) unchanged unless the repo is a monorepo. For a monorepo,
keep the multi-context layout described inside it.

### The agent pointer

Pick the file to edit:

- If `CLAUDE.md` exists, edit it.
- Else if `AGENTS.md` exists, edit it.
- If neither exists, ask the user which one to create.

Never create a second of the two. If an `## Agent skills` section already exists, update
it in place; do not overwrite the surrounding sections. Replace the directory
placeholders with the confirmed paths before writing.

```markdown
## Agent skills

### Tickets

Work is tracked as Markdown tickets under `<TICKETS_DIR>/`; the index lives in
`<OUTPUT_DIR>/`. Read the index before opening tickets. See
`docs/agents/issue-tracker.md`.

### Domain docs

Single-context: `GLOSSARY.md` and `docs/adr/`. See `docs/agents/domain.md`.
```

## 4. Render and verify

Run the index script from the repository root, using the path where the skill is
installed:

```bash
python .cursor/skills/ticket-index/scripts/ticket_index.py render
python .cursor/skills/ticket-index/scripts/ticket_index.py check
```

Exit code `0` and `OK: ...` mean the scaffolding is consistent. An empty ticket store is
valid: the overview and one file per module are generated, all counts zero.

Then tell the user:

- which files were written;
- that new tickets need one `[tickets]` entry plus a `render`;
- that the optional auto-sync hook lives in the ticket-index skill folder
  (`hooks/hooks.json.example`) if they want generated files kept current automatically.
