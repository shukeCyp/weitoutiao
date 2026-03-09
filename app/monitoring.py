from __future__ import annotations

import argparse
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from .db import (
    create_monitor_run,
    finish_monitor_run,
    get_benchmark_account_by_id,
    get_setting,
    persist_monitored_articles,
)

logger = logging.getLogger("weitoutiao.monitoring")

AUTOMATION_HEADLESS_KEY = "automation.headless"
AUTOMATION_WORKER_COUNT_KEY = "automation.worker_count"
DEFAULT_HEADLESS = True
DEFAULT_WORKER_COUNT = 1
MAX_WORKER_COUNT = 16
DEFAULT_MONITOR_URL = (
    "https://www.toutiao.com/c/user/token/"
    "Ciw1yhCBHf_GqdVq-hND0XUd9AjJ5oZ-tVNEIY6EdeC1bmaeUWt1W_LAGtZmKRpJCjwAAAAAAAAAAAAA"
    "UCfd_QeHzLFODRGp79H24P23IDVsfW8THC6UPIkunDy-gLI2xjoUyeZrWr8TnwTKZskQp7mLDhjDxYPqBCIBA_AK6jU="
    "/?source=m_redirect"
)
TARGET_FEED_PATH = "/api/pc/list/user/feed"
TARGET_FEED_CATEGORY = "pc_profile_ugc"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
)
MAX_SCROLL_ROUNDS = 12
MAX_NO_PROGRESS_ROUNDS = 3
MAX_SAME_CURSOR_ROUNDS = 2
PAGE_BOOTSTRAP_TIMEOUT_MS = 60000
PAGE_IDLE_WAIT_MS = 4000
TAB_CLICK_WAIT_MS = 3000
SCROLL_WAIT_MS = 2500
NETWORK_SETTLE_TIMEOUT_MS = 4000


@dataclass(slots=True)
class AutomationSettings:
    headless: bool
    worker_count: int


@dataclass(slots=True)
class MonitoringThresholds:
    min_play_count: int = 0
    min_digg_count: int = 0
    min_forward_count: int = 0


@dataclass(slots=True)
class FeedCapture:
    request_url: str
    payload_text: str
    payload_json: dict[str, Any] | list[Any] | None


@dataclass(slots=True)
class BatchMonitorAccountResult:
    benchmark_account_id: int
    benchmark_account_url: str
    status: str
    saved_count: int
    article_count: int
    filtered_article_count: int
    capture_count: int
    warning: str | None
    error: str | None
    monitor_run_id: int | None
    articles: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "benchmarkAccountId": self.benchmark_account_id,
            "benchmarkAccountUrl": self.benchmark_account_url,
            "status": self.status,
            "savedCount": self.saved_count,
            "articleCount": self.article_count,
            "filteredArticleCount": self.filtered_article_count,
            "captureCount": self.capture_count,
            "warning": self.warning,
            "error": self.error,
            "monitorRunId": self.monitor_run_id,
            "articles": self.articles,
        }


@dataclass(slots=True)
class NormalizedArticle:
    id: str | None
    group_id: str | None
    item_id: str | None
    cell_type: str | None
    title: str | None
    content: str | None
    publish_time: str | None
    source: str | None
    media_name: str | None
    display_url: str | None
    raw: dict[str, Any]


