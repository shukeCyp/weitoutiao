from __future__ import annotations

import json
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from .db import get_monitored_article_by_id, update_article_rewrite_result
from .image_backend_client import ImageBackendClient
from .paths import IMAGES_DIR
from .title_rewriter import ArticleRewriter, ImagePromptGenerator, TitleRewriter

logger = logging.getLogger("weitoutiao.pipeline")

_SECTION_MARKER_RE = re.compile(r"########(\w+)\s*\n([\s\S]*?)(?=########\w+|$)")
_IMAGE_GEN_MAX_RETRIES = 3


def _extract_first_paragraph(content: str) -> str:
    paragraphs = [p.strip() for p in content.strip().split("\n\n") if p.strip()]
    if paragraphs:
        return paragraphs[0]
    lines = [line.strip() for line in content.strip().splitlines() if line.strip()]
    return lines[0] if lines else content.strip()


def _parse_article_sections(raw: str) -> tuple[str, list[str]]:
    matches = _SECTION_MARKER_RE.findall(raw)
    intro = ""
    sections = []
    for label, body in matches:
        text = body.strip()
        if label.strip() == "导语":
            intro = text
        elif text:
            sections.append(text)
    return intro, sections


def _image_save_path(article_id: int, index: int) -> Path:
    timestamp = int(time.time() * 1000)
    return IMAGES_DIR / f"{timestamp}_{article_id}_{index}.png"


