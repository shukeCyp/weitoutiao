"""
PyInstaller runtime hook for Playwright.

This file is executed by PyInstaller before any app code runs.
It sets PLAYWRIGHT_BROWSERS_PATH to the bundled ms-playwright directory
so Playwright can find Chromium inside the packaged app.
"""
import os
import sys

if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    _bundled_browsers = os.path.join(sys._MEIPASS, "ms-playwright")
    os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", _bundled_browsers)
