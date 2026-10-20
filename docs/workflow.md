# Workflow

The kit covers one loop: decide, specify, split, navigate, implement, review, merge.
Every stage writes Markdown, so any stage can be resumed by a fresh agent session.

## Stage 0: install and configure once

```bash
python scripts/install.py --target /path/to/repo
```

Then run `/setup-ticket-workflow` in the target repo. It confirms the id prefix and
module list, writes `ticket-index.toml` and `.tickets/README.md`, and writes the tracker
and domain pointers that the other skills read:

```text
docs/agents/issue-tracker.md   how to create, read, claim, block, and close tickets
docs/agents/domain.md          where GLOSSARY.md and ADRs live
```

The setup is a one-time cost per repository. Re-run it only to add modules or change the
ticket layout.

## Stage 1: decide what the work is

Two entry points, chosen by how clear the destination is.

**Clear enough to discuss directly**: `/grilling`. The skill interviews you about a plan
or design, branch by branch, until every decision that affects the work is settled. Use
`/domain-modeling` alongside it when new terms or decisions deserve a glossary entry or
an ADR.

**Too large or too foggy for one session**: `/wayfinder`. It names the destination, maps
the known decisions as child tickets under a map ticket, and resolves them one per
session. `ticket-index` renders the map and its children like any other ticket, so the
frontier is visible after every resolution.

Both paths end with decisions recorded in tickets, not in chat history.

## Stage 2: record a spec

`/to-spec` synthesises the current conversation into a spec: problem, solution, user
stories, implementation decisions, testing decisions, out of scope. It publishes the
spec to `docs/specs/` and creates a tracking ticket tagged `ready-for-agent`.

No interview happens here. If the conversation is not settled, go back to Stage 1.

## Stage 3: cut the spec into tickets

`/to-tickets` breaks the spec into **tracer bullets**: narrow but complete vertical
slices, each demoable on its own and sized for one fresh context. Each ticket declares
its blocking edges.

The skill presents the breakdown for approval before publishing. Tickets land in
`.tickets/<id>.md` with `deps` written in a second pass, after every id exists.

The result is a **task graph**, not a list. A ticket whose blockers are all closed is
ready; everything else is blocked.

## Stage 4: navigate the graph

After publishing or changing tickets:

```bash
python .cursor/skills/ticket-index/scripts/ticket_index.py check
python .cursor/skills/ticket-index/scripts/ticket_index.py diff
python .cursor/skills/ticket-index/scripts/ticket_index.py render
python .cursor/skills/ticket-index/scripts/ticket_index.py check
```

For a new ticket, add its `[tickets]` entry to `ticket-index.toml` first. `check` names
every missing entry, unknown module, and broken reference.

The generated overview answers the questions an agent asks at the start of a session:

- **Frontier**: what can start now.
- **Blocked**: what cannot, and by which ticket.
- **Missing owners**: what has no real owner.
- **Modules**: where a domain's work lives.
- **Cross-module relations**: what a change in one module will touch elsewhere.

Read the overview, open one module page if needed, then one ticket. Do not read the whole
backlog.

## Stage 5: implement

**One ticket**: `/implement`. It fetches the ticket, states its title, drives `/tdd` at
pre-agreed seams, then calls `/code-review`.

**A whole spec**: `/implement-spec`. It treats the tickets as a task graph, starts
implementer subagents on the ready frontier (each in its own worktree), merges completed
work onto one integration branch, and repeats as the frontier opens. It finishes with one
`/code-review` pass on the integration branch.

Concurrency rule: claim a ticket by setting `assignee` and `status: in_progress` before
starting. An open, unassigned ticket is unclaimed and may be picked by another session.

## Stage 6: review

`/code-review` runs two parallel reviews of the diff since a fixed point:

- **Standards**: does the code follow the repo's documented standards?
- **Spec**: does it faithfully implement the originating ticket or spec?

Findings are reported side by side so a standards fix does not hide a spec gap.

## Stage 7: merge request

`/pr` writes the body: a summary built from the smallest visual that makes the change
clear, before/after evidence, and a merge-danger call (one-way or two-way door, plus
blast radius).

Then close the ticket: append `## Outcome` with the verification evidence and set
`status: closed`. Re-render the index so the frontier reflects the closure.

## Anytime: hand off

`/handoff` compacts the session into a temporary document for the next agent, pointing at
specs, tickets, and commits instead of restating them. Useful when a ticket spans several
sessions or a context window is about to be exhausted.

`/writing-for-agents` is for maintaining the kit itself: writing a new skill, tightening
a description, or adding pointer docs to `AGENTS.md`.

## Artifacts

| Artifact | Owner | Mutability |
| --- | --- | --- |
| `.tickets/<id>.md` | ticket author and assignee | source of truth |
| `ticket-index.toml` | maintainers | human-owned config |
| `docs/tickets/INDEX.md` | script | generated, never hand-edited |
| `docs/tickets/modules/<id>.md` | script | generated, never hand-edited |
| `docs/specs/<date>-<slug>.md` | `to-spec` | source of truth |
| `docs/agents/issue-tracker.md` | `setup-ticket-workflow` | editable adapter |
| `docs/agents/domain.md` | `setup-ticket-workflow` | editable adapter |
| `GLOSSARY.md`, `docs/adr/` | `domain-modeling` | source of truth |

## Multi-agent rules

- One ticket, one claim. The claim is `assignee` plus `in_progress`.
- Do not edit a generated file; edit the ticket or configuration and re-render.
- Re-read a ticket before editing it. If someone else changed it, append a dated note
  instead of overwriting.
- Keep `render` and its resulting generated files in the same commit.
- When two sessions close tickets at once, the second `render` is a no-op on files that
  already match; if it conflicts, re-run `check` and resolve at the ticket level.

## A worked example

[`examples/demo`](../examples/demo) contains six tickets across three modules:

- a decision map in `core` with two children;
- one closed decision that unblocks an implementation ticket;
- a cross-module API ticket blocked by that implementation;
- a documentation ticket linked to the API ticket;
- a closed ticket with a placeholder owner.

Its committed `docs/tickets/` output shows every view: module stats, hierarchy, frontier,
blocked, missing owners, and cross-module relations. Run:

```bash
cd examples/demo
python ../../skills/ticket-index/scripts/ticket_index.py check
```

Edit a ticket status, run `diff`, and read the few hunks that change. That is the
day-to-day loop.
