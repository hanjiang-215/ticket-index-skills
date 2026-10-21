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
import os
import shutil
import sys
import tempfile
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


def copy_skills(
    source_root: Path,
    dest_root: Path,
    names: list[str],
    force: bool,
    hooks: tuple[Path, str] | None = None,
) -> list[str]:
    conflicts = [name for name in names if (dest_root / name).exists()]
    if conflicts and not force:
        raise SystemExit(
            "Refusing to overwrite existing skill(s): "
            + ", ".join(conflicts)
            + ". Re-run with --force to replace them."
        )

    dest_root.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="ticket-index-install-", dir=dest_root.parent) as temp:
        transaction = Path(temp)
        staged_skills = transaction / "skills"
        staged_skills.mkdir()
        backups = transaction / "backups"
        backups.mkdir()
        for name in names:
            shutil.copytree(
                source_root / name,
                staged_skills / name,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )

        staged_hook: Path | None = None
        if hooks is not None:
            hooks_path, content = hooks
            hooks_path.parent.mkdir(parents=True, exist_ok=True)
            staged_hook = transaction / "hooks.json"
            staged_hook.write_text(content, encoding="utf-8")

        dest_root.mkdir(parents=True, exist_ok=True)
        committed: list[tuple[Path, Path | None]] = []
        try:
            for name in names:
                destination = dest_root / name
                backup = backups / name if destination.exists() else None
                if backup is not None:
                    os.replace(destination, backup)
                try:
                    os.replace(staged_skills / name, destination)
                except OSError:
                    if backup is not None:
                        os.replace(backup, destination)
                    raise
                committed.append((destination, backup))

            if hooks is not None and staged_hook is not None:
                os.replace(staged_hook, hooks[0])
        except BaseException:
            for destination, backup in reversed(committed):
                if destination.exists():
                    shutil.rmtree(destination)
                if backup is not None and backup.exists():
                    os.replace(backup, destination)
            raise

    return names


def prepare_hooks(target: Path, dest_skills: Path) -> tuple[Path, str]:
    hooks_path = target / ".cursor" / "hooks.json"
    data: dict = {}
    if hooks_path.is_file():
        try:
            data = json.loads(hooks_path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"{hooks_path} is not valid JSON: {exc}")
    if not isinstance(data, dict):
        raise SystemExit(f"{hooks_path}: top-level JSON value must be an object.")

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

    return hooks_path, json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def install_hooks(target: Path, dest_skills: Path) -> Path:
    hooks_path, content = prepare_hooks(target, dest_skills)
    hooks_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=hooks_path.parent, delete=False
    ) as stream:
        stream.write(content)
        staged = Path(stream.name)
    try:
        os.replace(staged, hooks_path)
    finally:
        staged.unlink(missing_ok=True)
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

    hook_update = prepare_hooks(target, dest_skills) if args.install_hooks else None
    copied = copy_skills(SKILLS_ROOT, dest_skills, names, args.force, hooks=hook_update)

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
