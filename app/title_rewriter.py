from __future__ import annotations

import json
import logging
import re
import time
from urllib import error, request

from .db import get_setting
from .prompt_constants import PromptTemplates

LLM_BASE_URL_KEY = "llm.base_url"
LLM_API_KEY_KEY = "llm.api_key"
LLM_MODEL_KEY = "llm.model"
TITLE_REWRITE_TIMEOUT_SECONDS = 120
ARTICLE_REWRITE_TIMEOUT_SECONDS = 300
LLM_PREVIEW_MAX_LENGTH = 300
ARTICLE_REWRITE_PROMPTS = {
    "international_account_starter": PromptTemplates.INTERNATIONAL_ACCOUNT_STARTER_PROMPT,
    "international_stable_hardcore": PromptTemplates.INTERNATIONAL_STABLE_HARDCORE_PROMPT,
    "international_stable_strategic": PromptTemplates.INTERNATIONAL_STABLE_STRATEGIC_PROMPT,
}

logger = logging.getLogger("weitoutiao.llm")

TITLE_OUTPUT_FORMAT_INSTRUCTION = """

请严格按照下面格式返回，不要输出任何多余说明：
########标题
XXXXX（此处是标题）
"""

ARTICLE_OUTPUT_FORMAT_INSTRUCTION = """

请严格按照下面格式返回，不要输出任何多余说明，在 ########01 之前禁止输出任何导语、引子、前言或与文章无关的内容：
########01
段落1
########02
段落2

后续小节也必须完全按照这个规则继续输出，使用 ########03、########04 ... 这样的格式。
"""


class BaseLlmRewriter:
    def _rewrite(
        self,
        user_prompt: str,
        *,
        empty_message: str,
        error_prefix: str,
        timeout_seconds: int,
    ) -> str:
        normalized_prompt = user_prompt.strip()
        if not normalized_prompt:
            raise ValueError(empty_message)

        model = self._read_required_setting(LLM_MODEL_KEY, "大模型 model")
        base_url = self._normalize_base_url(self._read_required_setting(LLM_BASE_URL_KEY, "大模型 base_url"))
        api_key = get_setting(LLM_API_KEY_KEY) or ""
        endpoint = f"{base_url}/chat/completions"
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": normalized_prompt,
                }
            ],
            "stream": False,
        }
        payload_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        logger.info(
            "发起大模型请求 endpoint=%s model=%s timeout=%ss payload_bytes=%s user_prompt_length=%s user_prompt_preview=%r api_key_configured=%s",
            endpoint,
            model,
            timeout_seconds,
            len(payload_bytes),
            len(normalized_prompt),
            self._preview_text(normalized_prompt),
            bool(api_key.strip()),
        )

        req = request.Request(
            url=endpoint,
            data=payload_bytes,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            method="POST",
        )

        started_at = time.perf_counter()
        try:
            with request.urlopen(req, timeout=timeout_seconds) as response:
                response_body = response.read().decode("utf-8")
                elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
                logger.info(
                    "大模型请求返回 status=%s reason=%s elapsed_ms=%s response_bytes=%s response_preview=%r",
                    getattr(response, "status", None),
                    getattr(response, "reason", None),
                    elapsed_ms,
                    len(response_body.encode("utf-8")),
                    self._preview_text(response_body),
                )
                data = json.loads(response_body)
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="ignore")
            elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
            logger.exception(
                "大模型请求HTTP异常 status=%s reason=%s elapsed_ms=%s response_preview=%r",
                exc.code,
                exc.reason,
                elapsed_ms,
                self._preview_text(body),
            )
            raise RuntimeError(f"{error_prefix}: {exc.code} {body or exc.reason}") from exc
        except error.URLError as exc:
            elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
            logger.exception("大模型请求网络异常 reason=%s elapsed_ms=%s", exc.reason, elapsed_ms)
            raise RuntimeError(f"{error_prefix}: {exc.reason}") from exc
        except Exception:
            elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
            logger.exception("大模型请求解析异常 elapsed_ms=%s", elapsed_ms)
            raise

        response_content = data.get("choices", [{}])[0].get("message", {}).get("content")
        if not isinstance(response_content, str) or not response_content.strip():
            logger.error(
                "大模型响应缺少有效内容 response_keys=%s response_preview=%r",
                list(data.keys()) if isinstance(data, dict) else None,
                self._preview_text(json.dumps(data, ensure_ascii=False)) if isinstance(data, dict) else self._preview_text(str(data)),
            )
            raise RuntimeError(f"{error_prefix}响应中未找到有效内容。")

        final_content = response_content.strip()
        logger.info(
            "大模型请求完成 output_length=%s output_preview=%r",
            len(final_content),
            self._preview_text(final_content),
        )
        return final_content

    def _render_prompt(self, template: str, content: str) -> str:
        normalized_content = content.strip()
        replacements = (
            ("{{TITLE}}", normalized_content),
            ("{{title}}", normalized_content),
            ("{title}", normalized_content),
            ("{{INPUT}}", normalized_content),
            ("{{input}}", normalized_content),
            ("{input}", normalized_content),
            ("{{CONTENT}}", normalized_content),
            ("{{content}}", normalized_content),
            ("{content}", normalized_content),
        )

        rendered_prompt = template
        matched_placeholder = False
        for placeholder, value in replacements:
            if placeholder in rendered_prompt:
                rendered_prompt = rendered_prompt.replace(placeholder, value)
                matched_placeholder = True

        if not matched_placeholder:
            return f"{template.rstrip()}\n\n{normalized_content}"
        return rendered_prompt

    def _append_output_instruction(self, prompt: str, instruction: str) -> str:
        return f"{prompt.rstrip()}\n{instruction}"

    def _normalize_title_output(self, content: str) -> str:
        normalized = content.strip()
        if normalized.startswith("########标题"):
            return normalized
        return f"########标题\n{normalized}"

    def _normalize_article_output(self, content: str) -> str:
        normalized = content.strip()
        if normalized.startswith("########01"):
            return normalized

        lines = [line.strip() for line in normalized.splitlines() if line.strip()]
        if not lines:
            return "########01\n"

        blocks: list[str] = []
        current_number = 1
        current_paragraph_lines: list[str] = []

        for line in lines:
            if re.fullmatch(r"#*\s*\d{1,2}[、.．)]?\s*", line):
                if current_paragraph_lines:
                    blocks.append(f"########{current_number:02d}")
                    blocks.append("\n".join(current_paragraph_lines))
                    current_number += 1
                    current_paragraph_lines = []
                continue
            current_paragraph_lines.append(line)

        if current_paragraph_lines:
            blocks.append(f"########{current_number:02d}")
            blocks.append("\n".join(current_paragraph_lines))

        if not blocks:
            blocks.append("########01")
            blocks.append("\n".join(lines))

        return "\n".join(blocks)

    def _rewrite_with_format(
        self,
        template: str,
        content: str,
        *,
        empty_message: str,
        error_prefix: str,
        timeout_seconds: int,
        format_instruction: str,
        output_normalizer,
    ) -> str:
        rendered_prompt = self._render_prompt(template, content)
        formatted_prompt = self._append_output_instruction(rendered_prompt, format_instruction)
        result = self._rewrite(
            formatted_prompt,
            empty_message=empty_message,
            error_prefix=error_prefix,
            timeout_seconds=timeout_seconds,
        )
        return output_normalizer(result)

    def _read_required_setting(self, key: str, label: str) -> str:
        value = (get_setting(key) or "").strip()
        if not value:
            raise RuntimeError(f"未配置{label}。")
        return value

    def _normalize_base_url(self, value: str) -> str:
        return value.rstrip("/")

    def _preview_text(self, value: str, limit: int = LLM_PREVIEW_MAX_LENGTH) -> str:
        normalized_value = " ".join(value.split())
        if len(normalized_value) <= limit:
            return normalized_value
        return f"{normalized_value[:limit]}...<truncated>"


