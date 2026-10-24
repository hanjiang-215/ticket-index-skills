import importlib.util
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "scripts" / "install.py"
spec = importlib.util.spec_from_file_location("skill_installer", INSTALLER)
installer = importlib.util.module_from_spec(spec)
sys.modules["skill_installer"] = installer
spec.loader.exec_module(installer)


class InstallerTransactionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.target = Path(self.temp.name) / "repo"
        self.target.mkdir()
        self.skills = self.target / ".cursor" / "skills"
        self.skills.mkdir(parents=True)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_failed_copy_preserves_all_existing_skill_directories(self) -> None:
        names = ["ticket-index", "setup-ticket-workflow"]
        originals = {}
        for name in names:
            destination = self.skills / name
            destination.mkdir()
            marker = destination / "local.txt"
            marker.write_text(f"old {name}", encoding="utf-8")
            originals[name] = marker.read_bytes()

        real_copytree = shutil.copytree
        calls = 0

        def fail_second_copy(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("simulated copy failure")
            return real_copytree(*args, **kwargs)

        with mock.patch.object(installer.shutil, "copytree", side_effect=fail_second_copy):
            with self.assertRaises(OSError):
                installer.copy_skills(installer.SKILLS_ROOT, self.skills, names, force=True)

        for name in names:
            marker = self.skills / name / "local.txt"
            with self.subTest(skill=name):
                self.assertEqual(marker.read_bytes(), originals[name])

    def test_invalid_hook_config_does_not_overwrite_installed_skill(self) -> None:
        destination = self.skills / "ticket-index"
        destination.mkdir()
        marker = destination / "local.txt"
        marker.write_text("preserve this installation", encoding="utf-8")
        original = marker.read_bytes()
        hooks = self.target / ".cursor" / "hooks.json"
        hooks.write_text("{ invalid json", encoding="utf-8")

        with mock.patch.object(
            sys,
            "argv",
            [
                str(INSTALLER),
                "--target",
                str(self.target),
                "--skills",
                "ticket-index",
                "--force",
                "--install-hooks",
            ],
        ):
            with self.assertRaises(SystemExit):
                installer.main()

        self.assertEqual(marker.read_bytes(), original)
        self.assertEqual(hooks.read_text(encoding="utf-8"), "{ invalid json")

    def test_hook_write_failure_rolls_back_skill_replacement(self) -> None:
        destination = self.skills / "ticket-index"
        destination.mkdir()
        marker = destination / "local.txt"
        marker.write_text("original", encoding="utf-8")
        hooks = self.target / ".cursor" / "hooks.json"
        hooks.write_text('{"version": 1}', encoding="utf-8")
        hook_content = (hooks, '{"version": 1, "hooks": {}}\n')
        original_replace = installer.os.replace

        def fail_hook_replace(source, target):
            if Path(target) == hooks:
                raise OSError("simulated hook commit failure")
            return original_replace(source, target)

        with mock.patch.object(installer.os, "replace", side_effect=fail_hook_replace):
            with self.assertRaises(OSError):
                installer.copy_skills(
                    installer.SKILLS_ROOT,
                    self.skills,
                    ["ticket-index"],
                    force=True,
                    hooks=hook_content,
                )

        self.assertEqual(marker.read_text(encoding="utf-8"), "original")
        self.assertEqual(hooks.read_text(encoding="utf-8"), '{"version": 1}')


class InstallerMergeDriverTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.target = Path(self.temp.name) / "repo"
        self.target.mkdir()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_writes_gitattributes_rule_even_without_git(self) -> None:
        status = installer.install_git_merge(self.target)
        attributes = (self.target / ".gitattributes").read_text(encoding="utf-8")
        self.assertIn("docs/tickets/** merge=ours", attributes)
        self.assertIn("not a git repository", status)

    def test_registers_merge_driver_on_git_repository(self) -> None:
        dot_git = self.target / ".git"
        dot_git.mkdir()
        (dot_git / "config").write_text("[core]\n\trepositoryformatversion = 0\n", encoding="utf-8")

        installer.install_git_merge(self.target)

        config = (dot_git / "config").read_text(encoding="utf-8")
        self.assertIn('[merge "ours"]', config)
        self.assertIn("driver = true", config)
        attributes = (self.target / ".gitattributes").read_text(encoding="utf-8")
        self.assertIn("docs/tickets/** merge=ours", attributes)

    def test_is_idempotent(self) -> None:
        dot_git = self.target / ".git"
        dot_git.mkdir()
        (dot_git / "config").write_text("[core]\n", encoding="utf-8")

        installer.install_git_merge(self.target)
        first_attrs = (self.target / ".gitattributes").read_text(encoding="utf-8")
        first_config = (dot_git / "config").read_text(encoding="utf-8")

        installer.install_git_merge(self.target)

        self.assertEqual(first_attrs, (self.target / ".gitattributes").read_text(encoding="utf-8"))
        self.assertEqual(first_config, (dot_git / "config").read_text(encoding="utf-8"))

    def test_reads_configured_output_dir(self) -> None:
        (self.target / "ticket-index.toml").write_text(
            '[settings]\noutput_dir = "docs/cards"\n', encoding="utf-8"
        )

        installer.install_git_merge(self.target)

        attributes = (self.target / ".gitattributes").read_text(encoding="utf-8")
        self.assertIn("docs/cards/** merge=ours", attributes)
        self.assertNotIn("docs/tickets/** merge=ours", attributes)

    def test_handles_worktree_gitfile_pointer(self) -> None:
        git_dir = self.target / ".worktrees" / "main"
        git_dir.mkdir(parents=True)
        (git_dir / "config").write_text("[core]\n", encoding="utf-8")
        (self.target / ".git").write_text(f"gitdir: {git_dir.as_posix()}\n", encoding="utf-8")

        installer.install_git_merge(self.target)

        config = (git_dir / "config").read_text(encoding="utf-8")
        self.assertIn('[merge "ours"]', config)


class InstallerGitHooksTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.target = Path(self.temp.name) / "repo"
        self.target.mkdir()
        self.skills = self.target / ".cursor" / "skills"
        self.skills.mkdir(parents=True)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def git_repo(self) -> None:
        dot_git = self.target / ".git"
        dot_git.mkdir()
        (dot_git / "hooks").mkdir()
        (dot_git / "config").write_text("[core]\n", encoding="utf-8")

    def test_writes_post_merge_and_post_checkout_hooks(self) -> None:
        self.git_repo()
        status = installer.install_git_hooks(self.target, self.skills)
        self.assertIn("post-merge", status)
        self.assertIn("post-checkout", status)
        for name in ("post-merge", "post-checkout"):
            content = (self.target / ".git" / "hooks" / name).read_text(encoding="utf-8")
            self.assertIn("ticket-index", content)
            self.assertIn(".cursor/skills/ticket-index/scripts/ticket_index.py", content)
            self.assertIn("exit 0", content)

    def test_never_overwrites_a_user_hook(self) -> None:
        self.git_repo()
        user_hook = self.target / ".git" / "hooks" / "post-merge"
        user_hook.write_text("#!/bin/sh\necho custom\n", encoding="utf-8")
        status = installer.install_git_hooks(self.target, self.skills)
        self.assertIn("kept existing hooks: post-merge", status)
        self.assertIn("custom", user_hook.read_text(encoding="utf-8"))

    def test_skips_cleanly_without_a_git_repository(self) -> None:
        status = installer.install_git_hooks(self.target, self.skills)
        self.assertIn("not a git repository", status)
        self.assertFalse((self.target / ".git" / "hooks" / "post-merge").exists())

    def test_is_idempotent(self) -> None:
        self.git_repo()
        installer.install_git_hooks(self.target, self.skills)
        first = (self.target / ".git" / "hooks" / "post-merge").read_text(encoding="utf-8")
        status = installer.install_git_hooks(self.target, self.skills)
        second = (self.target / ".git" / "hooks" / "post-merge").read_text(encoding="utf-8")
        self.assertEqual(first, second)
        self.assertIn("installed git hooks: post-merge, post-checkout", status)

    def test_main_installs_git_hooks_via_flag(self) -> None:
        self.git_repo()
        with mock.patch.object(
            sys,
            "argv",
            [
                str(INSTALLER),
                "--target",
                str(self.target),
                "--skills",
                "ticket-index",
                "--install-git-hooks",
            ],
        ):
            installer.main()
        self.assertTrue((self.target / ".git" / "hooks" / "post-merge").is_file())
        self.assertTrue((self.target / ".git" / "hooks" / "post-checkout").is_file())


if __name__ == "__main__":
    unittest.main()
