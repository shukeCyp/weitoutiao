from __future__ import annotations

import os
import subprocess
from pathlib import Path

from .db import count_settings, get_setting, set_setting
from .paths import DB_DIR, LOG_DIR, SETTINGS_DB_FILE


def _open_folder(path: Path) -> bool:
    path.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.Popen(["open", str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False


class Api:
    """API surface for frontend/backend integration."""

    def ping(self) -> str:
        return "pong"

    def get_setting(self, key: str) -> str | None:
        return get_setting(key)

    def set_setting(self, key: str, value: str) -> bool:
        return set_setting(key, value)

    def get_monitoring_status(self) -> dict[str, str | int]:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        DB_DIR.mkdir(parents=True, exist_ok=True)

        log_files = [p for p in LOG_DIR.glob("app.log*") if p.is_file()]
        log_size = sum(p.stat().st_size for p in log_files)
        db_size = SETTINGS_DB_FILE.stat().st_size if SETTINGS_DB_FILE.exists() else 0

        return {
            "logDir": str(LOG_DIR),
            "dbFile": str(SETTINGS_DB_FILE),
            "logFiles": len(log_files),
            "logSizeBytes": log_size,
            "dbSizeBytes": db_size,
            "settingCount": count_settings(),
        }

    def open_logs_folder(self) -> bool:
        return _open_folder(LOG_DIR)

    def open_db_folder(self) -> bool:
        return _open_folder(DB_DIR)

    def clear_logs(self) -> bool:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        removed = False

        for file in LOG_DIR.glob("app.log*"):
            if not file.is_file():
                continue
            try:
                os.remove(file)
                removed = True
            except OSError:
                continue

        return removed
