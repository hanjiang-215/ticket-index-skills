import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX_SCRIPT = ROOT / "skills" / "ticket-index" / "scripts" / "ticket_index.py"


@unittest.skipUnless(
    (ROOT / "ticket-index.toml").is_file(), "the kit is not self-indexed here"
)
class KitIndexTest(unittest.TestCase):
    """This repository indexes its own tickets, so a stale index must fail CI."""

    def test_repository_index_is_current(self) -> None:
        result = subprocess.run(
            [sys.executable, str(INDEX_SCRIPT), "check"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
