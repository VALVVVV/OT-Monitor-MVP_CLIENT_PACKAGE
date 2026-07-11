#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
import shutil
import sys

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
BACKUPS_DIR = BASE_DIR / "backups"
TARGET_FILES = [
    "documents.json",
    "check_log.json",
    "decisions.json",
    "review_comments.json",
]


def clear_payload(value):
    if isinstance(value, list):
        return []
    if isinstance(value, dict):
        return {key: clear_payload(inner) for key, inner in value.items()}
    return value


def load_or_default(path: Path):
    if not path.exists():
        return []
    raw = path.read_text(encoding="utf-8-sig")
    if not raw.strip():
        return []
    payload = json.loads(raw)
    if isinstance(payload, list):
        return []
    if isinstance(payload, dict):
        return clear_payload(payload)
    return []


def write_json_no_bom(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    path.write_text(text, encoding="utf-8", newline="")


def create_backup_dir() -> Path:
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_dir = BACKUPS_DIR / f"demo_reset_{timestamp}" / "data"
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


def main() -> int:
    backup_dir = create_backup_dir()
    print(f"Backup directory: {backup_dir}")

    for name in TARGET_FILES:
        source_path = DATA_DIR / name
        backup_path = backup_dir / name
        if source_path.exists():
            shutil.copy2(source_path, backup_path)
            print(f"Backed up: {source_path}")
        else:
            print(f"Missing before reset, will create: {source_path}")

        payload = load_or_default(source_path)
        write_json_no_bom(source_path, payload)
        print(f"Reset: {source_path}")

    print("Demo data reset complete.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"Reset failed: {type(error).__name__}: {error}", file=sys.stderr)
        raise
