# Domain Docs

How the bundled skills consume this repo's domain documentation while exploring the
codebase.

## Before exploring, read these

- **`GLOSSARY.md`** at the repo root, or
- **`GLOSSARY-MAP.md`** at the repo root if it exists: it points at one `GLOSSARY.md` per
  context. Read each one relevant to the topic.
- **`docs/adr/`**: read ADRs that touch the area you are about to work in. In
  multi-context repos, also check `src/<context>/docs/adr/` for context-scoped decisions.

If any of these files do not exist, **proceed silently**. Do not flag their absence and
do not suggest creating them upfront. The `domain-modeling` skill creates them lazily
when terms or decisions actually get resolved.

## File structure

Single-context repo (most repos):

```text
/
├── GLOSSARY.md
├── docs/adr/
│   ├── 0001-event-sourced-orders.md
│   └── 0002-postgres-for-write-model.md
└── src/
```

Multi-context repo (presence of `GLOSSARY-MAP.md` at the root):

```text
/
├── GLOSSARY-MAP.md
├── docs/adr/                          ← system-wide decisions
└── src/
    ├── ordering/
    │   ├── GLOSSARY.md
    │   └── docs/adr/                  ← context-specific decisions
    └── billing/
        ├── GLOSSARY.md
        └── docs/adr/
```

## Use the glossary's vocabulary

When your output names a domain concept (in a ticket title, a refactor proposal, a
hypothesis, a test name), use the term as defined in `GLOSSARY.md`. Do not drift to
synonyms the glossary explicitly avoids.

If the concept you need is not in the glossary yet, that is a signal: either you are
inventing language the project does not use (reconsider) or there is a real gap (note it
for `domain-modeling`).

## Flag ADR conflicts

If your output contradicts an existing ADR, surface it explicitly rather than silently
overriding:

> _Contradicts ADR-0007 (event-sourced orders), but worth reopening because…_