class AccountMonitor:
    def __init__(
        self,
        url: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        single_capture: bool = False,
        thresholds: MonitoringThresholds | None = None,
    ) -> None:
        self.url = url.strip()
        self.start_time = start_time
        self.end_time = end_time
        self.single_capture = single_capture
        self.thresholds = thresholds or MonitoringThresholds()
        self.settings = self._load_settings()

    def _parse_non_negative_int(self, value: str | None, default: int = 0) -> int:
        try:
            parsed = int(value) if value is not None else default
        except ValueError:
            parsed = default
        return max(0, parsed)

    def _load_settings(self) -> AutomationSettings:
        headless_raw = get_setting(AUTOMATION_HEADLESS_KEY)
        worker_count_raw = get_setting(AUTOMATION_WORKER_COUNT_KEY)

        headless = DEFAULT_HEADLESS if headless_raw is None else headless_raw.lower() == "true"

        try:
            worker_count = int(worker_count_raw) if worker_count_raw is not None else DEFAULT_WORKER_COUNT
        except ValueError:
            worker_count = DEFAULT_WORKER_COUNT

        worker_count = max(1, min(worker_count, MAX_WORKER_COUNT))
        return AutomationSettings(
            headless=headless,
            worker_count=worker_count,
        )

    def _normalize_threshold_value(self, value: int | str | None) -> int:
        if value is None:
            return 0
        try:
            return max(0, int(value))
        except (TypeError, ValueError):
            return 0

    def _validate(self) -> None:
        if not self.url:
            raise ValueError("监控地址不能为空。")

        if not self.url.startswith(("http://", "https://")):
            raise ValueError("监控地址必须是有效的 http/https 链接。")

    def _serialize_datetime(self, value: datetime | None) -> str | None:
        return value.isoformat() if value else None

    def _extract_payload(self, payload_text: str) -> dict[str, Any] | list[Any] | None:
        if not payload_text:
            return None

        try:
            return json.loads(payload_text)
        except json.JSONDecodeError:
            return None

    def _is_target_feed_response(self, response_url: str) -> bool:
        parsed = urlparse(response_url)
        if parsed.path != TARGET_FEED_PATH:
            return False

        query = parse_qs(parsed.query)
        category = query.get("category", [""])[0]
        return category == TARGET_FEED_CATEGORY

    def _extract_feed_items(self, payload: dict[str, Any] | list[Any] | None) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]

        if not isinstance(payload, dict):
            return []

        data = payload.get("data")
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]

        return []

    def _extract_item_timestamp(self, item: dict[str, Any]) -> datetime | None:
        candidate_keys = [
            "publish_time",
            "behot_time",
            "create_time",
            "datetime",
            "time",
        ]

        for key in candidate_keys:
            value = item.get(key)
            if isinstance(value, (int, float)):
                try:
                    return datetime.fromtimestamp(value)
                except (OSError, OverflowError, ValueError):
                    continue
            if isinstance(value, str) and value.strip():
                try:
                    return datetime.fromisoformat(value.strip())
                except ValueError:
                    continue

        return None

    def _is_in_range(self, item_time: datetime | None) -> bool:
        if item_time is None:
            return self.start_time is None and self.end_time is None

        if self.start_time is not None and item_time < self.start_time:
            return False

        if self.end_time is not None and item_time > self.end_time:
            return False

        return True

    def _filter_items(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if self.start_time is None and self.end_time is None:
            return items

        filtered: list[dict[str, Any]] = []
        for item in items:
            item_time = self._extract_item_timestamp(item)
            if self._is_in_range(item_time):
                filtered.append(item)
        return filtered

    def _should_continue_scrolling(self, items: list[dict[str, Any]], filtered_items: list[dict[str, Any]]) -> bool:
        if self.start_time is None and self.end_time is None:
            return bool(items)

        if filtered_items:
            return False

        known_times = [self._extract_item_timestamp(item) for item in items]
        known_times = [item_time for item_time in known_times if item_time is not None]
        if not known_times:
            return True

        oldest_time = min(known_times)
        if self.start_time is not None and oldest_time > self.start_time:
            return True

        return False

    def _get_continue_reason(self, items: list[dict[str, Any]], filtered_items: list[dict[str, Any]]) -> tuple[bool, str]:
        if self.start_time is None and self.end_time is None:
            if items:
                return True, "has_items"
            return False, "empty_items"

        if filtered_items:
            return False, "time_range_satisfied"

        known_times = [self._extract_item_timestamp(item) for item in items]
        known_times = [item_time for item_time in known_times if item_time is not None]
        if not known_times:
            return True, "no_timestamps"

        oldest_time = min(known_times)
        if self.start_time is not None and oldest_time > self.start_time:
            return True, "need_older_items"

        return False, "oldest_reached_start"

    def _build_type_summary(self, payload: dict[str, Any] | list[Any] | None, items: list[dict[str, Any]]) -> dict[str, Any]:
        summary: dict[str, Any] = {
            "topLevelType": type(payload).__name__ if payload is not None else None,
            "itemCount": len(items),
        }

        if isinstance(payload, dict):
            summary["topLevelKeys"] = sorted(payload.keys())
            summary["dataType"] = type(payload.get("data")).__name__ if "data" in payload else None

        if items:
            summary["sampleItemKeys"] = sorted(items[0].keys())

        return summary

    def _stringify(self, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def _extract_text(self, item: dict[str, Any], *keys: str) -> str | None:
        for key in keys:
            value = item.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None

    def _extract_number(self, item: dict[str, Any], *keys: str) -> int | None:
        for key in keys:
            value = item.get(key)
            if isinstance(value, bool):
                continue
            if isinstance(value, (int, float)):
                return int(value)
            if isinstance(value, str) and value.strip().isdigit():
                return int(value.strip())
        return None

    def _normalize_article(self, item: dict[str, Any]) -> dict[str, Any]:
        publish_time = self._extract_item_timestamp(item)
        return {
            "id": self._stringify(item.get("id")),
            "groupId": self._stringify(item.get("group_id")),
            "itemId": self._stringify(item.get("item_id")),
            "cellType": self._stringify(item.get("cell_type")),
            "title": self._extract_text(item, "title"),
            "content": self._extract_text(item, "content", "abstract", "display_text"),
            "publishTime": publish_time.isoformat() if publish_time else None,
            "source": self._extract_text(item, "source"),
            "mediaName": self._extract_text(item, "media_name"),
            "displayUrl": self._extract_text(item, "display_url", "share_url", "source_url"),
            "playCount": self._extract_number(item, "play_count", "read_count", "view_count", "impression_count"),
            "diggCount": self._extract_number(item, "digg_count", "like_count", "up_count"),
            "commentCount": self._extract_number(item, "comment_count"),
            "forwardCount": self._extract_number(item, "forward_count", "share_count", "repin_count"),
            "buryCount": self._extract_number(item, "bury_count"),
            "raw": item,
        }

    def _passes_metric_threshold(self, value: int | None, threshold: int) -> bool:
        if threshold <= 0:
            return True
        if value is None:
            return False
        return value >= threshold

    def _passes_capture_thresholds(self, article: dict[str, Any]) -> bool:
        return (
            self._passes_metric_threshold(article.get("playCount"), self.thresholds.min_play_count)
            and self._passes_metric_threshold(article.get("diggCount"), self.thresholds.min_digg_count)
            and self._passes_metric_threshold(article.get("forwardCount"), self.thresholds.min_forward_count)
        )

    def _wait_for_optional_signing_runtime(self, page: Any) -> None:
        try:
            page.wait_for_function(
                """
                () => document.readyState === 'complete' || typeof window.byted_acrawler?.sign === 'function'
                """,
                timeout=PAGE_BOOTSTRAP_TIMEOUT_MS,
            )
        except PlaywrightTimeoutError:
            logger.info("页面签名运行时未在预期时间内出现，继续按浏览器交互方式采集。")

    def _capture_response(self, response: Any) -> FeedCapture:
        payload_text = response.text()
        return FeedCapture(
            request_url=response.url,
            payload_text=payload_text,
            payload_json=self._extract_payload(payload_text),
        )

    def _open_profile_page(self, page: Any, headless: bool) -> None:
        logger.info("开始加载头条账号页 url=%s headless=%s", self.url, headless)
        page.goto(self.url, wait_until="domcontentloaded", timeout=PAGE_BOOTSTRAP_TIMEOUT_MS)
        page.wait_for_timeout(PAGE_IDLE_WAIT_MS)
        self._wait_for_optional_signing_runtime(page)

    def _get_microheadline_locator(self, page: Any) -> Any:
        locator_candidates = [
            page.get_by_role("tab", name="微头条"),
            page.get_by_role("button", name="微头条"),
            page.get_by_role("link", name="微头条"),
            page.get_by_text("微头条", exact=True),
            page.locator("text=微头条"),
        ]

        for locator in locator_candidates:
            try:
                candidate = locator.first
                if candidate.count() == 0:
                    continue
                if candidate.is_visible(timeout=1500):
                    return candidate
            except Exception:
                continue

        raise RuntimeError("未找到“微头条”标签，无法切换到微头条列表。")

    def _open_microheadline_tab(self, page: Any) -> FeedCapture:
        locator = self._get_microheadline_locator(page)
        with page.expect_response(lambda response: self._is_target_feed_response(response.url), timeout=PAGE_BOOTSTRAP_TIMEOUT_MS) as response_info:
            locator.click(timeout=PAGE_BOOTSTRAP_TIMEOUT_MS)
        page.wait_for_timeout(TAB_CLICK_WAIT_MS)
        response = response_info.value
        return self._capture_response(response)

    def _extract_item_identity(self, item: dict[str, Any]) -> str | None:
        for key in ("id", "group_id", "item_id", "thread_id", "thread_id_str"):
            value = self._stringify(item.get(key))
            if value:
                return value
        return None

    def _extract_capture_item_ids(self, capture: FeedCapture) -> set[str]:
        items = self._extract_feed_items(capture.payload_json)
        return {item_id for item_id in (self._extract_item_identity(item) for item in items) if item_id}

    def _build_capture_signature(self, capture: FeedCapture) -> str:
        items = self._extract_feed_items(capture.payload_json)
        identities = [identity for identity in (self._extract_item_identity(item) for item in items[:5]) if identity]
        next_cursor = self._get_next_max_behot_time(capture.payload_json, items)
        return f"{len(items)}|{next_cursor}|{'|'.join(identities)}"

    def _get_next_max_behot_time(self, payload: dict[str, Any] | list[Any] | None, items: list[dict[str, Any]]) -> int | None:
        if isinstance(payload, dict):
            for key in ("next", "next_max_behot_time", "max_behot_time"):
                value = payload.get(key)
                if isinstance(value, (int, float)):
                    return int(value)
                if isinstance(value, str) and value.strip().isdigit():
                    return int(value.strip())

        timestamps: list[int] = []
        for item in items:
            for key in ("behot_time", "publish_time", "create_time"):
                value = item.get(key)
                if isinstance(value, (int, float)):
                    timestamps.append(int(value))
                    break
                if isinstance(value, str) and value.strip().isdigit():
                    timestamps.append(int(value.strip()))
                    break
        if timestamps:
            return min(timestamps)
        return None

    def _get_scroll_mode(self, no_progress_rounds: int, same_cursor_rounds: int) -> str:
        if same_cursor_rounds > 0 or no_progress_rounds >= 2:
            return "aggressive"
        if no_progress_rounds > 0:
            return "recovery"
        return "normal"

    def _trigger_feed_pagination(self, page: Any, round_index: int, no_progress_rounds: int, same_cursor_rounds: int) -> str:
        mode = self._get_scroll_mode(no_progress_rounds, same_cursor_rounds)
        logger.info(
            "触发浏览器滚动分页 round=%s no_progress_rounds=%s same_cursor_rounds=%s mode=%s",
            round_index + 1,
            no_progress_rounds,
            same_cursor_rounds,
            mode,
        )
        wheel_delta = 1600 + round_index * 120
        if mode == "recovery":
            wheel_delta += 500
        if mode == "aggressive":
            wheel_delta += 900

        page.mouse.wheel(0, wheel_delta)
        page.evaluate(
            """
            ({ mode }) => {
              const aggressive = mode === 'aggressive'
              const recovery = mode === 'recovery'
              window.scrollBy(0, window.innerHeight * (aggressive ? 2.5 : recovery ? 1.7 : 1.2))
              const elements = Array.from(document.querySelectorAll('*'))
              let best = null
              let bestScrollable = 0
              for (const element of elements) {
                if (!(element instanceof HTMLElement)) {
                  continue
                }
                const style = window.getComputedStyle(element)
                const scrollable = element.scrollHeight - element.clientHeight
                if (scrollable <= 200) {
                  continue
                }
                if (!['auto', 'scroll', 'overlay'].includes(style.overflowY)) {
                  continue
                }
                if (element.clientHeight < 160) {
                  continue
                }
                if (scrollable > bestScrollable) {
                  bestScrollable = scrollable
                  best = element
                }
              }
              if (best) {
                const ratio = aggressive ? 2.2 : recovery ? 1.6 : 1.1
                best.scrollTop = Math.min(best.scrollTop + best.clientHeight * ratio, best.scrollHeight)
                if (aggressive) {
                  best.scrollTop = Math.min(best.scrollTop + best.clientHeight * 0.9, best.scrollHeight)
                }
              }
              if (aggressive) {
                window.scrollTo(0, Math.min(document.body.scrollHeight, window.scrollY + window.innerHeight * 2))
              }
            }
            """,
            {"mode": mode},
        )
        page.wait_for_timeout(SCROLL_WAIT_MS)
        try:
            page.wait_for_load_state("networkidle", timeout=NETWORK_SETTLE_TIMEOUT_MS)
        except PlaywrightTimeoutError:
            logger.info("滚动后未进入 networkidle，继续检查已捕获响应。 round=%s mode=%s", round_index + 1, mode)
        return mode

    def _log_capture_decision(
        self,
        round_number: int,
        reason: str,
        capture: FeedCapture,
        item_count: int,
        next_cursor: int | None,
        new_item_count: int = 0,
    ) -> None:
        logger.info(
            "响应处理 round=%s reason=%s url=%s item_count=%s next_cursor=%s new_item_count=%s",
            round_number,
            reason,
            capture.request_url,
            item_count,
            next_cursor,
            new_item_count,
        )

    def _collect_feed_captures_with_browser(self, headless: bool) -> list[FeedCapture]:
        captures: list[FeedCapture] = []
        pending_captures: list[FeedCapture] = []
        pending_index = 0
        stop_reason: str | None = None

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=headless)
            context = browser.new_context(user_agent=DEFAULT_USER_AGENT, locale="zh-CN")
            page = context.new_page()

            def handle_response(response: Any) -> None:
                if not self._is_target_feed_response(response.url):
                    return
                try:
                    pending_captures.append(self._capture_response(response))
                except Exception as exc:  # noqa: BLE001
                    logger.warning("读取目标响应失败 url=%s error=%s", response.url, exc)

            try:
                self._open_profile_page(page, headless)
                first_capture = self._open_microheadline_tab(page)
                first_items = self._extract_feed_items(first_capture.payload_json)
                first_filtered_items = self._filter_items(first_items)
                first_cursor = self._get_next_max_behot_time(first_capture.payload_json, first_items)
                first_type_summary = self._build_type_summary(first_capture.payload_json, first_items)
                first_continue, first_continue_reason = self._get_continue_reason(first_items, first_filtered_items)

                logger.info(
                    "首屏响应 summary item_count=%s filtered_item_count=%s next_cursor=%s top_level_type=%s data_type=%s continue=%s reason=%s url=%s",
                    len(first_items),
                    len(first_filtered_items),
                    first_cursor,
                    first_type_summary.get("topLevelType"),
                    first_type_summary.get("dataType"),
                    first_continue,
                    first_continue_reason,
                    first_capture.request_url,
                )

                if first_capture.payload_json is None or not first_items:
                    logger.warning("首个微头条响应未返回有效文章数据。")

                captures.append(first_capture)

                seen_request_urls = {first_capture.request_url}
                seen_capture_signatures = {self._build_capture_signature(first_capture)}
                seen_item_ids = self._extract_capture_item_ids(first_capture)
                no_progress_rounds = 0
                same_cursor_rounds = 0
                last_seen_cursor = first_cursor

                if self.single_capture:
                    stop_reason = "single_capture_requested"
                    logger.info(
                        "停止分页 reason=%s round=0 capture_count=%s article_count=%s filtered_article_count=%s no_progress_rounds=%s",
                        stop_reason,
                        len(captures),
                        len(first_items),
                        len(first_filtered_items),
                        no_progress_rounds,
                    )
                    return captures

                if not first_continue:
                    stop_reason = f"first_capture_{first_continue_reason}"
                    logger.info(
                        "停止分页 reason=%s round=0 capture_count=%s article_count=%s filtered_article_count=%s no_progress_rounds=%s",
                        stop_reason,
                        len(captures),
                        len(first_items),
                        len(first_filtered_items),
                        no_progress_rounds,
                    )
                    return captures

                page.on("response", handle_response)

                for round_index in range(MAX_SCROLL_ROUNDS - 1):
                    round_number = round_index + 1
                    logger.info(
                        "分页轮次开始 round=%s captures_total=%s seen_items_total=%s no_progress_rounds=%s same_cursor_rounds=%s",
                        round_number,
                        len(captures),
                        len(seen_item_ids),
                        no_progress_rounds,
                        same_cursor_rounds,
                    )
                    scroll_mode = self._trigger_feed_pagination(page, round_index, no_progress_rounds, same_cursor_rounds)

                    new_pending = pending_captures[pending_index:]
                    pending_index = len(pending_captures)
                    accepted_captures: list[FeedCapture] = []
                    rejected_duplicate_url_count = 0
                    rejected_invalid_count = 0
                    rejected_duplicate_signature_count = 0
                    rejected_no_new_items_count = 0
                    new_unique_item_count = 0
                    latest_cursor: int | None = last_seen_cursor

                    for capture in new_pending:
                        items = self._extract_feed_items(capture.payload_json)
                        item_count = len(items)
                        next_cursor = self._get_next_max_behot_time(capture.payload_json, items)
                        latest_cursor = next_cursor if next_cursor is not None else latest_cursor

                        if capture.request_url in seen_request_urls:
                            rejected_duplicate_url_count += 1
                            self._log_capture_decision(round_number, "duplicate_request", capture, item_count, next_cursor)
                            continue

                        if capture.payload_json is None or not items:
                            rejected_invalid_count += 1
                            reason = "invalid_json" if capture.payload_json is None else "empty_items"
                            self._log_capture_decision(round_number, reason, capture, item_count, next_cursor)
                            continue

                        signature = self._build_capture_signature(capture)
                        if signature in seen_capture_signatures:
                            rejected_duplicate_signature_count += 1
                            self._log_capture_decision(round_number, "duplicate_signature", capture, item_count, next_cursor)
                            continue

                        capture_item_ids = self._extract_capture_item_ids(capture)
                        new_item_ids = capture_item_ids - seen_item_ids
                        if capture_item_ids and not new_item_ids:
                            rejected_no_new_items_count += 1
                            self._log_capture_decision(round_number, "no_new_items", capture, item_count, next_cursor)
                            continue

                        seen_request_urls.add(capture.request_url)
                        seen_capture_signatures.add(signature)
                        seen_item_ids.update(new_item_ids)
                        new_unique_item_count += len(new_item_ids)
                        accepted_captures.append(capture)
                        self._log_capture_decision(
                            round_number,
                            "accepted",
                            capture,
                            item_count,
                            next_cursor,
                            len(new_item_ids),
                        )

                    items_total_before = sum(len(self._extract_feed_items(capture.payload_json)) for capture in captures)
                    logger.info(
                        "分页轮次结果 round=%s mode=%s pending=%s accepted=%s dup_req=%s invalid=%s dup_content=%s no_new_items=%s new_unique_items=%s captures_total=%s items_total=%s latest_cursor=%s no_progress_rounds=%s",
                        round_number,
                        scroll_mode,
                        len(new_pending),
                        len(accepted_captures),
                        rejected_duplicate_url_count,
                        rejected_invalid_count,
                        rejected_duplicate_signature_count,
                        rejected_no_new_items_count,
                        new_unique_item_count,
                        len(captures) + len(accepted_captures),
                        items_total_before + sum(len(self._extract_feed_items(c.payload_json)) for c in accepted_captures),
                        latest_cursor,
                        no_progress_rounds,
                    )

                    if not accepted_captures or new_unique_item_count == 0:
                        no_progress_rounds += 1
                        if latest_cursor is not None and latest_cursor == last_seen_cursor:
                            same_cursor_rounds += 1
                        else:
                            same_cursor_rounds = 0

                        reason = "no_new_pending_responses" if not new_pending else "no_new_items_progress"
                        logger.info(
                            "本轮滚动未形成有效进展 round=%s reason=%s no_progress_rounds=%s same_cursor_rounds=%s",
                            round_number,
                            reason,
                            no_progress_rounds,
                            same_cursor_rounds,
                        )

                        if same_cursor_rounds >= MAX_SAME_CURSOR_ROUNDS:
                            stop_reason = "stalled_same_cursor_without_new_items"
                            logger.info(
                                "停止分页 reason=%s round=%s capture_count=%s article_count=%s filtered_article_count=%s no_progress_rounds=%s",
                                stop_reason,
                                round_number,
                                len(captures),
                                items_total_before,
                                len(self._filter_items([item for capture in captures for item in self._extract_feed_items(capture.payload_json)])),
                                no_progress_rounds,
                            )
                            break

                        if no_progress_rounds >= MAX_NO_PROGRESS_ROUNDS:
                            stop_reason = "max_no_progress_rounds"
                            logger.info(
                                "停止分页 reason=%s round=%s capture_count=%s article_count=%s filtered_article_count=%s no_progress_rounds=%s",
                                stop_reason,
                                round_number,
                                len(captures),
                                items_total_before,
                                len(self._filter_items([item for capture in captures for item in self._extract_feed_items(capture.payload_json)])),
                                no_progress_rounds,
                            )
                            break
                        continue

                    no_progress_rounds = 0
                    captures.extend(accepted_captures)
                    latest_capture = accepted_captures[-1]
                    items = self._extract_feed_items(latest_capture.payload_json)
                    filtered_items = self._filter_items(items)
                    latest_cursor = self._get_next_max_behot_time(latest_capture.payload_json, items)
                    if latest_cursor is not None and latest_cursor == last_seen_cursor:
                        same_cursor_rounds += 1
                    else:
                        same_cursor_rounds = 0
                    last_seen_cursor = latest_cursor

                    continue_scrolling, continue_reason = self._get_continue_reason(items, filtered_items)
                    oldest_time = min(
                        (item_time for item_time in (self._extract_item_timestamp(item) for item in items) if item_time is not None),
                        default=None,
                    )
                    newest_time = max(
                        (item_time for item_time in (self._extract_item_timestamp(item) for item in items) if item_time is not None),
                        default=None,
                    )
                    logger.info(
                        "滚动决策 round=%s continue=%s reason=%s item_count=%s filtered_item_count=%s oldest=%s newest=%s start=%s end=%s",
                        round_number,
                        continue_scrolling,
                        continue_reason,
                        len(items),
                        len(filtered_items),
                        oldest_time.isoformat() if oldest_time else None,
                        newest_time.isoformat() if newest_time else None,
                        self.start_time.isoformat() if self.start_time else None,
                        self.end_time.isoformat() if self.end_time else None,
                    )

                    if same_cursor_rounds >= MAX_SAME_CURSOR_ROUNDS and new_unique_item_count == 0:
                        stop_reason = "stalled_same_cursor_without_new_items"
                        logger.info(
                            "停止分页 reason=%s round=%s capture_count=%s article_count=%s filtered_article_count=%s no_progress_rounds=%s",
                            stop_reason,
                            round_number,
                            len(captures),
                            sum(len(self._extract_feed_items(capture.payload_json)) for capture in captures),
                            len(self._filter_items([item for capture in captures for item in self._extract_feed_items(capture.payload_json)])),
                            no_progress_rounds,
                        )
                        break

                    if not continue_scrolling:
                        stop_reason = continue_reason
                        logger.info(
                            "停止分页 reason=%s round=%s capture_count=%s article_count=%s filtered_article_count=%s no_progress_rounds=%s",
                            stop_reason,
                            round_number,
                            len(captures),
                            sum(len(self._extract_feed_items(capture.payload_json)) for capture in captures),
                            len(self._filter_items([item for capture in captures for item in self._extract_feed_items(capture.payload_json)])),
                            no_progress_rounds,
                        )
                        break
                else:
                    stop_reason = "reached_max_scroll_rounds"
                    logger.info(
                        "停止分页 reason=%s round=%s capture_count=%s article_count=%s filtered_article_count=%s no_progress_rounds=%s",
                        stop_reason,
                        MAX_SCROLL_ROUNDS - 1,
                        len(captures),
                        sum(len(self._extract_feed_items(capture.payload_json)) for capture in captures),
                        len(self._filter_items([item for capture in captures for item in self._extract_feed_items(capture.payload_json)])),
                        no_progress_rounds,
                    )
            finally:
                try:
                    page.remove_listener("response", handle_response)
                except Exception:
                    pass
                context.close()
                browser.close()

        if stop_reason is None:
            logger.info("停止分页 reason=completed_without_explicit_reason capture_count=%s", len(captures))
        return captures

    def _collect_feed_captures(self) -> list[FeedCapture]:
        last_error: Exception | None = None
        modes = [self.settings.headless]
        if self.settings.headless:
            modes.append(False)

        for index, headless in enumerate(modes):
            logger.info("开始尝试获取头条 feed 数据 headless=%s", headless)
            try:
                captures = self._collect_feed_captures_with_browser(headless)
                if captures:
                    items: list[dict[str, Any]] = []
                    for capture in captures:
                        items.extend(self._extract_feed_items(capture.payload_json))
                    logger.info("头条 feed 获取完成 headless=%s capture_count=%s article_count=%s", headless, len(captures), len(items))
                    if items or captures[-1].payload_json is not None:
                        return captures
            except PlaywrightTimeoutError as exc:
                last_error = exc
                logger.warning("头条页面加载或切换超时 headless=%s error=%s", headless, exc)
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                logger.warning("头条 feed 获取失败 headless=%s error=%s", headless, exc)

            if index < len(modes) - 1:
                logger.info("切换采集模式 from_headless=%s to_headless=%s reason=previous_attempt_failed", headless, modes[index + 1])

        if last_error is not None:
            raise last_error
        return []

    def _build_warning(self, captures: list[FeedCapture], latest_capture: FeedCapture | None) -> str | None:
        if not captures:
            return "未捕获到目标接口响应。"
        if latest_capture and latest_capture.payload_json is None:
            return "已捕获到目标接口，但返回内容不是可解析的 JSON。"
        return None

    def _build_result(self, captures: list[FeedCapture]) -> dict[str, Any]:
        latest_capture = captures[-1] if captures else None
        latest_valid_capture = next((capture for capture in reversed(captures) if capture.payload_json is not None), latest_capture)
        all_items: list[dict[str, Any]] = []
        seen_item_ids: set[str] = set()

        for capture in captures:
            for item in self._extract_feed_items(capture.payload_json):
                item_id = self._extract_item_identity(item)
                if item_id and item_id in seen_item_ids:
                    continue
                if item_id:
                    seen_item_ids.add(item_id)
                all_items.append(item)

        filtered_items = self._filter_items(all_items)
        type_summary = self._build_type_summary(latest_valid_capture.payload_json if latest_valid_capture else None, all_items)
        result_items = filtered_items if filtered_items else all_items
        normalized_articles = [self._normalize_article(item) for item in result_items]
        capture_filtered_articles = [article for article in normalized_articles if self._passes_capture_thresholds(article)]

        return {
            "url": self.url,
            "matchedRequestUrl": latest_valid_capture.request_url if latest_valid_capture else None,
            "rawText": latest_valid_capture.payload_text if latest_valid_capture else None,
            "json": latest_valid_capture.payload_json if latest_valid_capture else None,
            "startTime": self._serialize_datetime(self.start_time),
            "endTime": self._serialize_datetime(self.end_time),
            "captureCount": len(captures),
            "typeSummary": type_summary,
            "articleCount": len(all_items),
            "filteredArticleCount": len(filtered_items),
            "articles": capture_filtered_articles,
            "warning": self._build_warning(captures, latest_capture),
        }

    def run(self) -> dict[str, Any]:
        self._validate()
        try:
            captures = self._collect_feed_captures()
        except Exception as exc:
            raise RuntimeError(f"账号监控执行失败：{exc}") from exc
        return self._build_result(captures)


def run_batch_account_monitoring(
    benchmark_account_ids: list[int],
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    thresholds: MonitoringThresholds | None = None,
) -> dict[str, Any]:
    normalized_thresholds = thresholds or MonitoringThresholds()
    settings = AccountMonitor(
        url=DEFAULT_MONITOR_URL,
        start_time=start_time,
        end_time=end_time,
        thresholds=normalized_thresholds,
    )._load_settings()
    account_ids = [int(account_id) for account_id in benchmark_account_ids]

    if not account_ids:
        raise ValueError("请选择至少一个对标账号。")

    def run_single(account_id: int) -> BatchMonitorAccountResult:
        benchmark_account = get_benchmark_account_by_id(account_id)
        if benchmark_account is None:
            raise ValueError(f"未找到对标账号 id={account_id}")

        monitor_run = create_monitor_run(benchmark_account, benchmark_account.url)
        try:
            monitor = AccountMonitor(
                url=benchmark_account.url,
                start_time=start_time,
                end_time=end_time,
                thresholds=normalized_thresholds,
            )
            result = monitor.run()
            saved_count = persist_monitored_articles(benchmark_account, monitor_run, result.get("articles") or [])
            status = "warning" if result.get("warning") else "success"
            finish_monitor_run(
                monitor_run,
                status=status,
                warning=result.get("warning"),
                article_count=saved_count,
            )
            return BatchMonitorAccountResult(
                benchmark_account_id=benchmark_account.id,
                benchmark_account_url=benchmark_account.url,
                status=status,
                saved_count=saved_count,
                article_count=int(result.get("articleCount") or 0),
                filtered_article_count=int(result.get("filteredArticleCount") or 0),
                capture_count=int(result.get("captureCount") or 0),
                warning=result.get("warning"),
                error=None,
                monitor_run_id=monitor_run.id,
                articles=result.get("articles") or [],
            )
        except Exception as exc:
            finish_monitor_run(monitor_run, status="failed", warning=str(exc), article_count=0)
            return BatchMonitorAccountResult(
                benchmark_account_id=benchmark_account.id,
                benchmark_account_url=benchmark_account.url,
                status="failed",
                saved_count=0,
                article_count=0,
                filtered_article_count=0,
                capture_count=0,
                warning=None,
                error=str(exc),
                monitor_run_id=monitor_run.id,
                articles=[],
            )

    results: list[BatchMonitorAccountResult] = []
    with ThreadPoolExecutor(max_workers=settings.worker_count) as executor:
        future_map = {executor.submit(run_single, account_id): account_id for account_id in account_ids}
        for future in as_completed(future_map):
            results.append(future.result())

    results.sort(key=lambda item: account_ids.index(item.benchmark_account_id))
    succeeded_count = sum(1 for item in results if item.status == "success")
    failed_count = sum(1 for item in results if item.status == "failed")
    warning_count = sum(1 for item in results if item.status == "warning")

    return {
        "requestedCount": len(account_ids),
        "succeededCount": succeeded_count,
        "failedCount": failed_count,
        "warningCount": warning_count,
        "results": [item.to_dict() for item in results],
    }


def _parse_datetime_arg(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Toutiao account monitoring with Playwright.")
    parser.add_argument("--url", default=DEFAULT_MONITOR_URL, help="Toutiao account URL")
    parser.add_argument("--start-time", default=None, help="ISO datetime, e.g. 2026-03-07T00:00:00")
    parser.add_argument("--end-time", default=None, help="ISO datetime, e.g. 2026-03-07T23:59:59")
    parser.add_argument("--single-capture", action="store_true", help="Only capture the first real feed response")
    args = parser.parse_args()

    monitor = AccountMonitor(
        url=args.url,
        start_time=_parse_datetime_arg(args.start_time),
        end_time=_parse_datetime_arg(args.end_time),
        single_capture=args.single_capture,
    )
    result = monitor.run()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