class TitleRewriter(BaseLlmRewriter):
    def rewrite(self, title: str) -> str:
        return self._rewrite_with_format(
            PromptTemplates.TITLE_REWRITE_PROMPT,
            title,
            empty_message="标题不能为空。",
            error_prefix="标题改写请求失败",
            timeout_seconds=TITLE_REWRITE_TIMEOUT_SECONDS,
            format_instruction=TITLE_OUTPUT_FORMAT_INSTRUCTION,
            output_normalizer=self._normalize_title_output,
        )


class ArticleRewriter(BaseLlmRewriter):
    def rewrite(self, content: str, template_key: str) -> str:
        prompt = ARTICLE_REWRITE_PROMPTS.get(template_key)
        if not prompt:
            raise ValueError("无效的文章改写模板。")

        return self._rewrite_with_format(
            prompt,
            content,
            empty_message="文章内容不能为空。",
            error_prefix="文章改写请求失败",
            timeout_seconds=ARTICLE_REWRITE_TIMEOUT_SECONDS,
            format_instruction=ARTICLE_OUTPUT_FORMAT_INSTRUCTION,
            output_normalizer=self._normalize_article_output,
        )

    def list_template_keys(self) -> list[str]:
        return list(ARTICLE_REWRITE_PROMPTS.keys())


IMAGE_PROMPT_GENERATION_TIMEOUT_SECONDS = 120
IMAGE_PROMPT_MARKER_RE = re.compile(r"########(\d+)\s*\n([\s\S]*?)(?=########\d+|$)")


class ImagePromptGenerator(BaseLlmRewriter):
    def generate(self, rewritten_article: str) -> list[str]:
        logger.info("开始生成图片提示词 article_length=%s", len(rewritten_article))
        prompt = PromptTemplates.IMAGE_PROMPT_GENERATION_PROMPT.replace("{{CONTENT}}", rewritten_article.strip())
        raw = self._rewrite(
            prompt,
            empty_message="改写文章不能为空。",
            error_prefix="图片提示词生成请求失败",
            timeout_seconds=IMAGE_PROMPT_GENERATION_TIMEOUT_SECONDS,
        )
        prompts = self._parse_image_prompts(raw)
        logger.info("图片提示词生成完成 count=%s", len(prompts))
        return prompts

    def _parse_image_prompts(self, raw: str) -> list[str]:
        matches = IMAGE_PROMPT_MARKER_RE.findall(raw)
        prompts = [content.strip() for _index, content in sorted(matches, key=lambda m: int(m[0])) if content.strip()]
        if not prompts:
            lines = [line.strip() for line in raw.strip().splitlines() if line.strip()]
            prompts = lines[:3]
        return prompts[:3]


__all__ = ["ArticleRewriter", "ARTICLE_REWRITE_PROMPTS", "ImagePromptGenerator", "TitleRewriter"]
