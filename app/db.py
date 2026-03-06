from __future__ import annotations

from datetime import datetime

from peewee import CharField, DateTimeField, Model, SqliteDatabase, TextField

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


def init_db() -> None:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    _db.connect(reuse_if_open=True)
    _db.create_tables([Setting])


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
