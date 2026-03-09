from __future__ import annotations

import json
from datetime import datetime
from math import ceil
from typing import Any

from peewee import (
    CharField,
    DateTimeField,
    ForeignKeyField,
    IntegerField,
    Model,
    SqliteDatabase,
    TextField,
)

from .paths import DB_DIR, SETTINGS_DB_FILE

_db = SqliteDatabase(SETTINGS_DB_FILE)


class BaseModel(Model):
    class Meta:
        database = _db


class Setting(BaseModel):
    key = CharField(unique=True, max_length=255)
    value = TextField()
    updated_at = DateTimeField(default=datetime.utcnow)

    class Meta:
        table_name = "setting"


class BenchmarkAccount(BaseModel):
    url = CharField(unique=True, max_length=2048)
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    last_monitored_at = DateTimeField(null=True)

    class Meta:
        table_name = "benchmark_account"


class MonitorRun(BaseModel):
    benchmark_account = ForeignKeyField(BenchmarkAccount, backref="monitor_runs", on_delete="CASCADE")
    source_url = CharField(max_length=2048)
    status = CharField(max_length=32, default="running")
    warning = TextField(null=True)
    article_count = IntegerField(default=0)
    started_at = DateTimeField(default=datetime.utcnow)
    finished_at = DateTimeField(null=True)

    class Meta:
        table_name = "monitor_run"


class MonitoredArticle(BaseModel):
    benchmark_account = ForeignKeyField(BenchmarkAccount, backref="articles", on_delete="CASCADE")
    monitor_run = ForeignKeyField(MonitorRun, backref="articles", on_delete="SET NULL", null=True)
    dedupe_key = CharField(unique=True, max_length=255)
    item_id = CharField(max_length=255, null=True)
    group_id = CharField(max_length=255, null=True)
    cell_type = CharField(max_length=64, null=True)
    content = TextField(null=True)
    publish_time = DateTimeField(null=True)
    source = CharField(max_length=255, null=True)
    media_name = CharField(max_length=255, null=True)
    display_url = TextField(null=True)
    play_count = IntegerField(null=True)
    digg_count = IntegerField(null=True)
    comment_count = IntegerField(null=True)
    forward_count = IntegerField(null=True)
    bury_count = IntegerField(null=True)
    raw_json = TextField(null=True)
    isdelete = IntegerField(default=0)
    rewritten_title = TextField(null=True)
    rewritten_intro = TextField(null=True)
    rewritten_article = TextField(null=True)
    image_prompts = TextField(null=True)
    image_paths = TextField(null=True)
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)

    class Meta:
        table_name = "monitored_article"


def _serialize_benchmark_account(account: BenchmarkAccount) -> dict[str, Any]:
    return {
        "id": account.id,
        "url": account.url,
        "createdAt": account.created_at.isoformat(),
        "updatedAt": account.updated_at.isoformat(),
        "lastMonitoredAt": account.last_monitored_at.isoformat() if account.last_monitored_at else None,
    }


def _serialize_benchmark_account_option(account: BenchmarkAccount) -> dict[str, Any]:
    return {
        "id": account.id,
        "url": account.url,
    }


def _serialize_monitored_article(article: MonitoredArticle) -> dict[str, Any]:
    account = article.benchmark_account
    return {
        "id": article.id,
        "benchmarkAccountId": account.id,
        "benchmarkAccountUrl": account.url,
        "itemId": article.item_id,
        "groupId": article.group_id,
        "cellType": article.cell_type,
        "content": article.content,
        "publishTime": article.publish_time.isoformat() if article.publish_time else None,
        "source": article.source,
        "mediaName": article.media_name,
        "displayUrl": article.display_url,
        "playCount": article.play_count,
        "diggCount": article.digg_count,
        "commentCount": article.comment_count,
        "forwardCount": article.forward_count,
        "buryCount": article.bury_count,
        "updatedAt": article.updated_at.isoformat(),
        "raw": json.loads(article.raw_json) if article.raw_json else {},
        "rewrittenTitle": article.rewritten_title,
        "rewrittenIntro": article.rewritten_intro,
        "rewrittenArticle": article.rewritten_article,
        "imagePrompts": article.image_prompts,
        "imagePaths": article.image_paths,
    }


def _column_exists(table_name: str, column_name: str) -> bool:
    columns = _db.execute_sql(f"PRAGMA table_info({table_name})").fetchall()
    return any(column[1] == column_name for column in columns)


