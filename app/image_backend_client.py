from __future__ import annotations

import base64
import json
import logging
import re
import time
from pathlib import Path
from urllib import error, request

from .db import get_setting

IMAGE_BASE_URL_KEY = "image.base_url"
IMAGE_API_KEY_KEY = "image.api_key"
IMAGE_MODEL_KEY = "image.model"
IMAGE_GEN_TIMEOUT_SECONDS = 300

logger = logging.getLogger("weitoutiao.image")

_MARKDOWN_IMAGE_RE = re.compile(
    r"!\[[^\]]*\]\((data:image/([a-zA-Z0-9.+-]+);base64,([^)]+))\)"
)


def _read_required_setting(key: str, label: str) -> str:
    value = get_setting(key)
    if not value or not value.strip():
        raise RuntimeError(f"未配置{label}，请先在设置中填写。")
    return value.strip()


def _normalize_base_url(value: str) -> str:
    return value.rstrip("/")


def _parse_sse_events(chunk: str) -> list[str]:
    events = []
    for line in chunk.splitlines():
        line = line.strip()
        if not line.startswith("data:"):
            continue
        payload = line[5:].strip()
        if payload and payload != "[DONE]":
            events.append(payload)
    return events


class ImageBackendClient:
    def generate_and_save(self, prompt: str, save_path: Path, *, max_retries: int = 3) -> str:
        last_exc: Exception | None = None
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(
                    "生图请求开始 attempt=%d/%d save_path=%s prompt_preview=%r",
                    attempt,
                    max_retries,
                    save_path,
                    prompt[:80],
                )
                actual_path = self._generate_and_save_once(prompt, save_path)
                logger.info("生图成功 attempt=%d actual_path=%s", attempt, actual_path)
                return str(actual_path)
            except Exception as exc:
                last_exc = exc
                logger.warning("生图失败 attempt=%d/%d error=%s", attempt, max_retries, exc)
                if attempt < max_retries:
                    time.sleep(2)

        raise RuntimeError(f"生图失败（已重试 {max_retries} 次）：{last_exc}") from last_exc

    def _generate_and_save_once(self, prompt: str, save_path: Path) -> Path:
        model = _read_required_setting(IMAGE_MODEL_KEY, "生图 model")
        base_url = _normalize_base_url(_read_required_setting(IMAGE_BASE_URL_KEY, "生图 base_url"))
        api_key = get_setting(IMAGE_API_KEY_KEY) or ""
        endpoint = f"{base_url}/chat/completions"

        payload_bytes = json.dumps(
            {
                "model": model,
                "messages": [{"role": "user", "content": prompt.strip()}],
                "stream": True,
            },
            ensure_ascii=False,
        ).encode("utf-8")

        logger.info("发起生图 SSE 请求 endpoint=%s model=%s", endpoint, model)

        request_headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "Accept": "text/event-stream",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Connection": "keep-alive",
        }

        req = request.Request(
            url=endpoint,
            data=payload_bytes,
            headers=request_headers,
            method="POST",
        )

        raw_content = ""
        started_at = time.perf_counter()

        try:
            with request.urlopen(req, timeout=IMAGE_GEN_TIMEOUT_SECONDS) as response:
                logger.info(
                    "生图 SSE 连接建立 status=%s",
                    getattr(response, "status", None),
                )
                all_raw_bytes = b""
                while True:
                    chunk = response.read(4096)
                    if not chunk:
                        break
                    all_raw_bytes += chunk

                complete_text = all_raw_bytes.decode("utf-8", errors="replace")
                for payload in _parse_sse_events(complete_text):
                    try:
                        data = json.loads(payload)
                    except json.JSONDecodeError:
                        continue
                    delta = (data.get("choices") or [{}])[0].get("delta") or {}
                    content_piece = delta.get("content") or ""
                    if content_piece:
                        raw_content += content_piece

        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="ignore")
            elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
            logger.exception(
                "生图请求HTTP异常 status=%s elapsed_ms=%s response=%r",
                exc.code,
                elapsed_ms,
                body[:300],
            )
            raise RuntimeError(f"生图请求失败: {exc.code} {body or exc.reason}") from exc
        except error.URLError as exc:
            elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
            logger.exception("生图请求网络异常 reason=%s elapsed_ms=%s", exc.reason, elapsed_ms)
            raise RuntimeError(f"生图请求网络异常: {exc.reason}") from exc

        elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
        logger.info(
            "生图 SSE 接收完毕 elapsed_ms=%s raw_content_length=%s",
            elapsed_ms,
            len(raw_content),
        )

        match = _MARKDOWN_IMAGE_RE.search(raw_content)
        if not match:
            preview = raw_content[:300]
            logger.error("生图响应中未找到 base64 图片数据 raw_preview=%r", preview)
            raise RuntimeError("生图响应中未找到 base64 图片数据。")

        mime_type = match.group(2)
        b64_data = match.group(3)
        image_bytes = base64.b64decode(b64_data)

        ext = mime_type.split("/")[-1].split("+")[0] or "png"
        final_path = save_path.with_suffix(f".{ext}") if save_path.suffix != f".{ext}" else save_path
        final_path.parent.mkdir(parents=True, exist_ok=True)
        final_path.write_bytes(image_bytes)

        logger.info(
            "图片已保存 path=%s mime=%s size_bytes=%s",
            final_path,
            mime_type,
            len(image_bytes),
        )

        if final_path != save_path:
            save_path.unlink(missing_ok=True)

        return final_path
