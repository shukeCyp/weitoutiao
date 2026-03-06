from __future__ import annotations

import sys

import webview

from .api import Api
from .db import init_db
from .logging_setup import configure_logging
from .paths import FRONTEND_INDEX_FILE

WINDOW_TITLE = "微头条爬虫"


def resolve_frontend_url() -> str:
    if not FRONTEND_INDEX_FILE.exists():
        raise FileNotFoundError(
            "Missing frontend build artifact: "
            f"{FRONTEND_INDEX_FILE}. Please run ./run.sh to build frontend first."
        )
    return FRONTEND_INDEX_FILE.as_uri()


def main() -> int:
    logger = configure_logging()
    logger.info("Starting desktop application")

    try:
        init_db()
        logger.info("Database initialized")

        url = resolve_frontend_url()
        logger.info("Frontend asset resolved: %s", FRONTEND_INDEX_FILE)
    except FileNotFoundError as exc:
        logger.error(str(exc))
        print(str(exc), file=sys.stderr)
        return 1
    except Exception:
        logger.exception("Application initialization failed")
        return 1

    api = Api()
    logger.info("Creating pywebview window")
    webview.create_window(WINDOW_TITLE, url=url, js_api=api, width=1180, height=760)
    logger.info("Starting pywebview event loop")
    webview.start()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
