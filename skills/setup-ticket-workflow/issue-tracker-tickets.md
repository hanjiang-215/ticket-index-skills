# Ticket tracker: Local Markdown

Work for this repo is tracked as Markdown files under `<TICKETS_DIR>/`, one file per
ticket, plus a generated index under `<OUTPUT_DIR>/`. This file is the adapter the
skills read when they are told to "publish to the tracker", "fetch a ticket", or "claim
the next frontier ticket".

## The contract

Every ticket is `<TICKETS_DIR>/<id>.md`. The filename stem must equal the frontmatter
`id` and match `<PREFIX>-[0-9a-z]{4}`.

```markdown
---
id: <PREFIX>-a1b2
status: open              # open | in_progress | closed
type: task                # epic | spec | task | research | prototype | decision
priority: 2               # 0 highest, 4 lowest
assignee: alice           # empty means unclaimed or unowned
parent: <PREFIX>-9z8y     # optional; hierarchy only
deps: [<PREFIX>-5e6f]     # optional; the tickets that block this one
links: [<PREFIX>-7g8h]    # optional; symmetric associations
tags: [map, core]         # "map" marks a decision map
created: 2026-01-01T00:00:00Z
---
# Ticket title

Body...
```

Rules:

- The first `# ` heading is the title; later headings are sections.
- `deps` lists **blockers**: this ticket cannot start until those are `closed`.
- `links` is symmetric association, never hierarchy. Hierarchy comes only from `parent`.
- A tag of `map` (or `wayfinder:map`) marks a decision map. `ticket-index` renders maps
  first and lists them in the module stats.
- This tracker has no labels. When a skill says to apply a triage label, add it as a tag
  instead: `ready-for-agent`, `needs-info`, and so on.
- Unknown statuses are reported as warnings and treated as inactive. Stick to the three.
- Read files with their full body. Never rewrite a ticket owned by someone else; append
  a dated `## Notes` entry instead.

## Operations

If a ticket CLI is installed (for example `fer`), use it: the commands below are the
same operations. Otherwise edit the file directly. Either way, finish by updating the
index (see the last section).

| Operation | How |
| --- | --- |
| Create | Mint an unused id with `python <skill>/scripts/ticket_index.py new-id` (or choose one by the id pattern), write `<TICKETS_DIR>/<new-id>.md` with the frontmatter above, `status: open`, and `created` set to now. Add its `[tickets]` entry to `ticket-index.toml`. |
| Read | Open the file. Resolve references through the index, not by guessing ids. |
| Change status | Edit `status` to `open`, `in_progress`, or `closed`. |
| Claim | Set `assignee` to the driver and `status: in_progress`, as one edit, before any work. |
| Close | Append `## Answer` (or `## Outcome` for implementation tickets), then set `status: closed`. |
| Reopen | Set `status: open` and keep the existing answer; append a dated note saying why. |
| Block | Add the blocker id to the blocked ticket's `deps`. |
| Associate | Add each id to the other's `links`. |
| Comment | Append a dated `## Notes` subsection at the bottom. |

Never keep two copies of the same fact. The ticket body is the only full copy; the index
is a projection and must not be edited by hand.

## Publishing a spec

When a skill says "publish the spec to the issue tracker":

1. Write the spec to `docs/specs/YYYY-MM-DD-<slug>.md`.
2. Create one ticket with `type: spec` (or `epic` when the spec spans several modules),
   a title naming the feature, a body pointing at the spec path, and the tag
   `ready-for-agent`.
3. Leave it `open` and unassigned unless the user names an owner.

`to-tickets` breaks a spec into tickets; each ticket body points back at the spec path.

## Publishing tickets

When a skill says "publish the tickets":

- One file per ticket, never a combined file.
- Ids follow `<PREFIX>-<4 chars>`, generated in dependency order but not otherwise
  meaningful.
- Write the blocking edges into `deps` in a second pass, after every ticket id exists.
- Put the acceptance criteria in the body as task-list items.
- Add one `[tickets]` entry per ticket and choose its **primary module**: the domain
  where the ticket's conclusion lands.
- Apply the tag `ready-for-agent` unless the user says otherwise.

## Frontier query

The frontier is every active (`open` or `in_progress`) ticket whose deps are all
`closed`.

- Fast path: read the **Frontier** and **Blocked** tables in `<OUTPUT_DIR>/INDEX.md`.
- Machine path: run `python <skill>/scripts/ticket_index.py facts` and filter the
  `status`, `parent`, and summary columns.
- Order: priority ascending, then id. An `in_progress` ticket is already claimed; skip it
  unless the user names it.

## Wayfinding operations

Used by `/wayfinder`. A map is a normal ticket with the `map` tag; its decision tickets
are its children.

- **Map**: a ticket with `tags` including `map`, `type: epic`. Its body carries
  `## Destination`, `## Notes`, `## Decisions so far`, `## Not yet specified`, and
  `## Out of scope`.
- **Child ticket**: `parent: <map-id>`, `type` one of `research`, `prototype`,
  `grilling`, or `task`, with `## Question` as its body. Also record the type in `tags`
  as `wayfinder:<type>` so a map can be filtered by decision kind.
- **Blocking**: list blockers in `deps`. There is no native blocking UI; the generated
  index is the visual frontier.
- **Claim**: set `assignee` and `status: in_progress` before any work. An open,
  unassigned child is unclaimed.
- **Resolve**: append `## Answer`, set `status: closed`, then append one line to the
  map's `## Decisions so far` that names the ticket and gists the answer.
- **Fog**: stays in the map's `## Not yet specified` until it can be stated sharply
  enough to become a ticket.
- **Out of scope**: close the ticket and add one line to the map's `## Out of scope`
  naming it and the reason.

## Keeping the index current

After any mutation:

```bash
python <skill>/scripts/ticket_index.py check     # reports missing entries and stale output
python <skill>/scripts/ticket_index.py diff      # review only the hunks that would change
python <skill>/scripts/ticket_index.py render    # write INDEX.md and modules/*.md
python <skill>/scripts/ticket_index.py check     # must exit 0
```

`check` fails when a ticket has no module entry or summary, when a module is unknown, or
when a dependency, link, or parent points at a missing ticket. Fix errors before
rendering; `render` refuses to write while the config has errors.
