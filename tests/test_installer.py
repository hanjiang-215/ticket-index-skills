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


if __name__ == "__main__":
    unittest.main()