def _ensure_column(table_name: str, column_name: str, definition: str) -> None:
    if _column_exists(table_name, column_name):
        return
    _db.execute_sql(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")


def init_db() -> None:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    _db.connect(reuse_if_open=True)
    _db.create_tables([Setting, BenchmarkAccount, MonitorRun, MonitoredArticle])
    _ensure_column("benchmark_account", "last_monitored_at", "DATETIME NULL")
    _ensure_column("monitored_article", "isdelete", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column("monitored_article", "rewritten_title", "TEXT NULL")
    _ensure_column("monitored_article", "rewritten_intro", "TEXT NULL")
    _ensure_column("monitored_article", "rewritten_article", "TEXT NULL")
    _ensure_column("monitored_article", "image_prompts", "TEXT NULL")
    _ensure_column("monitored_article", "image_paths", "TEXT NULL")


def get_setting(key: str) -> str | None:
    row = Setting.get_or_none(Setting.key == key)
    return row.value if row else None


def set_setting(key: str, value: str) -> bool:
    now = datetime.utcnow()
    Setting.insert(
        key=key,
        value=value,
        updated_at=now,
    ).on_conflict(
        conflict_target=[Setting.key],
        update={
            Setting.value: value,
            Setting.updated_at: now,
        },
    ).execute()
    return True


def count_settings() -> int:
    return Setting.select().count()


def count_benchmark_accounts() -> int:
    return BenchmarkAccount.select().count()


def count_monitor_runs() -> int:
    return MonitorRun.select().count()


def count_monitored_articles() -> int:
    return MonitoredArticle.select().count()


def list_benchmark_account_options() -> list[dict[str, Any]]:
    query = BenchmarkAccount.select().order_by(BenchmarkAccount.updated_at.desc(), BenchmarkAccount.id.desc())
    return [_serialize_benchmark_account_option(account) for account in query]


def list_benchmark_accounts(page: int, page_size: int) -> dict[str, Any]:
    safe_page = max(1, page)
    safe_page_size = max(1, min(page_size, 200))
    total = BenchmarkAccount.select().count()
    query = (
        BenchmarkAccount.select()
        .order_by(BenchmarkAccount.updated_at.desc(), BenchmarkAccount.id.desc())
        .paginate(safe_page, safe_page_size)
    )

    return {
        "items": [_serialize_benchmark_account(account) for account in query],
        "total": total,
        "page": safe_page,
        "pageSize": safe_page_size,
        "totalPages": ceil(total / safe_page_size) if total else 1,
    }


def create_benchmark_account(url: str) -> dict[str, Any]:
    now = datetime.utcnow()
    account = BenchmarkAccount.create(url=url, created_at=now, updated_at=now)
    return _serialize_benchmark_account(account)


def update_benchmark_account(account_id: int, url: str) -> dict[str, Any]:
    account = BenchmarkAccount.get_by_id(account_id)
    account.url = url
    account.updated_at = datetime.utcnow()
    account.save()
    return _serialize_benchmark_account(account)


def get_benchmark_account_by_id(account_id: int) -> BenchmarkAccount | None:
    return BenchmarkAccount.get_or_none(BenchmarkAccount.id == account_id)


def get_benchmark_account_by_url(url: str) -> BenchmarkAccount | None:
    return BenchmarkAccount.get_or_none(BenchmarkAccount.url == url)


def touch_benchmark_account_monitor(account: BenchmarkAccount, monitored_at: datetime) -> None:
    account.last_monitored_at = monitored_at
    account.updated_at = monitored_at
    account.save()


def delete_benchmark_account(account_id: int) -> bool:
    return BenchmarkAccount.delete_by_id(account_id) > 0


def delete_benchmark_accounts(account_ids: list[int]) -> int:
    if not account_ids:
        return 0

    return BenchmarkAccount.delete().where(BenchmarkAccount.id.in_(account_ids)).execute()


def export_benchmark_accounts() -> list[dict[str, Any]]:
    query = BenchmarkAccount.select().order_by(BenchmarkAccount.created_at.asc(), BenchmarkAccount.id.asc())
    return [_serialize_benchmark_account(account) for account in query]


def import_benchmark_accounts(payload: str) -> dict[str, int]:
    data = json.loads(payload)
    if not isinstance(data, list):
        raise ValueError("导入内容必须是数组。")

    created = 0
    updated = 0
    skipped = 0
    now = datetime.utcnow()

    for item in data:
        if isinstance(item, str):
            url = item.strip()
        elif isinstance(item, dict):
            url = str(item.get("url", "")).strip()
        else:
            skipped += 1
            continue

        if not url:
            skipped += 1
            continue

        existing = BenchmarkAccount.get_or_none(BenchmarkAccount.url == url)
        if existing:
            existing.updated_at = now
            existing.save()
            updated += 1
            continue

        BenchmarkAccount.create(url=url, created_at=now, updated_at=now)
        created += 1

    return {
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "total": len(data),
    }


def create_monitor_run(benchmark_account: BenchmarkAccount, source_url: str) -> MonitorRun:
    return MonitorRun.create(
        benchmark_account=benchmark_account,
        source_url=source_url,
        status="running",
        article_count=0,
        started_at=datetime.utcnow(),
    )


def finish_monitor_run(run: MonitorRun, status: str, warning: str | None, article_count: int) -> None:
    run.status = status
    run.warning = warning
    run.article_count = article_count
    run.finished_at = datetime.utcnow()
    run.save()


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _stringify(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _build_article_dedupe_key(account_id: int, article: dict[str, Any]) -> str:
    item_id = _stringify(article.get("itemId"))
    if item_id:
        return f"{account_id}:item:{item_id}"

    group_id = _stringify(article.get("groupId"))
    if group_id:
        return f"{account_id}:group:{group_id}"

    publish_time = _stringify(article.get("publishTime")) or "none"
    content = _stringify(article.get("content")) or "none"
    return f"{account_id}:fallback:{publish_time}:{content[:80]}"


def persist_monitored_articles(benchmark_account: BenchmarkAccount, run: MonitorRun, articles: list[dict[str, Any]]) -> int:
    now = datetime.utcnow()
    saved_count = 0

    with _db.atomic():
        for article in articles:
            dedupe_key = _build_article_dedupe_key(benchmark_account.id, article)
            existing = MonitoredArticle.get_or_none(MonitoredArticle.dedupe_key == dedupe_key)
            if existing is not None and existing.isdelete:
                continue

            payload = {
                "benchmark_account": benchmark_account,
                "monitor_run": run,
                "dedupe_key": dedupe_key,
                "item_id": _stringify(article.get("itemId")),
                "group_id": _stringify(article.get("groupId")),
                "cell_type": _stringify(article.get("cellType")),
                "content": _stringify(article.get("content")),
                "publish_time": _parse_datetime(_stringify(article.get("publishTime"))),
                "source": _stringify(article.get("source")),
                "media_name": _stringify(article.get("mediaName")),
                "display_url": _stringify(article.get("displayUrl")),
                "play_count": article.get("playCount"),
                "digg_count": article.get("diggCount"),
                "comment_count": article.get("commentCount"),
                "forward_count": article.get("forwardCount"),
                "bury_count": article.get("buryCount"),
                "raw_json": json.dumps(article.get("raw") or {}, ensure_ascii=False),
                "updated_at": now,
            }

            if existing is None:
                MonitoredArticle.create(
                    **payload,
                    isdelete=0,
                    created_at=now,
                )
            else:
                existing.benchmark_account = benchmark_account
                existing.monitor_run = run
                existing.item_id = payload["item_id"]
                existing.group_id = payload["group_id"]
                existing.cell_type = payload["cell_type"]
                existing.content = payload["content"]
                existing.publish_time = payload["publish_time"]
                existing.source = payload["source"]
                existing.media_name = payload["media_name"]
                existing.display_url = payload["display_url"]
                existing.play_count = payload["play_count"]
                existing.digg_count = payload["digg_count"]
                existing.comment_count = payload["comment_count"]
                existing.forward_count = payload["forward_count"]
                existing.bury_count = payload["bury_count"]
                existing.raw_json = payload["raw_json"]
                existing.updated_at = now
                existing.save()

            saved_count += 1

        touch_benchmark_account_monitor(benchmark_account, now)

    return saved_count


def delete_monitored_article(article_id: int) -> bool:
    now = datetime.utcnow()
    return (
        MonitoredArticle.update(isdelete=1, updated_at=now)
        .where((MonitoredArticle.id == article_id) & (MonitoredArticle.isdelete == 0))
        .execute()
        > 0
    )


def _build_monitored_articles_query(filters: dict[str, Any]):
    query = MonitoredArticle.select(MonitoredArticle, BenchmarkAccount).join(BenchmarkAccount).where(MonitoredArticle.isdelete == 0)

    account_id = filters.get("accountId")
    if account_id:
        query = query.where(MonitoredArticle.benchmark_account == int(account_id))

    keyword = str(filters.get("keyword") or "").strip()
    if keyword:
        query = query.where(MonitoredArticle.content.contains(keyword))

    start_time = _parse_datetime(filters.get("startTime"))
    if start_time is not None:
        query = query.where(MonitoredArticle.publish_time >= start_time)

    end_time = _parse_datetime(filters.get("endTime"))
    if end_time is not None:
        query = query.where(MonitoredArticle.publish_time <= end_time)

    for field_name, column in (
        ("minPlayCount", MonitoredArticle.play_count),
        ("minDiggCount", MonitoredArticle.digg_count),
        ("minCommentCount", MonitoredArticle.comment_count),
        ("minForwardCount", MonitoredArticle.forward_count),
    ):
        raw_value = filters.get(field_name)
        if raw_value in (None, ""):
            continue
        query = query.where(column >= int(raw_value))

    return query


def soft_delete_all_monitored_articles() -> int:
    now = datetime.utcnow()
    return MonitoredArticle.update(isdelete=1, updated_at=now).where(MonitoredArticle.isdelete == 0).execute()


def get_monitored_article_by_id(article_id: int) -> MonitoredArticle | None:
    return MonitoredArticle.get_or_none((MonitoredArticle.id == article_id) & (MonitoredArticle.isdelete == 0))


def update_article_rewrite_result(
    article_id: int,
    rewritten_title: str,
    rewritten_intro: str,
    rewritten_article_json: str,
    image_prompts_json: str,
    image_paths_json: str,
) -> bool:
    now = datetime.utcnow()
    updated = (
        MonitoredArticle.update(
            rewritten_title=rewritten_title,
            rewritten_intro=rewritten_intro,
            rewritten_article=rewritten_article_json,
            image_prompts=image_prompts_json,
            image_paths=image_paths_json,
            updated_at=now,
        )
        .where((MonitoredArticle.id == article_id) & (MonitoredArticle.isdelete == 0))
        .execute()
    )
    return updated > 0


def list_article_ids_for_batch(filters: dict[str, Any], skip_rewritten: bool = True) -> list[int]:
    """返回符合筛选条件的所有文章 ID。skip_rewritten=True 时跳过已有改写标题的文章。"""
    query = _build_monitored_articles_query(filters)
    if skip_rewritten:
        query = query.where(
            MonitoredArticle.rewritten_title.is_null() | (MonitoredArticle.rewritten_title == "")
        )
    return [row.id for row in query.select(MonitoredArticle.id)]


def list_completed_article_ids(filters: dict[str, Any]) -> list[int]:
    """返回已完成改写（有标题+正文+图片路径）的所有文章 ID，用于批量下载。"""
    query = _build_monitored_articles_query(filters)
    query = query.where(
        MonitoredArticle.rewritten_title.is_null(False)
        & (MonitoredArticle.rewritten_title != "")
        & MonitoredArticle.rewritten_article.is_null(False)
        & (MonitoredArticle.rewritten_article != "")
        & MonitoredArticle.image_paths.is_null(False)
        & (MonitoredArticle.image_paths != "")
        & (MonitoredArticle.image_paths != "[]")
    )
    return [row.id for row in query.select(MonitoredArticle.id)]


def list_monitored_articles(filters: dict[str, Any], page: int, page_size: int) -> dict[str, Any]:
    safe_page = max(1, page)
    safe_page_size = max(1, min(page_size, 200))

    query = _build_monitored_articles_query(filters)
    total = query.count()
    paged_query = query.order_by(MonitoredArticle.publish_time.desc(nulls="LAST"), MonitoredArticle.updated_at.desc()).paginate(safe_page, safe_page_size)

    return {
        "items": [_serialize_monitored_article(article) for article in paged_query],
        "total": total,
        "page": safe_page,
        "pageSize": safe_page_size,
        "totalPages": ceil(total / safe_page_size) if total else 1,
    }
