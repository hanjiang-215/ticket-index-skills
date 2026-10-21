#!/usr/bin/env python3
"""Keep a ticket index in sync after ticket mutations.

Register this script for two Cursor hooks:

    afterShellExecution  ->  argument ``after-shell``
    afterFileEdit        ->  argument ``after-file-edit``

It renders only when the event touches the configured tickets directory, the
config file, or a ticket-CLI mutation command. Failures are reported on stderr
and never block the command or the edit.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    raise SystemExit(0)

SKILL_ROOT = Path(__file__).resolve().parents[1]
INDEX_SCRIPT = SKILL_ROOT / "scripts" / "ticket_index.py"

FER_WORD = re.compile(r"\bfer(?:\.exe)?\b", re.IGNORECASE)
FER_MUTATION = re.compile(
    r"\b(?:create|start|close|status|reopen|dep|undep|link|unlink|edit|add-note)\b",
    re.IGNORECASE,
)


def find_config() -> Path | None:
    explicit = os.environ.get("TICKET_INDEX_CONFIG")
    if explicit:
        path = Path(explicit)
        return path.resolve() if path.is_file() else None
    for base in (Path.cwd().resolve(), *Path.cwd().resolve().parents):
        for relative in ("ticket-index.toml", "docs/tickets/index.toml"):
            candidate = base / relative
            if candidate.is_file():
                return candidate.resolve()
    return None


def load_paths(config_path: Path) -> tuple[Path, Path, Path]:
    root = config_path.parent
    if (
        config_path.name == "index.toml"
        and config_path.parent.name == "tickets"
        and config_path.parent.parent.name == "docs"
    ):
        root = config_path.parent.parent.parent
    try:
        raw = tomllib.loads(config_path.read_text(encoding="utf-8-sig"))
    except (OSError, tomllib.TOMLDecodeError):
        raw = {}
    settings = raw.get("settings", {}) if isinstance(raw, dict) else {}
    tickets_value = settings.get("tickets_dir", ".tickets")
    output_value = settings.get("output_dir")
    tickets_dir = (root / str(tickets_value)).resolve()
    if output_value:
        output_dir = (root / str(output_value)).resolve()
    elif config_path.parent.name == "tickets":
        output_dir = config_path.parent
    else:
        output_dir = (root / "docs/tickets").resolve()
    return root, tickets_dir, output_dir


def touches_tickets(event: str, payload: dict, config_path: Path) -> bool:
    if event == "after-shell":
        command = str(payload.get("command", ""))
        return bool(FER_WORD.search(command) and FER_MUTATION.search(command))
    if event == "after-file-edit":
        _, tickets_dir, _ = load_paths(config_path)
        try:
            edited = Path(str(payload.get("file_path", ""))).resolve()
        except OSError:
            return False
        try:
            config_resolved = config_path.resolve()
        except OSError:
            config_resolved = config_path
        if edited == config_resolved:
            return True
        try:
            return edited.is_relative_to(tickets_dir) and edited.suffix == ".md"
        except ValueError:
            return False
    return False


def render(root: Path, config_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(INDEX_SCRIPT), "render", "--config", str(config_path)],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        print(f"ticket-index auto-sync failed: {detail}", file=sys.stderr)


def main() -> int:
    event = sys.argv[1] if len(sys.argv) > 1 else ""
    try:
        raw = sys.stdin.buffer.read() if hasattr(sys.stdin, "buffer") else sys.stdin.read().encode()
        payload = json.loads(raw.decode("utf-8-sig", errors="replace"))
    except (json.JSONDecodeError, ValueError, UnicodeError):
        return 0

    config_path = find_config()
    if config_path is None or not INDEX_SCRIPT.is_file():
        return 0
    if not touches_tickets(event, payload, config_path):
        return 0

    root = config_path.parent
    if (
        config_path.name == "index.toml"
        and config_path.parent.name == "tickets"
        and config_path.parent.parent.name == "docs"
    ):
        root = config_path.parent.parent.parent
    render(root, config_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
