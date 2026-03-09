# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for 微头条爬虫 (weitoutiao).

Usage:
    pyinstaller weitoutiao.spec --noconfirm

macOS  → dist/weitoutiao.app  (bundle with dmg via create-dmg)
Windows → dist/weitoutiao.exe  (single-file executable)
"""

import sys
from pathlib import Path

ROOT = Path(SPECPATH)  # noqa: F821 – injected by PyInstaller

IS_MACOS = sys.platform == "darwin"
IS_WINDOWS = sys.platform == "win32"

# ── Data files bundled into the executable ─────────────────────────────
# Tuple format: (source_glob_or_dir, dest_path_inside_bundle)
datas = [
    # Frontend build artifacts
    (str(ROOT / "frontend" / "dist"), "frontend/dist"),
]

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
    runtime_hooks=[],
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
