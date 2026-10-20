#!/usr/bin/env python3
"""Run the kit's verification: unit tests, the demo cycle, and the installer.

Standard library only. Exits non-zero on the first failure.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parents[1]
DEMO = KIT_ROOT / "examples" / "demo"
INDEX_SCRIPT = KIT_ROOT / "skills" / "ticket-index" / "scripts" / "ticket_index.py"
INSTALL_SCRIPT = KIT_ROOT / "scripts" / "install.py"


def run(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def fail(label: str, result: subprocess.CompletedProcess[str]) -> int:
    print(f"FAIL: {label} (exit {result.returncode})")
    if result.stdout.strip():
        print(result.stdout.rstrip())
    if result.stderr.strip():
        print(result.stderr.rstrip(), file=sys.stderr)
    return 1


def check_exit(
    label: str, result: subprocess.CompletedProcess[str], expected: int
) -> int | None:
    if result.returncode != expected:
        return fail(label, result)
    print(f"ok: {label}")
    return None


def verify_units() -> int:
    print("== unit tests ==")
    result = run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], KIT_ROOT)
    return check_exit("unit tests", result, 0) or 0


def verify_demo() -> int:
    print("== demo cycle ==")
    with tempfile.TemporaryDirectory(prefix="ticket-index-demo-") as temp:
        demo = Path(temp) / "demo"
        shutil.copytree(DEMO, demo)
        shutil.rmtree(demo / "docs" / "tickets", ignore_errors=True)

        script = str(INDEX_SCRIPT)
        result = run([sys.executable, script, "check"], demo)
        if check_exit("check fails before render", result, 1):
            return 1

        result = run([sys.executable, script, "render"], demo)
        if check_exit("render writes the index", result, 0):
            return 1

        result = run([sys.executable, script, "check"], demo)
        if check_exit("check passes after render", result, 0):
            return 1

        result = run([sys.executable, script, "diff"], demo)
        if check_exit("diff is clean after render", result, 0):
            return 1
        if "already current" not in result.stdout:
            return fail("diff reports no pending changes", result)

        result = run([sys.executable, script, "render"], demo)
        if check_exit("render is idempotent", result, 0):
            return 1
        if "written 0" not in result.stdout:
            return fail("second render writes nothing", result)
    return 0


def verify_installer() -> int:
    print("== installer ==")
    with tempfile.TemporaryDirectory(prefix="ticket-index-install-") as temp:
        target = Path(temp) / "repo"
        target.mkdir()

        result = run(
            [sys.executable, str(INSTALL_SCRIPT), "--target", str(target), "--skills", "ticket-index", "--install-hooks"],
            KIT_ROOT,
        )
        if check_exit("install skills and hooks", result, 0):
            return 1

        installed = target / ".cursor" / "skills" / "ticket-index" / "SKILL.md"
        if not installed.is_file():
            return fail("installed SKILL.md is missing", result)

        hooks_path = target / ".cursor" / "hooks.json"
        hooks_text = hooks_path.read_text(encoding="utf-8") if hooks_path.is_file() else ""
        if "ticket-index-sync.py after-file-edit" not in hooks_text:
            return fail("hooks.json does not reference the sync hook", result)

        result = run(
            [sys.executable, str(INSTALL_SCRIPT), "--target", str(target), "--skills", "ticket-index"],
            KIT_ROOT,
        )
        if check_exit("installer refuses to overwrite", result, 1):
            return 1

        result = run(
            [sys.executable, str(INSTALL_SCRIPT), "--target", str(target), "--skills", "ticket-index", "--force"],
            KIT_ROOT,
        )
        if check_exit("installer overwrites with --force", result, 0):
            return 1
    return 0


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")

    for step in (verify_units, verify_demo, verify_installer):
        code = step()
        if code:
            return code

    print()
    print("All verification passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
