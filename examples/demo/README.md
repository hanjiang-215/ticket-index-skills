# Demo project

A six-ticket project that exercises every view in the index. The tickets describe the
first end-to-end release of a small execution service: a decision map, a closed storage
decision, an implementation ticket blocked by the decision, an API ticket blocked by the
implementation, a documentation ticket linked to the API, and a closed ticket whose owner
is still a placeholder.

## Run it

```bash
cd examples/demo
python ../../skills/ticket-index/scripts/ticket_index.py check
```

The generated index is committed in [`docs/tickets/`](docs/tickets), so `check` should
report `OK`.

## Try the loop

1. Close the implementation ticket:

   In `.tickets/demo-c3d4.md`, change `status: open` to `status: closed`.

2. Review the delta without writing:

   ```bash
   python ../../skills/ticket-index/scripts/ticket_index.py diff
   ```

   Only the affected hunks appear: the ticket moves from the frontier into the module
   tree as closed, and the API ticket becomes unblocked.

3. Write and verify:

   ```bash
   python ../../skills/ticket-index/scripts/ticket_index.py render
   python ../../skills/ticket-index/scripts/ticket_index.py check
   ```

4. Break something on purpose. Add a dependency on a non-existent ticket and run
   `check`; it exits `1` and names the broken reference.

Reset the ticket when you are done, or re-clone the repository.

## What to look at

- `ticket-index.toml`: three modules, six ownership and summary entries.
- `docs/tickets/INDEX.md`: overview, owners, modules, frontier, blocked, missing owners,
  and cross-module relations.
- `docs/tickets/modules/core.md`: a map with two children, one of them closed.
- `.tickets/demo-e5f6.md`: a ticket owned by two modules; it expands only in its primary
  module and appears as a reference in the other.
