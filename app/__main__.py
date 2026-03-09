"""Entry point for PyInstaller and `python -m app`."""
from __future__ import annotations

import sys

# When running as a PyInstaller bundle, __file__ is inside _MEIPASS.
# The paths module uses Path(__file__).parent.parent to find ROOT_DIR,
# which points to _MEIPASS – that is where frontend/dist is copied.
# User data (data/db, data/logs, data/images) is resolved relative to
# the executable's real location to keep it persistent across updates.
if getattr(sys, "frozen", False):
    import os
    from pathlib import Path

    # Override DATA_DIR to sit next to the executable (persistent user data)
    _exe_dir = Path(sys.executable).parent
    _data_dir = _exe_dir / "data"

    import app.paths as _paths  # noqa: E402

    _paths.DATA_DIR = _data_dir
    _paths.LOG_DIR = _data_dir / "logs"
    _paths.DB_DIR = _data_dir / "db"
    _paths.IMAGES_DIR = _data_dir / "images"
    _paths.SETTINGS_DB_FILE = _paths.DB_DIR / "settings.sqlite3"
    # frontend/dist is bundled inside _MEIPASS
    _paths.FRONTEND_DIST_DIR = Path(sys._MEIPASS) / "frontend" / "dist"  # type: ignore[attr-defined]
    _paths.FRONTEND_INDEX_FILE = _paths.FRONTEND_DIST_DIR / "index.html"

from app.main import main  # noqa: E402

raise SystemExit(main())
