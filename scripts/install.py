#!/usr/bin/env python3
"""Install the bundled skills into a repository.

Copies the skill folders to the directory your agent reads (``.cursor/skills`` for
Cursor, ``.claude/skills`` for Claude Code, or any path via ``--skills-dir``). Optionally
merges the ticket-index auto-sync hook into ``.cursor/hooks.json``. Also configures the
generated ticket index to merge without conflict (``.gitattributes`` plus the ``ours``
merge driver), and, with ``--install-git-hooks``, writes ``post-merge`` and
``post-checkout`` git hooks that re-render the index after every merge and branch switch.

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

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None

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


def read_output_dir(target: Path) -> str | None:
    """Return the generated-index output dir relative to ``target``, if configured.

    Reads ``settings.output_dir`` from ``<target>/ticket-index.toml``. Absent
    config, parse errors, and absolute output dirs yield ``None`` so callers
    fall back to the kit default ``docs/tickets``.
    """
    config = target / "ticket-index.toml"
    if tomllib is None or not config.is_file():
        return None
    try:
        raw = tomllib.loads(config.read_text(encoding="utf-8-sig"))
    except (OSError, tomllib.TOMLDecodeError):
        return None
    settings = raw.get("settings") if isinstance(raw, dict) else None
    if not isinstance(settings, dict):
        return None
    output = settings.get("output_dir")
    if not isinstance(output, str) or Path(output).is_absolute():
        return None
    return output.strip().replace("\\", "/").strip("/")


def git_config_path(target: Path) -> Path | None:
    """Path to the git config backing ``target``'s repository, if any.

    Handles regular clones (``.git/`` directory), worktrees, and submodules
    (``.git`` file with a ``gitdir:`` pointer). Returns ``None`` when the
    target is not a git repository, so merge-driver setup is skipped quietly.
    """
    dot_git = target / ".git"
    if dot_git.is_dir():
        return dot_git / "config"
    if dot_git.is_file():
        for line in dot_git.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("gitdir:"):
                gitdir = Path(stripped.partition(":")[2].strip())
                if not gitdir.is_absolute():
                    gitdir = target / gitdir
                return gitdir / "config"
    return None


def install_git_merge(target: Path) -> str:
    """Make generated index files merge without conflicts.

    Two steps: (1) add ``<output>/** merge=ours`` to ``<target>/.gitattributes``,
    and (2) when the target is a git repository, register the matching ``ours``
    merge driver in its git config. git then keeps the branch-local index during
    a merge or rebase; the integrator runs ``render`` once afterwards so the
    merged index carries both sides. ``render`` remains the source of truth for
    the files; this only removes them from the conflict surface.

    Best-effort: a write failure returns a warning instead of aborting the
    install. Returns a human-readable status line.
    """
    output = read_output_dir(target) or "docs/tickets"
    rule = f"{output}/** merge=ours"

    attrs_path = target / ".gitattributes"
    try:
        existing = attrs_path.read_text(encoding="utf-8") if attrs_path.is_file() else ""
        if rule not in existing.splitlines():
            prefix = "" if not existing or existing.endswith("\n") else "\n"
            with attrs_path.open("a", encoding="utf-8", newline="\n") as stream:
                stream.write(prefix + rule + "\n")
    except OSError as exc:
        return f"warning: could not write {attrs_path}: {exc}"

    config_path = git_config_path(target)
    if config_path is None:
        return (
            f"configured {rule} in .gitattributes ({target.name} is not a git "
            "repository; merge driver not registered)"
        )

    driver_header = '[merge "ours"]'
    try:
        existing = config_path.read_text(encoding="utf-8") if config_path.is_file() else ""
        if driver_header not in existing:
            prefix = "" if not existing or existing.endswith("\n") else "\n"
            with config_path.open("a", encoding="utf-8", newline="\n") as stream:
                stream.write(f"{prefix}{driver_header}\n\tdriver = true\n")
    except OSError as exc:
        return f"warning: could not write {config_path}: {exc}"

    return (
        f"configured {rule} with the `ours` merge driver: merge or rebase keeps "
        "the branch-local index, then run `render` once on the integration branch"
    )


# A POSIX shell hook: git runs hooks with sh even on Windows, and the working
# directory is the top of the worktree. It must never block the git operation,
# so failures are swallowed and the exit code is always 0.
GIT_HOOK_TEMPLATE = """#!/bin/sh
# Managed by the ticket-index installer. Keeps the generated index current after
# merges and branch switches. Render is idempotent and fast; failures never block git.
root="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
script="$root/{skills_rel}/ticket-index/scripts/ticket_index.py"
[ -f "$script" ] || exit 0
# post-checkout receives <old> <new> <flag>; a flag other than 1 means a
# single-file checkout, which must not trigger a render. post-merge takes no args.
if [ "$#" -eq 3 ] && [ "$3" != "1" ]; then
  exit 0
fi
python3 "$script" render >/dev/null 2>&1 || python "$script" render >/dev/null 2>&1 || true
exit 0
"""
GIT_HOOK_MARKER = "# Managed by the ticket-index installer"


def git_hooks_dir(target: Path) -> Path | None:
    """Hooks directory backing ``target``'s repository, if any."""
    dot_git = target / ".git"
    if dot_git.is_dir():
        return dot_git / "hooks"
    if dot_git.is_file():
        for line in dot_git.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("gitdir:"):
                gitdir = Path(stripped.partition(":")[2].strip())
                if not gitdir.is_absolute():
                    gitdir = target / gitdir
                return gitdir / "hooks"
    return None


def install_git_hooks(target: Path, dest_skills: Path) -> str:
    """Install ``post-merge`` and ``post-checkout`` hooks that re-render the index.

    The hooks are best-effort conveniences: they keep the index fresh after a
    merge or a branch switch, which is exactly when a stale index hides other
    people's work. They never overwrite a user's existing hook (one without the
    installer's marker) and never fail the git operation. Returns a status line.
    """
    hooks_dir = git_hooks_dir(target)
    if hooks_dir is None:
        return (
            f"skipped git hooks ({target.name} is not a git repository; "
            "re-run with --install-git-hooks inside a clone)"
        )

    skills_rel = dest_skills.relative_to(target).as_posix()
    content = GIT_HOOK_TEMPLATE.format(skills_rel=skills_rel)
    try:
        hooks_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return f"warning: could not create {hooks_dir}: {exc}"
    installed: list[str] = []
    skipped: list[str] = []
    for name in ("post-merge", "post-checkout"):
        hook_path = hooks_dir / name
        try:
            existing = hook_path.read_text(encoding="utf-8") if hook_path.is_file() else ""
        except OSError as exc:
            return f"warning: could not read {hook_path}: {exc}"
        if existing and GIT_HOOK_MARKER not in existing:
            skipped.append(name)
            continue
        if existing == content:
            installed.append(name)
            continue
        try:
            hook_path.write_text(content, encoding="utf-8", newline="\n")
            try:
                os.chmod(hook_path, 0o755)
            except OSError:
                pass
            installed.append(name)
        except OSError as exc:
            return f"warning: could not write {hook_path}: {exc}"

    message = "installed git hooks: " + (", ".join(installed) or "(none)")
    if skipped:
        message += "; kept existing hooks: " + ", ".join(skipped)
    return message


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
    parser.add_argument(
        "--install-git-hooks",
        action="store_true",
        help="Write post-merge and post-checkout hooks that re-render the index",
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
    print(install_git_merge(target))
    if args.install_git_hooks:
        print(install_git_hooks(target, dest_skills))

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
