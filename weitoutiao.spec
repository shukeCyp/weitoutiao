# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for 微头条爬虫 (weitoutiao).

Usage:
    # 打包前先设置 PLAYWRIGHT_BROWSERS_PATH 并安装浏览器：
    #   export PLAYWRIGHT_BROWSERS_PATH=./playwright_browsers
    #   playwright install chromium
    pyinstaller weitoutiao.spec --noconfirm

macOS  → dist/weitoutiao.app  (bundle with dmg via create-dmg)
Windows → dist/weitoutiao.exe  (single-file executable)
"""

import os
import sys
from pathlib import Path

ROOT = Path(SPECPATH)  # noqa: F821 – injected by PyInstaller

IS_MACOS = sys.platform == "darwin"
IS_WINDOWS = sys.platform == "win32"

# ── Playwright browsers directory ──────────────────────────────────────
# 优先读取环境变量 PLAYWRIGHT_BROWSERS_PATH（CI 中设置好的固定路径）
# 若未设置则尝试各平台默认位置
def _find_playwright_browsers() -> str | None:
    env_path = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "").strip()
    if env_path and Path(env_path).is_dir():
        return env_path

    if IS_MACOS:
        candidates = [
            Path.home() / "Library" / "Caches" / "ms-playwright",
            Path.home() / ".cache" / "ms-playwright",
        ]
    elif IS_WINDOWS:
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        candidates = [Path(local_app_data) / "ms-playwright"]
    else:
        candidates = [Path.home() / ".cache" / "ms-playwright"]

    for p in candidates:
        if p.is_dir():
            return str(p)
    return None


_playwright_browsers_dir = _find_playwright_browsers()
if _playwright_browsers_dir:
    print(f"[spec] Bundling Playwright browsers from: {_playwright_browsers_dir}")
else:
    print(
        "[spec] WARNING: Playwright browsers not found. "
        "Set PLAYWRIGHT_BROWSERS_PATH and run 'playwright install chromium' before packaging.",
        file=sys.stderr,
    )

# ── Data files bundled into the executable ─────────────────────────────
# Tuple format: (source_glob_or_dir, dest_path_inside_bundle)
datas = [
    # Frontend build artifacts
    (str(ROOT / "frontend" / "dist"), "frontend/dist"),
]

# 把 Playwright 浏览器目录整体打包进来，运行时钩子会设置 PLAYWRIGHT_BROWSERS_PATH
if _playwright_browsers_dir:
    datas.append((_playwright_browsers_dir, "ms-playwright"))

# ── Hidden imports needed at runtime ──────────────────────────────────
hidden_imports = [
    "webview",
    "webview.platforms.cocoa",   # macOS
    "webview.platforms.winforms",  # Windows
    "peewee",
    "docx",
    "docx.oxml",
    "docx.oxml.ns",
    "docx.shared",
    "playwright",
    "playwright.sync_api",
    "pkg_resources",
    "pkg_resources.extern",
]

# ── Analysis ───────────────────────────────────────────────────────────
a = Analysis(
    [str(ROOT / "app" / "__main__.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[str(ROOT / "playwright_runtime_hook.py")],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)  # noqa: F821

# ── Platform-specific packaging ────────────────────────────────────────
if IS_MACOS:
    exe = EXE(  # noqa: F821
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name="weitoutiao",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,
        disable_windowed_traceback=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )
    coll = COLLECT(  # noqa: F821
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name="weitoutiao",
    )
    app = BUNDLE(  # noqa: F821
        coll,
        name="weitoutiao.app",
        icon=None,
        bundle_identifier="com.weitoutiao.app",
        info_plist={
            "CFBundleDisplayName": "微头条爬虫",
            "CFBundleVersion": "1.0.0",
            "CFBundleShortVersionString": "1.0.0",
            "NSHighResolutionCapable": True,
        },
    )
else:
    # Windows – single-file exe
    exe = EXE(  # noqa: F821
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        [],
        name="weitoutiao",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,
        disable_windowed_traceback=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )
