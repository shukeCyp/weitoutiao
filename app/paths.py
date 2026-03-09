from __future__ import annotations

import sys
from pathlib import Path

# PyInstaller 单文件 EXE 时，__file__ 在临时解压目录（sys._MEIPASS）
# 用户数据（DB / 日志 / 图片）必须放在 EXE 旁边，而不是临时目录
if getattr(sys, "frozen", False):
    # 运行在打包后的 EXE 里：数据目录紧邻 EXE
    _APP_ROOT = Path(sys.executable).resolve().parent
    ROOT_DIR = _APP_ROOT
    FRONTEND_DIR = Path(sys._MEIPASS) / "frontend"  # type: ignore[attr-defined]
else:
    ROOT_DIR = Path(__file__).resolve().parent.parent
    FRONTEND_DIR = ROOT_DIR / "frontend"

FRONTEND_DIST_DIR = FRONTEND_DIR / "dist"
FRONTEND_INDEX_FILE = FRONTEND_DIST_DIR / "index.html"

DATA_DIR = ROOT_DIR / "data"
LOG_DIR = DATA_DIR / "logs"
DB_DIR = DATA_DIR / "db"
IMAGES_DIR = DATA_DIR / "images"
SETTINGS_DB_FILE = DB_DIR / "settings.sqlite3"
