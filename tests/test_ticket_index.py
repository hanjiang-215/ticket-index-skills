import contextlib
import importlib.util
import io
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "ticket-index" / "scripts" / "ticket_index.py"

spec = importlib.util.spec_from_file_location("ticket_index", SCRIPT)
ti = importlib.util.module_from_spec(spec)
sys.modules["ticket_index"] = ti
spec.loader.exec_module(ti)

BASE_SETTINGS = """[settings]
title = "Test Index"
tickets_dir = ".tickets"
output_dir = "docs/tickets"
id_pattern = "demo-[0-9a-z]{4}"
summary_max_chars = 160
placeholder_assignees = ["", "-", "team", "tbd", "todo", "unassigned"]
"""

DEFAULT_MODULES = """[[modules]]
id = "core"
title = "Core Platform"
scope = "Runtime and storage"
"""


class Repo:
    def __init__(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.tickets = self.root / ".tickets"
        self.tickets.mkdir(parents=True)
        self.config = self.root / "ticket-index.toml"

    def close(self) -> None:
        self.temp.cleanup()

    def ticket(
        self,
        ticket_id: str,
        title: str = "A ticket",
        status: str = "open",
        type_: str = "task",
        priority: int = 2,
        assignee: str = "alice",
        parent: str | None = None,
        deps: tuple[str, ...] = (),
        links: tuple[str, ...] = (),
        tags: tuple[str, ...] = (),
        created: str = "2026-01-01T00:00:00Z",
    ) -> Path:
        lines = [
            "---",
            f"id: {ticket_id}",
            f"status: {status}",
            f"type: {type_}",
            f"priority: {priority}",
            f"assignee: {assignee}",
        ]
        if parent:
            lines.append(f"parent: {parent}")
        lines.append("deps: [" + ", ".join(deps) + "]")
        lines.append("links: [" + ", ".join(links) + "]")
        lines.append("tags: [" + ", ".join(tags) + "]")
        lines.append(f"created: {created}")
        lines.append("---")
        lines.append(f"# {title}")
        lines.append("")
        lines.append("Body.")
        path = self.tickets / f"{ticket_id}.md"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path

    def write_config(
        self,
        tickets: dict[str, str] | None = None,
        modules: str = DEFAULT_MODULES,
        settings: str = BASE_SETTINGS,
        path: Path | None = None,
    ) -> Path:
        entries = tickets or {}
        body = settings + "\n" + modules + "\n[tickets]\n"
        for ticket_id, value in entries.items():
            body += f'"{ticket_id}" = {value}\n'
        target = path or self.config
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
        return target

    def load(self) -> "ti.Index":
        return ti.Index(ti.load_config(self.config))

    def run(self, command) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = command()
        return code, out.getvalue(), err.getvalue()

    def read(self, relative: str) -> str:
        return (self.root / relative).read_text(encoding="utf-8")


class TicketIndexTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = Repo()

    def tearDown(self) -> None:
        self.repo.close()

    def entry(self, module: str = "core", summary: str = "Decides the storage boundary") -> str:
        return f'{{ module = "{module}", summary = "{summary}" }}'

    def test_check_reports_missing_generated_files(self) -> None:
        self.repo.ticket("demo-a1b2")
        self.repo.write_config({"demo-a1b2": self.entry()})
        code, out, err = self.repo.run(lambda: ti.cmd_check(self.repo.load()))
        self.assertEqual(code, 1)
        self.assertIn("missing generated file", err)
        self.assertIn("INDEX.md", err)

    def test_render_then_check_is_green(self) -> None:
        self.repo.ticket("demo-a1b2")
        self.repo.write_config({"demo-a1b2": self.entry()})
        code, out, err = self.repo.run(lambda: ti.cmd_render(self.repo.load()))
        self.assertEqual(code, 0, err)
        self.assertIn("written 2", out)
        code, out, err = self.repo.run(lambda: ti.cmd_check(self.repo.load()))
        self.assertEqual(code, 0, err)
        self.assertIn("OK: 1 tickets, 1 modules", out)
        self.assertTrue((self.repo.root / "docs/tickets/INDEX.md").is_file())
        self.assertTrue((self.repo.root / "docs/tickets/modules/core.md").is_file())

    def test_render_is_idempotent(self) -> None:
        self.repo.ticket("demo-a1b2")
        self.repo.write_config({"demo-a1b2": self.entry()})
        self.repo.run(lambda: ti.cmd_render(self.repo.load()))
        before = self.repo.read("docs/tickets/INDEX.md")
        code, out, err = self.repo.run(lambda: ti.cmd_render(self.repo.load()))
        self.assertEqual(code, 0, err)
        self.assertIn("written 0", out)
        self.assertEqual(before, self.repo.read("docs/tickets/INDEX.md"))

    def test_stale_generated_file_is_detected(self) -> None:
        self.repo.ticket("demo-a1b2")
        self.repo.write_config({"demo-a1b2": self.entry()})
        self.repo.run(lambda: ti.cmd_render(self.repo.load()))
        index = self.repo.root / "docs/tickets/INDEX.md"
        index.write_text(index.read_text(encoding="utf-8") + "\nhand edit\n", encoding="utf-8")
        code, _, err = self.repo.run(lambda: ti.cmd_check(self.repo.load()))
        self.assertEqual(code, 1)
        self.assertIn("stale generated file", err)

    def test_missing_summary_blocks_render(self) -> None:
        self.repo.ticket("demo-a1b2")
        self.repo.write_config({"demo-a1b2": '{ module = "core", summary = "" }'})
        code, _, err = self.repo.run(lambda: ti.cmd_render(self.repo.load()))
        self.assertEqual(code, 1)
        self.assertIn("has no summary", err)
        self.assertFalse((self.repo.root / "docs/tickets/INDEX.md").exists())

    def test_unknown_module_is_an_error(self) -> None:
        self.repo.ticket("demo-a1b2")
        self.repo.write_config({"demo-a1b2": self.entry(module="ghost")})
        index = self.repo.load()
        self.assertTrue(any("unknown modules ghost" in item for item in index.errors))

    def test_entry_for_missing_ticket_is_an_error(self) -> None:
        self.repo.write_config({"demo-zzzz": self.entry()})
        index = self.repo.load()
        self.assertTrue(any("demo-zzzz" in item and "not a ticket file" in item for item in index.errors))

    def test_ticket_without_entry_is_an_error(self) -> None:
        self.repo.ticket("demo-a1b2")
        self.repo.write_config()
        index = self.repo.load()
        self.assertTrue(any("missing module and summary" in item for item in index.errors))

    def test_broken_references_are_errors(self) -> None:
        self.repo.ticket("demo-a1b2", parent="demo-9999", deps=("demo-8888",), links=("demo-7777",))
        self.repo.write_config({"demo-a1b2": self.entry()})
        index = self.repo.load()
        joined = "\n".join(index.errors)
        self.assertIn("parent `demo-9999` does not exist", joined)
        self.assertIn("dependency `demo-8888` does not exist", joined)
        self.assertIn("link `demo-7777` does not exist", joined)

    def test_id_must_match_filename(self) -> None:
        path = self.repo.ticket("demo-a1b2")
        path.write_text(
            path.read_text(encoding="utf-8").replace("id: demo-a1b2", "id: demo-b2c3"),
            encoding="utf-8",
        )
        self.repo.write_config()
        index = self.repo.load()
        self.assertTrue(any("does not match the filename" in item for item in index.errors))

    def test_non_ticket_file_is_skipped_with_warning(self) -> None:
        self.repo.ticket("demo-a1b2")
        (self.repo.tickets / "notes.md").write_text("# Notes\n", encoding="utf-8")
        (self.repo.tickets / "README.md").write_text("# Readme\n", encoding="utf-8")
        self.repo.write_config({"demo-a1b2": self.entry()})
        index = self.repo.load()
        self.assertEqual(index.errors, [])
        self.assertTrue(any("Ignoring non-ticket file: notes.md" in item for item in index.warnings))
        self.assertFalse(any("README" in item for item in index.warnings))

    def test_unknown_status_warns_and_is_inactive(self) -> None:
        self.repo.ticket("demo-a1b2", status="doing")
        self.repo.write_config({"demo-a1b2": self.entry()})
        index = self.repo.load()
        self.assertTrue(any("unknown status `doing`" in item for item in index.warnings))
        self.assertFalse(index.tickets["demo-a1b2"].active)

    def test_module_validation(self) -> None:
        self.repo.write_config(
            modules="""[[modules]]
id = "Bad_ID"
title = "Bad"

[[modules]]
id = "core"
title = ""

[[modules]]
id = "core"
title = "Duplicate"
"""
        )
        index = self.repo.load()
        joined = "\n".join(index.errors)
        self.assertIn("Invalid module id `Bad_ID`", joined)
        self.assertIn("Module `core` is missing a title", joined)
        self.assertIn("Duplicate module id `core`", joined)

    def test_obsolete_module_file_is_removed(self) -> None:
        self.repo.ticket("demo-a1b2")
        self.repo.write_config({"demo-a1b2": self.entry()})
        self.repo.run(lambda: ti.cmd_render(self.repo.load()))
        obsolete = self.repo.root / "docs/tickets/modules/old.md"
        obsolete.write_text(ti.GENERATED_MARK + "\n\n# Old\n", encoding="utf-8")

        self.repo.write_config(
            {"demo-a1b2": self.entry(module="core2")},
            modules=DEFAULT_MODULES.replace('id = "core"', 'id = "core2"'),
        )
        code, out, err = self.repo.run(lambda: ti.cmd_render(self.repo.load()))
        self.assertEqual(code, 0, err)
        self.assertIn("removed 2", out)
        self.assertFalse(obsolete.exists())
        self.assertFalse((self.repo.root / "docs/tickets/modules/core.md").exists())
        self.assertTrue((self.repo.root / "docs/tickets/modules/core2.md").exists())

    def test_multi_module_expands_only_in_primary(self) -> None:
        self.repo.ticket("demo-a1b2", title="Docs ticket")
        self.repo.write_config(
            {"demo-a1b2": '{ module = ["docs", "api"], summary = "Covers both domains" }'},
            modules=DEFAULT_MODULES
            + """
[[modules]]
id = "api"
title = "Public API"
scope = "Contracts"

[[modules]]
id = "docs"
title = "Documentation"
scope = "Guides"
""",
        )
        self.repo.run(lambda: ti.cmd_render(self.repo.load()))
        docs_page = self.repo.read("docs/tickets/modules/docs.md")
        api_page = self.repo.read("docs/tickets/modules/api.md")
        index_page = self.repo.read("docs/tickets/INDEX.md")
        api_tree, api_membership = api_page.split("## Cross-module membership", 1)
        self.assertIn("**Docs ticket**", docs_page)
        self.assertNotIn("**Docs ticket**", api_tree)
        self.assertIn("**Docs ticket**", api_membership)
        self.assertIn("Covers both domains", api_membership)
        self.assertIn("Multi-module membership", index_page)
        self.assertIn("| Documentation |", index_page)

    def test_cross_module_links_are_deduplicated(self) -> None:
        self.repo.ticket("demo-a1b2", links=("demo-b2c3",))
        self.repo.ticket("demo-b2c3", links=("demo-a1b2",))
        self.repo.write_config(
            {
                "demo-a1b2": self.entry(),
                "demo-b2c3": self.entry(module="api"),
            },
            modules=DEFAULT_MODULES
            + """
[[modules]]
id = "api"
title = "Public API"
scope = "Contracts"
""",
        )
        self.repo.run(lambda: ti.cmd_render(self.repo.load()))
        index_page = self.repo.read("docs/tickets/INDEX.md")
        self.assertEqual(index_page.count("| linked to |"), 1)

    def test_frontier_and_blocked_tables(self) -> None:
        self.repo.ticket("demo-a1b2", title="Ready now")
        self.repo.ticket("demo-b2c3", title="Needs A", deps=("demo-a1b2",))
        self.repo.ticket("demo-c3d4", title="Needs closed", deps=("demo-d4e5",))
        self.repo.ticket("demo-d4e5", title="Already closed", status="closed")
        self.repo.write_config(
            {
                "demo-a1b2": self.entry(),
                "demo-b2c3": self.entry(),
                "demo-c3d4": self.entry(),
                "demo-d4e5": self.entry(),
            }
        )
        self.repo.run(lambda: ti.cmd_render(self.repo.load()))
        index_page = self.repo.read("docs/tickets/INDEX.md")
        frontier, blocked = index_page.split("## Blocked", 1)
        self.assertIn("Ready now", frontier)
        self.assertIn("Needs closed", frontier)
        self.assertNotIn("Needs A", frontier)
        self.assertIn("Needs A", blocked)
        self.assertIn("demo-a1b2", blocked)
        self.assertNotIn("Already closed", blocked)

    def test_placeholder_assignee_is_listed_as_missing_owner(self) -> None:
        self.repo.ticket("demo-a1b2", assignee="Team")
        self.repo.write_config({"demo-a1b2": self.entry()})
        self.repo.run(lambda: ti.cmd_render(self.repo.load()))
        index_page = self.repo.read("docs/tickets/INDEX.md")
        self.assertIn("## Missing owners", index_page)
        self.assertIn("`Team`", index_page)
        self.assertIn("(placeholder)", index_page)

    def test_cross_module_parent_is_a_root_with_pointer(self) -> None:
        self.repo.ticket("demo-a1b2", title="Map", tags=("map",))
        self.repo.ticket("demo-b2c3", title="Child", parent="demo-a1b2")
        self.repo.write_config(
            {
                "demo-a1b2": self.entry(module="core"),
                "demo-b2c3": self.entry(module="docs"),
            },
            modules=DEFAULT_MODULES
            + """
[[modules]]
id = "docs"
title = "Documentation"
scope = "Guides"
""",
        )
        self.repo.run(lambda: ti.cmd_render(self.repo.load()))
        docs_page = self.repo.read("docs/tickets/modules/docs.md")
        self.assertIn("**Child**", docs_page)
        self.assertIn("parent", docs_page)
        self.assertIn("Core Platform", docs_page)

    def test_hierarchy_cycle_stays_visible(self) -> None:
        self.repo.ticket("demo-a1b2", title="Alpha", parent="demo-b2c3")
        self.repo.ticket("demo-b2c3", title="Beta", parent="demo-a1b2")
        self.repo.write_config(
            {"demo-a1b2": self.entry(), "demo-b2c3": self.entry()}
        )
        code, _, err = self.repo.run(lambda: ti.cmd_render(self.repo.load()))
        self.assertEqual(code, 0, err)
        page = self.repo.read("docs/tickets/modules/core.md")
        self.assertIn("Alpha", page)
        self.assertIn("Beta", page)
        self.assertIn("hierarchy cycle", page)

    def test_legacy_config_layout(self) -> None:
        self.repo.ticket("demo-a1b2")
        legacy = self.repo.root / "docs/tickets/index.toml"
        legacy.parent.mkdir(parents=True)
        legacy.write_text(
            """[[modules]]
id = "core"
title = "Core"
scope = "Scope"

[tickets]
"demo-a1b2" = { module = "core", summary = "Legacy layout works" }
""",
            encoding="utf-8",
        )
        config = ti.load_config(legacy)
        self.assertEqual(config.root, self.repo.root)
        index = ti.Index(config)
        self.assertEqual(index.errors, [])
        self.repo.run(lambda: ti.cmd_render(index))
        self.assertTrue((self.repo.root / "docs/tickets/INDEX.md").is_file())
        self.assertTrue((self.repo.root / "docs/tickets/modules/core.md").is_file())

    def test_diff_writes_nothing_and_reports_changes(self) -> None:
        self.repo.ticket("demo-a1b2")
        self.repo.write_config({"demo-a1b2": self.entry()})
        code, out, err = self.repo.run(lambda: ti.cmd_diff(self.repo.load()))
        self.assertEqual(code, 0, err)
        self.assertIn("would change", out)
        self.assertIn("### docs/tickets/INDEX.md", out)
        self.assertFalse((self.repo.root / "docs/tickets").exists())

    def test_diff_reports_nothing_when_current(self) -> None:
        self.repo.ticket("demo-a1b2")
        self.repo.write_config({"demo-a1b2": self.entry()})
        self.repo.run(lambda: ti.cmd_render(self.repo.load()))
        code, out, err = self.repo.run(lambda: ti.cmd_diff(self.repo.load()))
        self.assertEqual(code, 0, err)
        self.assertIn("already current", out)

    def test_facts_lists_one_row_per_ticket(self) -> None:
        self.repo.ticket("demo-a1b2", title="A title", assignee="")
        self.repo.write_config({"demo-a1b2": self.entry(summary="A summary")})
        code, out, err = self.repo.run(lambda: ti.cmd_facts(self.repo.load()))
        self.assertEqual(code, 0, err)
        lines = out.strip().splitlines()
        self.assertEqual(len(lines), 2)
        self.assertTrue(lines[0].startswith("id\tstatus\ttype"))
        self.assertIn("demo-a1b2", lines[1])
        self.assertIn("A summary", lines[1])
        self.assertIn("[unassigned]", lines[1])

    def test_summary_length_warns_but_does_not_fail(self) -> None:
        self.repo.ticket("demo-a1b2")
        self.repo.write_config({"demo-a1b2": self.entry(summary="x" * 200)})
        index = self.repo.load()
        self.assertEqual(index.errors, [])
        self.assertTrue(any("summary is 200 characters" in item for item in index.warnings))

    def test_invalid_summary_max_chars_is_rejected(self) -> None:
        self.repo.write_config(
            settings=BASE_SETTINGS.replace("summary_max_chars = 160", 'summary_max_chars = "many"')
        )
        with self.assertRaises(SystemExit) as context:
            ti.load_config(self.repo.config)
        self.assertIn("summary_max_chars", str(context.exception))

    def test_deep_hierarchy_renders_without_recursion(self) -> None:
        ticket_count = 1500
        entries: dict[str, str] = {}
        previous = None
        for number in range(ticket_count):
            ticket_id = f"demo-{number:04x}"
            self.repo.ticket(ticket_id, title=f"Ticket {number}", parent=previous)
            entries[ticket_id] = self.entry()
            previous = ticket_id
        self.repo.write_config(entries)

        index = self.repo.load()
        code, out, err = self.repo.run(lambda: ti.cmd_render(index))

        self.assertEqual(code, 0, err)
        module_page = self.repo.read("docs/tickets/modules/core.md")
        self.assertEqual(module_page.count("**Ticket "), ticket_count)

    def test_module_rendering_reuses_sorted_ticket_view(self) -> None:
        module_lines = "\n".join(
            f'[[modules]]\nid = "area-{number}"\ntitle = "Area {number}"\nscope = "Scope"'
            for number in range(8)
        )
        modules = module_lines + "\n"
        entries: dict[str, str] = {}
        for number in range(8):
            ticket_id = f"demo-{number:04x}"
            self.repo.ticket(ticket_id)
            entries[ticket_id] = self.entry(module=f"area-{number}")
        self.repo.write_config(entries, modules=modules)
        index = self.repo.load()

        sort_calls = 0
        original_sorted_tickets = index.sorted_tickets

        def count_sorted_tickets():
            nonlocal sort_calls
            sort_calls += 1
            return original_sorted_tickets()

        index.sorted_tickets = count_sorted_tickets
        expected = index.expected_files()

        self.assertEqual(len(expected), 9)
        self.assertLessEqual(sort_calls, 2)

    def test_render_refreshes_ticket_snapshot_after_waiting_for_lock(self) -> None:
        self.repo.ticket("demo-a1b2", title="Original title")
        self.repo.write_config({"demo-a1b2": self.entry()})
        stale_index = self.repo.load()
        self.repo.ticket("demo-a1b2", title="Updated title")

        code, out, err = self.repo.run(lambda: ti.cmd_render(stale_index))

        self.assertEqual(code, 0, err)
        module_page = self.repo.read("docs/tickets/modules/core.md")
        self.assertIn("**Updated title**", module_page)
        self.assertNotIn("**Original title**", module_page)

    def test_render_lock_serializes_threads(self) -> None:
        import threading

        attempting = threading.Event()
        acquired = threading.Event()

        def wait_for_lock() -> None:
            attempting.set()
            with ti.render_lock(self.repo.root):
                acquired.set()

        with ti.render_lock(self.repo.root):
            worker = threading.Thread(target=wait_for_lock)
            worker.start()
            self.assertTrue(attempting.wait(timeout=2))
            self.assertFalse(acquired.wait(timeout=0.1))

        self.assertTrue(acquired.wait(timeout=2))
        worker.join(timeout=2)
        self.assertFalse(worker.is_alive())

    def test_concurrent_render_processes_leave_a_current_index(self) -> None:
        import subprocess
        import sys

        entries: dict[str, str] = {}
        for number in range(40):
            ticket_id = f"demo-{number:04x}"
            parent = f"demo-{number - 1:04x}" if number else None
            self.repo.ticket(ticket_id, parent=parent)
            entries[ticket_id] = self.entry()
        self.repo.write_config(entries)
        command = [
            sys.executable,
            str(SCRIPT),
            "render",
            "--config",
            str(self.repo.config),
        ]
        processes = [
            subprocess.Popen(
                command,
                cwd=self.repo.root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
            )
            for _ in range(2)
        ]
        results = [process.communicate(timeout=20) for process in processes]

        for process, (stdout, stderr) in zip(processes, results):
            self.assertEqual(process.returncode, 0, stdout + stderr)
        code, out, err = self.repo.run(lambda: ti.cmd_check(self.repo.load()))
        self.assertEqual(code, 0, err)
        self.assertIn("40 tickets", out)


if __name__ == "__main__":
    unittest.main()
