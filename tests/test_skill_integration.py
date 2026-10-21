import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "scripts" / "install.py"
SKILL_NAMES = {"codebase-design", "diagnosing-bugs", "prototype"}
UPSTREAM_COMMIT = "5beb35b040e3de97e54fa9e386d7e42d15c295c2"


class SkillIntegrationTest(unittest.TestCase):
    def test_installer_discovers_and_copies_new_skills_and_references(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "repo"
            target.mkdir()
            result = subprocess.run(
                [sys.executable, str(INSTALLER), "--target", str(target)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            installed_root = target / ".cursor" / "skills"
            self.assertTrue(SKILL_NAMES <= {path.name for path in installed_root.iterdir()})

            required_files = {
                "codebase-design": (
                    "SKILL.md",
                    "agents/openai.yaml",
                    "DEEPENING.md",
                    "DESIGN-IT-TWICE.md",
                ),
                "prototype": (
                    "SKILL.md",
                    "agents/openai.yaml",
                    "LOGIC.md",
                    "UI.md",
                ),
                "diagnosing-bugs": (
                    "SKILL.md",
                    "agents/openai.yaml",
                    "scripts/hitl-loop.template.sh",
                ),
            }
            for skill, files in required_files.items():
                with self.subTest(skill=skill):
                    source = ROOT / "skills" / skill
                    installed = installed_root / skill
                    for relative_path in files:
                        with self.subTest(file=relative_path):
                            self.assertEqual(
                                (installed / relative_path).read_bytes(),
                                (source / relative_path).read_bytes(),
                            )

    def test_skill_descriptions_use_discovery_triggers(self) -> None:
        for skill in SKILL_NAMES:
            with self.subTest(skill=skill):
                content = (ROOT / "skills" / skill / "SKILL.md").read_text(
                    encoding="utf-8"
                )
                frontmatter = content.split("---", 2)[1]
                self.assertRegex(frontmatter, r"(?m)^description: Use when .+")

    def test_third_party_notice_records_sources_and_licenses(self) -> None:
        notice_path = ROOT / "THIRD-PARTY-NOTICES.md"
        self.assertTrue(notice_path.is_file(), "third-party notice is missing")
        notice = notice_path.read_text(encoding="utf-8")

        for required_text in (
            "Matt Pocock",
            "MIT",
            "https://github.com/mattpocock/skills",
            UPSTREAM_COMMIT,
            "codebase-design",
            "diagnosing-bugs",
            "prototype",
            "HumanLayer",
            "Dex Horthy",
            "https://github.com/humanlayer/skills",
        ):
            with self.subTest(text=required_text):
                self.assertIn(required_text, notice)

        for relative_path, copyright_line in (
            ("licenses/MIT-mattpocock-skills.txt", "Copyright (c) 2026 Matt Pocock"),
            ("licenses/MIT-humanlayer-show-me.txt", "Copyright (c) 2026 HumanLayer"),
        ):
            with self.subTest(license=relative_path):
                self.assertIn(
                    copyright_line,
                    (ROOT / relative_path).read_text(encoding="utf-8"),
                )

    def test_readmes_list_the_added_skills_and_source_notice(self) -> None:
        for readme_name in ("README.md", "README.zh-CN.md"):
            with self.subTest(readme=readme_name):
                readme = (ROOT / readme_name).read_text(encoding="utf-8")
                for skill in SKILL_NAMES:
                    self.assertIn(skill, readme)
                self.assertIn("THIRD-PARTY-NOTICES.md", readme)

    def test_readmes_document_source_based_conflict_resolution(self) -> None:
        english = (ROOT / "README.md").read_text(encoding="utf-8")
        chinese = (ROOT / "README.zh-CN.md").read_text(encoding="utf-8")

        self.assertIn("`docs/tickets/**` is", english)
        self.assertIn("never hand-merge the", english)
        self.assertIn("regenerate", english.lower())
        self.assertIn("不要手工合并 `docs/tickets/**`", chinese)
        self.assertIn("重新生成", chinese)

    def test_index_conflicts_are_resolved_from_sources_then_regenerated(self) -> None:
        skill = (ROOT / "skills" / "ticket-index" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("never hand-merge `docs/tickets/**`", skill)
        self.assertIn("resolve `.tickets/*.md` and `ticket-index.toml` first", skill)
        self.assertIn("run `render` and `check`", skill)
        self.assertIn("After the rebase finishes", skill)


if __name__ == "__main__":
    unittest.main()
