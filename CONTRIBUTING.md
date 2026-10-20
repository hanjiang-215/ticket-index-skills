# Contributing

Thanks for improving the kit. The bar is high for behaviour and low for ceremony: small,
tested changes that keep the generated index deterministic.

## Development

Requirements: Python 3.11+ (the index script uses `tomllib`). No dependencies.

```bash
python -m unittest discover -s tests -v
python scripts/verify.py
```

`verify.py` runs the unit suite and the demo end to end: `check` on an empty output,
`render`, `check`, and `diff`. It fails on a stale generated file or a non-zero exit code.

## Changing the index script

The script has one contract: **the same inputs must always produce byte-identical
output**. If you add a field:

1. Add a unit test in `tests/test_ticket_index.py` covering the new behaviour, including
   its failure mode.
2. Update the ticket contract in
   [`docs/ticket-contract.md`](docs/ticket-contract.md) and
   [`skills/ticket-index/SKILL.md`](skills/ticket-index/SKILL.md).
3. Regenerate the demo (`cd examples/demo && python ../../skills/ticket-index/scripts/ticket_index.py render`)
   and commit the changed generated files with the code.

Do not add network access, timestamps, absolute paths, or unordered iteration to the
render path. Those make `diff` noisy and `check` unreliable.

## Adding or changing a skill

- One folder per skill under `skills/`, with a `SKILL.md` whose frontmatter has `name`
  and `description`. The description states when the skill should be reached, not just
  what it is.
- Keep `SKILL.md` under roughly 500 lines. Move reference material into sibling files and
  point at them.
- Set `disable-model-invocation: true` for user-invoked workflow skills, following the
  existing files.
- Add or update `agents/openai.yaml` when the skill is user-invoked.
- If you adapt upstream material, record the source, author, license, and URL in
  [`THIRD-PARTY-NOTICES.md`](THIRD-PARTY-NOTICES.md) and in the skill's
  `metadata.credits`.

## Editing skills that were adapted

The bundled companion skills are adapted copies, not vendored upstream code. Changes are
welcome, but keep them surgical: the local ticket contract is the reason this kit exists,
and cross-skill references should point at `setup-ticket-workflow`, not at the upstream
setup skill.

## Pull requests

- Keep generated files and their source in the same commit.
- State the verification you ran (`python scripts/verify.py`, plus any manual demo run).
- If the change affects the workflow, update the diagram and the skills table in
  `README.md`.
