import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "skills" / "ticket-index" / "hooks" / "ticket-index-sync.py"
INDEX_SCRIPT = ROOT / "skills" / "ticket-index" / "scripts" / "ticket_index.py"

spec = importlib.util.spec_from_file_location("ticket_index_sync", HOOK)
hook = importlib.util.module_from_spec(spec)
sys.modules["ticket_index_sync"] = hook
spec.loader.exec_module(hook)

CONFIG = """[settings]
tickets_dir = ".tickets"
output_dir = "docs/tickets"

[[modules]]
id = "core"
title = "Core"
scope = "Scope"

[tickets]
"demo-a1b2" = { module = "core", summary = "A summary" }
"""


class HookTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.tickets = self.root / ".tickets"
        self.tickets.mkdir()
        self.config = self.root / "ticket-index.toml"
        self.config.write_text(CONFIG, encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_shell_mutations_trigger_render(self) -> None:
        for command in ("fer create --title x", "python x.py", "fer status demo-a1b2 closed"):
            with self.subTest(command=command):
                expected = command.startswith("fer")
                self.assertEqual(
                    hook.touches_tickets("after-shell", {"command": command}, self.config),
                    expected,
                )

    def test_shell_reads_and_unrelated_commands_do_not_trigger(self) -> None:
        for command in ("fer list", "fer show demo-a1b2", "git status", "python app.py"):
            with self.subTest(command=command):
                self.assertFalse(
                    hook.touches_tickets("after-shell", {"command": command}, self.config)
                )

    def test_file_edits_trigger_only_for_tickets_and_config(self) -> None:
        ticket = self.tickets / "demo-a1b2.md"
        cases = [
            (str(ticket), True),
            (str(self.config), True),
            (str(self.root / "README.md"), False),
            (str(self.root / "docs/tickets/INDEX.md"), False),
        ]
        for path, expected in cases:
            with self.subTest(path=path):
                self.assertEqual(
                    hook.touches_tickets("after-file-edit", {"file_path": path}, self.config),
                    expected,
                )

    def test_config_edit_triggers_with_an_unresolved_config_path(self) -> None:
        # Cursor may hand over either form of the path, and temp directories are
        # symlinked on some platforms, so both sides must be compared resolved.
        indirect = self.root / "docs" / ".." / "ticket-index.toml"
        self.assertTrue(
            hook.touches_tickets(
                "after-file-edit", {"file_path": str(self.config)}, indirect
            )
        )

    def test_load_paths_for_primary_layout(self) -> None:
        root, tickets, output = hook.load_paths(self.config)
        self.assertEqual(root, self.root)
        self.assertEqual(tickets, self.tickets.resolve())
        self.assertEqual(output, (self.root / "docs" / "tickets").resolve())

    def test_load_paths_for_legacy_layout(self) -> None:
        legacy = self.root / "docs" / "tickets" / "index.toml"
        legacy.parent.mkdir(parents=True)
        legacy.write_text(CONFIG, encoding="utf-8")
        root, tickets, output = hook.load_paths(legacy)
        self.assertEqual(root, self.root)
        self.assertEqual(tickets, self.tickets.resolve())
        self.assertEqual(output, legacy.parent.resolve())

    def test_hook_renders_after_a_ticket_edit(self) -> None:
        ticket = self.tickets / "demo-a1b2.md"
        ticket.write_text("# A ticket\n", encoding="utf-8")
        env = os.environ.copy()
        env["TICKET_INDEX_CONFIG"] = str(self.config)
        result = subprocess.run(
            [sys.executable, str(HOOK), "after-file-edit"],
            input=json.dumps({"file_path": str(ticket)}),
            cwd=self.root,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.root / "docs/tickets/INDEX.md").is_file())
        self.assertTrue((self.root / "docs/tickets/modules/core.md").is_file())

    def test_hook_ignores_unrelated_edits(self) -> None:
        env = os.environ.copy()
        env["TICKET_INDEX_CONFIG"] = str(self.config)
        result = subprocess.run(
            [sys.executable, str(HOOK), "after-file-edit"],
            input=json.dumps({"file_path": str(self.root / "README.md")}),
            cwd=self.root,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.root / "docs/tickets").exists())

    def test_hook_exits_cleanly_without_config(self) -> None:
        env = os.environ.copy()
        env.pop("TICKET_INDEX_CONFIG", None)
        result = subprocess.run(
            [sys.executable, str(HOOK), "after-file-edit"],
            input=json.dumps({"file_path": str(self.root / "README.md")}),
            cwd=self.root,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_hook_ignores_malformed_payload(self) -> None:
        env = os.environ.copy()
        env["TICKET_INDEX_CONFIG"] = str(self.config)
        result = subprocess.run(
            [sys.executable, str(HOOK), "after-file-edit"],
            input="not json",
            cwd=self.root,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_hook_accepts_a_utf8_bom_payload(self) -> None:
        ticket = self.tickets / "demo-a1b2.md"
        ticket.write_text("# A ticket\n", encoding="utf-8")
        env = os.environ.copy()
        env["TICKET_INDEX_CONFIG"] = str(self.config)
        payload = json.dumps({"file_path": str(ticket)}).encode("utf-8-sig")
        result = subprocess.run(
            [sys.executable, str(HOOK), "after-file-edit"],
            input=payload,
            cwd=self.root,
            env=env,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.root / "docs/tickets/INDEX.md").is_file())


if __name__ == "__main__":
    unittest.main()
