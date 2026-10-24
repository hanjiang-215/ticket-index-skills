# Configuration

The script reads one TOML file. It looks for `ticket-index.toml` at the current directory
and each parent, then falls back to the legacy `docs/tickets/index.toml`. `--config PATH`
overrides the search.

## Full example

```toml
[settings]
title = "Ticket Index"                  # H1 of INDEX.md
tickets_dir = ".tickets"                # directory holding <id>.md
output_dir = "docs/tickets"             # generated index location
id_pattern = "[A-Za-z][A-Za-z0-9]*-[0-9a-z]{4}"
summary_max_chars = 160                 # warning threshold only
placeholder_assignees = ["", "-", "team", "tbd", "todo", "unassigned"]

[[modules]]
id = "core"
title = "Core Platform"
scope = "Runtime, storage, and deployment boundaries"

[[modules]]
id = "api"
title = "Public API"
scope = "Contracts, endpoints, and client compatibility"

[tickets]
"app-1a2b" = { module = "core", summary = "Decide how sessions survive a worker restart" }
"app-3c4d" = { module = ["api", "core"], summary = "Define the public contract and its compatibility rule" }
```

## Settings

| Key | Default | Notes |
| --- | --- | --- |
| `title` | `Ticket Index` | Heading of `INDEX.md` |
| `tickets_dir` | `.tickets` | Relative paths resolve from the repository root |
| `output_dir` | `docs/tickets` | Relative paths resolve from the repository root |
| `id_pattern` | `[A-Za-z][A-Za-z0-9]*-[0-9a-z]{4}` | Python regex; used for filenames and for extracting ids from `parent`, `deps`, `links` |
| `summary_max_chars` | `160` | Longer summaries produce a warning, never an error |
| `placeholder_assignees` | `["", "-", "team", "tbd", "todo", "unassigned"]` | Case-insensitive; matched after trimming |

The root is the directory holding `ticket-index.toml`. For the legacy
`docs/tickets/index.toml`, the root is two levels above `docs/`, and the default
`output_dir` is that same `docs/tickets/` directory.

### Id patterns

The pattern is matched against filenames and used to find ids inside frontmatter values.
Choose a shape that cannot appear by accident in prose:

- Good: `[A-Za-z][A-Za-z0-9]*-[0-9a-z]{4}` → `app-a1b2`, `AI4-9z8y`.
- Risky: `[0-9]+` → ids like `42` appear in ordinary text and would be extracted from
  summaries or URLs.

The prefix may be uppercase; the four-character suffix is conventionally lowercase
letters and digits. `new-id` prints one id that matches the pattern and does not
collide with the existing store; it never writes files, so any scheme the pattern
accepts is valid.

## Modules

Each `[[modules]]` entry requires:

- `id`: lowercase letters, digits, and hyphens, starting with a letter or digit;
- `title`: shown in the overview and as the module page heading;
- `scope`: one line describing what belongs there.

Duplicate ids are an error. A module with no tickets still gets a page; that is useful
while a new domain is being set up.

Module order in the file is the order in the overview table. Put the domains readers
should scan first at the top.

## Ticket entries

Every ticket needs exactly one entry. The key is the ticket id; the value is an inline
table with two fields:

- `module`: a string, or an array of strings. The first is the **primary** module and the
  only place the ticket is expanded. Additional modules list it under cross-module
  membership.
- `summary`: one line, non-empty. Aim for 20–60 characters; the hard warning threshold is
  `summary_max_chars`.

Writing rules for summaries:

- Add information the title does not contain.
- Do not repeat the title, the status, the owner, a date, or a file path.
- For research, name what is being verified and what the result will be used for.
- For maps, name the destination.
- For closed decision tickets, state the scope of the conclusion, not the answer itself.
- Any language is fine; the surrounding scaffolding is English.

## Multi-module tickets

Use an array when one ticket genuinely serves several domains:

```toml
"app-3c4d" = { module = ["api", "core"], summary = "..." }
```

- The ticket is expanded once, under `api`.
- `core` lists it under cross-module membership with a link back to `api`.
- The overview's multi-module table shows the primary module and the others.

Do not add secondary modules to make a module page look fuller. A module page that lists
references it does not own is correct; duplicated rows are not.

## Generated files

`render` writes:

- `<output_dir>/INDEX.md`;
- `<output_dir>/modules/<module-id>.md` for every configured module.

It removes a file in `modules/` only when the file carries the generated marker and its
module is no longer configured. Files without the marker are never touched.

`check` also detects missing and obsolete files. `diff` covers files that would be
written, not files that would be removed; run `render` to remove them.

## Hook configuration

The optional hook (`skills/ticket-index/hooks/ticket-index-sync.py`) finds the same
configuration. Set `TICKET_INDEX_CONFIG` to an absolute path when the working directory
is not inside the repository, for example in a Cursor hook whose cwd differs from the
project root.

The hook ignores events that do not touch the tickets directory, the config file, or a
ticket-CLI mutation command. Failures print to stderr and never block the edit or
command.

## Common configuration errors

| Message | Fix |
| --- | --- |
| `missing module and summary for <id>` | Add the ticket's `[tickets]` entry |
| `<id> uses unknown modules ...` | Add the module to `[[modules]]` or correct the name |
| `<id> has no summary` | Write a one-line summary |
| `<id> is not a ticket file` | Delete the entry or restore the ticket |
| `Duplicate module id` | Keep one definition |
| `Invalid module id` | Use lowercase letters, digits, and hyphens |
| `parent/dependency/link ... does not exist` | Fix the id or create the ticket |
| `stale generated file ...` | Run `render` |