class ArticleRewritePipeline:
    def __init__(self, rewrite_workers: int, image_gen_workers: int) -> None:
        self._rewrite_workers = max(1, rewrite_workers)
        self._image_gen_workers = max(1, image_gen_workers)

    def run(self, article_id: int, template_key: str) -> dict[str, Any]:
        logger.info(
            "改写流水线开始 article_id=%s template_key=%s rewrite_workers=%s image_gen_workers=%s",
            article_id,
            template_key,
            self._rewrite_workers,
            self._image_gen_workers,
        )

        article = get_monitored_article_by_id(article_id)
        if article is None:
            raise ValueError(f"文章不存在或已删除 id={article_id}")

        content = (article.content or "").strip()
        if not content:
            raise ValueError(f"文章内容为空，无法改写 id={article_id}")

        logger.info("文章读取成功 id=%s content_length=%s", article_id, len(content))

        # ── Step 1: 标题 + 文章改写（已有则跳过）──────────────────────────
        has_title = bool(article.rewritten_title)
        has_intro = bool(article.rewritten_intro)
        has_article = bool(article.rewritten_article)

        # #region agent log
        import sys as _sys, json as _pjson, time as _ptime
        def _pdbg(step, **data):
            _pl = Path(_sys.executable).parent / "debug_exe.log" if getattr(_sys, "frozen", False) else Path(__file__).resolve().parent.parent / ".cursor" / "debug.log"
            _pl.parent.mkdir(parents=True, exist_ok=True)
            with _pl.open("a", encoding="utf-8") as _pf:
                _pf.write(_pjson.dumps({"ts": int(_ptime.time()*1000), "step": step, "data": data}) + "\n")
        _pdbg("pipeline_start", article_id=article_id, template_key=template_key,
              has_title=has_title, has_intro=has_intro, has_article=has_article,
              frozen=getattr(_sys, "frozen", False))
        # #endregion

        if has_title and has_intro and has_article:
            rewritten_title = article.rewritten_title
            rewritten_intro = article.rewritten_intro
            article_sections = json.loads(article.rewritten_article)
            rewritten_article_json = article.rewritten_article
            logger.info("跳过改写步骤（已有结果） title=%r intro_len=%s sections=%s", rewritten_title, len(rewritten_intro), len(article_sections))
        else:
            first_para = _extract_first_paragraph(content)
            # #region agent log
            _pdbg("rewrite_start", workers=self._rewrite_workers, content_len=len(content), first_para_len=len(first_para))
            # #endregion
            with ThreadPoolExecutor(max_workers=self._rewrite_workers, thread_name_prefix="rewrite") as rewrite_pool:
                title_future = rewrite_pool.submit(self._rewrite_title, first_para)
                article_future = rewrite_pool.submit(self._rewrite_article, content, template_key)
                rewritten_title = title_future.result()
                # #region agent log
                _pdbg("title_done", title=rewritten_title[:80])
                # #endregion
                try:
                    rewritten_raw = article_future.result()
                    # #region agent log
                    _pdbg("article_done", length=len(rewritten_raw), preview=rewritten_raw[:100])
                    # #endregion
                except Exception as _exc:
                    # #region agent log
                    _pdbg("article_failed", error_type=type(_exc).__name__, error=str(_exc)[:300])
                    # #endregion
                    raise

            logger.info("标题和文章改写完成 title=%r article_length=%s", rewritten_title, len(rewritten_raw))
            rewritten_intro, article_sections = _parse_article_sections(rewritten_raw)
            rewritten_article_json = json.dumps(article_sections, ensure_ascii=False)
            logger.info("文章段落解析完成 intro_len=%s sections=%s", len(rewritten_intro), len(article_sections))

        # ── Step 2: 图片提示词（已有则跳过）──────────────────────────────
        has_prompts = bool(article.image_prompts) and (has_title and has_intro and has_article)

        if has_prompts:
            image_prompts = json.loads(article.image_prompts)
            image_prompts_json = article.image_prompts
            logger.info("跳过图片提示词生成（已有结果） count=%s", len(image_prompts))
        else:
            article_text_for_prompt = "\n\n".join(article_sections)
            image_prompts = self._generate_image_prompts(article_text_for_prompt)
            image_prompts_json = json.dumps(image_prompts, ensure_ascii=False)
            logger.info("图片提示词生成完成 count=%s", len(image_prompts))

        # ── Step 3: 生图（只补全缺失的）─────────────────────────────────
        existing_paths: list[str | None] = json.loads(article.image_paths) if article.image_paths else []
        # 对齐长度到 image_prompts
        while len(existing_paths) < len(image_prompts):
            existing_paths.append(None)

        # 检查文件是否真实存在（兼容扩展名偏差），不存在则视为缺失
        def _resolve_existing(p: str | None) -> str | None:
            if not p:
                return None
            path = Path(p)
            if path.exists():
                return str(path)
            for alt_ext in (".jpeg", ".jpg", ".png", ".webp"):
                alt = path.with_suffix(alt_ext)
                if alt.exists():
                    return str(alt)
            return None

        resolved_paths: list[str | None] = [_resolve_existing(p) for p in existing_paths]
        missing_indices = [i for i, p in enumerate(resolved_paths) if not p]
        logger.info("生图状态检查 total=%s missing=%s resolved=%s", len(image_prompts), missing_indices, resolved_paths)

        if missing_indices:
            new_paths = list(resolved_paths)
            newly_generated = self._generate_missing_images(image_prompts, missing_indices, article_id)
            for i, path in newly_generated.items():
                new_paths[i] = path
            image_paths = new_paths
        else:
            image_paths = resolved_paths
            logger.info("所有图片已存在，跳过生图步骤")

        image_paths_json = json.dumps(image_paths, ensure_ascii=False)
        logger.info("图片生成完成 paths=%s", image_paths)

        # ── 持久化 ────────────────────────────────────────────────────────
        update_article_rewrite_result(
            article_id,
            rewritten_title,
            rewritten_intro,
            rewritten_article_json,
            image_prompts_json,
            image_paths_json,
        )
        logger.info("改写结果已保存到数据库 article_id=%s", article_id)

        return {
            "rewrittenTitle": rewritten_title,
            "rewrittenIntro": rewritten_intro,
            "rewrittenArticle": article_sections,
            "imagePrompts": image_prompts,
            "imagePaths": image_paths,
        }

    def _rewrite_title(self, first_para: str) -> str:
        logger.info("开始标题改写 first_para_length=%s", len(first_para))
        rewriter = TitleRewriter()
        raw = rewriter.rewrite(first_para)
        lines = raw.strip().splitlines()
        title_lines = [l for l in lines if not l.strip().startswith("########")]
        result = " ".join(title_lines).strip() or raw.strip()
        logger.info("标题改写完成 result=%r", result)
        return result

    def _rewrite_article(self, content: str, template_key: str) -> str:
        logger.info("开始文章改写 template_key=%s content_length=%s", template_key, len(content))
        rewriter = ArticleRewriter()
        result = rewriter.rewrite(content, template_key)
        logger.info("文章改写完成 result_length=%s", len(result))
        return result

    def _generate_image_prompts(self, rewritten_article: str) -> list[str]:
        generator = ImagePromptGenerator()
        return generator.generate(rewritten_article)

    def _generate_missing_images(
        self, prompts: list[str], missing_indices: list[int], article_id: int
    ) -> dict[int, str | None]:
        """只对 missing_indices 中的下标（0-based）生成图片，返回 {index: path} 映射。"""
        client = ImageBackendClient()
        tasks = []
        for i in missing_indices:
            prompt = prompts[i] if i < len(prompts) else ""
            if not prompt:
                logger.warning("第 %s 张图片提示词为空，跳过", i + 1)
                continue
            save_path = _image_save_path(article_id, i + 1)
            tasks.append((i, prompt, save_path))

        if not tasks:
            return {}

        results: dict[int, str | None] = {}
        with ThreadPoolExecutor(
            max_workers=min(self._image_gen_workers, len(tasks)),
            thread_name_prefix="image_gen",
        ) as image_pool:
            future_map = {
                image_pool.submit(self._generate_single_image, client, prompt, save_path): idx
                for idx, prompt, save_path in tasks
            }
            for future in as_completed(future_map):
                idx = future_map[future]
                try:
                    path = future.result()
                    results[idx] = path
                    logger.info("第 %s 张图片生成成功 path=%s", idx + 1, path)
                except Exception as exc:
                    logger.error("第 %s 张图片生成最终失败 error=%s", idx + 1, exc)
                    results[idx] = None

        return results

    def _generate_single_image(self, client: ImageBackendClient, prompt: str, save_path: Path) -> str:
        return client.generate_and_save(prompt, save_path, max_retries=_IMAGE_GEN_MAX_RETRIES)
