# Ticket contract

Ticket Index reads Markdown files with YAML frontmatter. It does not write them. Any
tool or editor that produces this shape works; the kit's `setup-ticket-workflow` skill
writes the operations down for agents.

## Location and identity

- One file per ticket: `<tickets_dir>/<id>.md`. Default `tickets_dir` is `.tickets/`.
- The filename stem must equal the frontmatter `id`.
- The id must match `settings.id_pattern`, default `[A-Za-z][A-Za-z0-9]*-[0-9a-z]{4}`.
  A familiar shape is `app-a1b2`.
- A file named `README.md` is ignored. Any other file whose stem does not match the id
  pattern is skipped with a warning.

Ids are stable identifiers. Choose them once; renaming an id means updating every
reference in `parent`, `deps`, and `links`, plus the configuration entry.

## Frontmatter fields

| Field | Type | Default | Meaning |
| --- | --- | --- | --- |
| `id` | string | filename stem | Must match the filename and `id_pattern` |
| `status` | `open` \| `in_progress` \| `closed` | `open` | Unknown values warn and count as inactive |
| `type` | string | `task` | Free-form; common values are `epic`, `spec`, `task`, `research`, `prototype` |
| `priority` | integer `0`–`4` | `2` | `0` is highest; used for ordering |
| `assignee` | string | empty | The person responsible; placeholders count as missing |
| `parent` | ticket id | none | Hierarchy only; the ticket renders under its parent in the same module |
| `deps` | list of ids | empty | Blockers; the ticket is blocked while any dep is not `closed` |
| `links` | list of ids | empty | Symmetric associations, not hierarchy |
| `tags` | list of strings | empty | `map` (or `wayfinder:map`) marks a decision map |
| `created` | ISO timestamp | empty | Informational; not rendered |

The parser is deliberately small: it reads one `key: value` per line inside the first
`---` block, strips surrounding quotes, and extracts ids with the configured pattern.
Nested YAML structures are not supported and not needed.

## Title

The first `# ` heading in the body is the title. Later headings are sections and may be
used freely (`## Decision`, `## Acceptance criteria`, `## Answer`, `## Notes`).

If no `# ` heading exists, the filename stem is used as the title. That is a signal the
ticket is malformed, not a supported style.

## Status semantics

| Status | Meaning | Active? |
| --- | --- | --- |
| `open` | Ready to start, subject to `deps` | Yes |
| `in_progress` | Claimed and being worked on | Yes |
| `closed` | Accepted; for decisions, the answer is in the body | No |

"Active" means `open` or `in_progress`. Frontier and blocked lists contain only active
tickets. A dependency counts as satisfied only when its status is exactly `closed`;
unknown statuses are warnings and are treated as inactive for statistics but do not
satisfy dependencies.

## Parent, deps, links

These three fields are easy to confuse, and the index uses each for exactly one job:

- `parent` builds the tree. A ticket appears under its parent only when both are in the
  same primary module. A cross-module parent is shown as a pointer, and the ticket
  becomes a root in its own module.
- `deps` blocks. The frontier is computed from it, and only unresolved deps appear in
  ticket rows and the blocked table.
- `links` associates. Cross-module links appear once in the overview; same-module links
  are not rendered because the module page already contains both rows.

Do not use `links` to express hierarchy or blocking. The index will render it as an
association, and the frontier will be wrong.

## Maps

A ticket with `tags: [map]` is a decision map. The index:

- sorts it before other tickets in its module;
- counts it in the module's `Maps` column;
- exposes its children through the ordinary `parent` hierarchy.

The map body conventionally holds `## Destination`, `## Notes`, `## Decisions so far`,
`## Not yet specified`, and `## Out of scope`. The `wayfinder` skill maintains those
sections; the index only needs the `map` tag.

## Example ticket

```markdown
---
id: app-c3d4
status: open
type: task
priority: 1
assignee: bob
parent: app-a1b2
deps: [app-b2c3]
links: [app-e5f6]
tags: [core]
created: 2026-01-06T09:00:00Z
---
# Persist execution state

Implement the record lifecycle agreed in the storage decision.

## Acceptance criteria

- [ ] A submitted command creates one execution record.
- [ ] Restarting the scheduler keeps every record readable.
```

## What `check` validates

Errors (exit `1`):

- the tickets directory is missing;
- a frontmatter `id` differs from its filename;
- a module id is malformed, duplicated, or missing a title;
- a configuration entry names a non-existent ticket, has no module, repeats a module, or
  names an unknown module;
- a configuration entry has an empty summary;
- a ticket has no configuration entry;
- `parent`, `deps`, or `links` reference a missing ticket;
- a generated file is missing, stale, or obsolete.

Warnings (exit `0`):

- a non-ticket file was skipped;
- a ticket has an unknown status;
- a summary exceeds `summary_max_chars`;
- a placeholder assignee is active (also surfaced in the overview's missing-owner table).

## Migrating from another tracker

The script only reads files, so any tracker can feed it through an export step:

1. Export each issue to `.tickets/<id>.md`.
2. Map native fields: state to `status`, labels to `tags`, assignee to `assignee`,
   parent/sub-issue to `parent`, blocking links to `deps`, related links to `links`.
3. Add one `[tickets]` entry per exported ticket with a module and a summary.
4. Run `check`.

Keep the export one-way or scripted. Hand-editing both the remote tracker and the local
files reintroduces the drift this design removes.
