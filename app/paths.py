from __future__ import annotations

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = ROOT_DIR / "frontend"
FRONTEND_DIST_DIR = FRONTEND_DIR / "dist"
FRONTEND_INDEX_FILE = FRONTEND_DIST_DIR / "index.html"

DATA_DIR = ROOT_DIR / "data"
LOG_DIR = DATA_DIR / "logs"
DB_DIR = DATA_DIR / "db"
SETTINGS_DB_FILE = DB_DIR / "settings.sqlite3"
