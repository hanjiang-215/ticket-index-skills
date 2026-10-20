#!/usr/bin/env python3
"""Install the bundled skills into a repository.

Copies the skill folders to the directory your agent reads (``.cursor/skills`` for
Cursor, ``.claude/skills`` for Claude Code, or any path via ``--skills-dir``). Optionally
merges the ticket-index auto-sync hook into ``.cursor/hooks.json``.

Standard library only.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = KIT_ROOT / "skills"
AGENT_DIRS = {
    "cursor": ".cursor/skills",
    "claude": ".claude/skills",
}


def available_skills() -> list[str]:
    return sorted(
        path.name
        for path in SKILLS_ROOT.iterdir()
        if path.is_dir() and (path / "SKILL.md").is_file()
    )


def parse_skills(value: str | None) -> list[str]:
    names = available_skills()
    if not value:
        return names
    requested = [item.strip() for item in value.split(",") if item.strip()]
    unknown = [item for item in requested if item not in names]
    if unknown:
        raise SystemExit(f"Unknown skill(s): {', '.join(unknown)}. Use --list to see them.")
    return requested


def copy_skills(source_root: Path, dest_root: Path, names: list[str], force: bool) -> list[str]:
    copied: list[str] = []
    conflicts = [name for name in names if (dest_root / name).exists()]
    if conflicts and not force:
        raise SystemExit(
            "Refusing to overwrite existing skill(s): "
            + ", ".join(conflicts)
            + ". Re-run with --force to replace them."
        )
    dest_root.mkdir(parents=True, exist_ok=True)
    for name in names:
        source = source_root / name
        destination = dest_root / name
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(
            source,
            destination,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
        copied.append(name)
    return copied


def install_hooks(target: Path, dest_skills: Path) -> Path:
    hooks_path = target / ".cursor" / "hooks.json"
    hooks_path.parent.mkdir(parents=True, exist_ok=True)

    data: dict = {}
    if hooks_path.is_file():
        try:
            data = json.loads(hooks_path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"{hooks_path} is not valid JSON: {exc}")

    data.setdefault("version", 1)
    hooks = data.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise SystemExit(f"{hooks_path}: `hooks` must be an object.")

    hook_script = dest_skills / "ticket-index" / "hooks" / "ticket-index-sync.py"
    relative = hook_script.relative_to(target).as_posix()
    commands = {
        "afterShellExecution": f"python {relative} after-shell",
        "afterFileEdit": f"python {relative} after-file-edit",
    }

    for event, command in commands.items():
        entries = hooks.setdefault(event, [])
        if not isinstance(entries, list):
            raise SystemExit(f"{hooks_path}: `hooks.{event}` must be an array.")
        if not any(
            isinstance(entry, dict) and entry.get("command") == command for entry in entries
        ):
            entries.append({"command": command})

    hooks_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return hooks_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", help="Repository root to install into")
    parser.add_argument(
        "--agent",
        choices=sorted(AGENT_DIRS),
        default="cursor",
        help="Agent preset that decides the skills directory (default: cursor)",
    )
    parser.add_argument(
        "--skills-dir",
        help="Skills directory relative to the target, overriding --agent "
        "(for example .codex/skills)",
    )
    parser.add_argument("--skills", help="Comma-separated skill names (default: all)")
    parser.add_argument("--force", action="store_true", help="Replace existing skill folders")
    parser.add_argument(
        "--install-hooks",
        action="store_true",
        help="Merge the ticket-index hook into <target>/.cursor/hooks.json",
    )
    parser.add_argument("--list", action="store_true", help="List bundled skills and exit")
    args = parser.parse_args()

    if args.list:
        for name in available_skills():
            print(name)
        return 0

    if not args.target:
        parser.error("--target is required unless --list is used")

    target = Path(args.target).expanduser().resolve()
    if not target.is_dir():
        raise SystemExit(f"Target directory does not exist: {target}")

    relative_dir = args.skills_dir or AGENT_DIRS[args.agent]
    dest_skills = (target / relative_dir).resolve()
    try:
        dest_skills.relative_to(target)
    except ValueError:
        raise SystemExit("--skills-dir must stay inside the target repository.")

    names = parse_skills(args.skills)

    if args.install_hooks and dest_skills != (target / ".cursor" / "skills").resolve():
        raise SystemExit(
            "Hook installation requires the Cursor layout, .cursor/skills. "
            "Re-run with --agent cursor (default) to install the hook."
        )

    copied = copy_skills(SKILLS_ROOT, dest_skills, names, args.force)

    print(f"Installed {len(copied)} skill(s) into {dest_skills}")
    for name in copied:
        print(f"  - {name}")

    if args.install_hooks:
        hooks_path = install_hooks(target, dest_skills)
        print(f"Merged ticket-index hooks into {hooks_path}")
        print("Restart Cursor (or start a new session) so it loads the hook config.")

    print()
    print("Next steps:")
    print("  1. Run /setup-ticket-workflow in the repository.")
    print("  2. Add tickets under the tickets directory and render the index:")
    script = (dest_skills / "ticket-index" / "scripts" / "ticket_index.py").relative_to(target)
    print(f"     python {script.as_posix()} render")
    print(f"     python {script.as_posix()} check")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
