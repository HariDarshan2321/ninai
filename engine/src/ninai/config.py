from __future__ import annotations

import os
from pathlib import Path


def data_dir() -> Path:
    configured = os.getenv("NINAI_DATA_DIR")
    path = Path(configured).expanduser() if configured else Path.home() / ".ninai"
    path.mkdir(parents=True, exist_ok=True)
    return path


def database_path() -> Path:
    return data_dir() / "ninai.sqlite3"


def client_id() -> str:
    return os.getenv("NINAI_CLIENT_ID", "claude-code").strip() or "claude-code"
