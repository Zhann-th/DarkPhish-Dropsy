"""Case folders and user-supplied research material stored locally."""
import base64
import binascii
from datetime import UTC, date, datetime
from hashlib import sha256
from typing import Literal
from urllib.parse import urlsplit
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator

from .audit import Snapshot
from .history import _database, store_snapshot

MAX_IMAGE_SIZE = 5 * 1024 * 1024
MAX_IMAGE_BASE64 = (MAX_IMAGE_SIZE + 2) // 3 * 4


def _required_text(value):
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("Введите название.")
    return cleaned


class CaseInput(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=4000)

    @field_validator("title")
    @classmethod
    def check_title(cls, value):
        return _required_text(value)


class MaterialInput(BaseModel):
    kind: Literal["link", "note", "image", "snapshot"]
    title: str = Field(min_length=1, max_length=200)
    source_url: str = Field(default="", max_length=2048)
    note: str = Field(default="", max_length=12000)
    observed_on: date | None = None
    image_base64: str | None = Field(default=None, max_length=MAX_IMAGE_BASE64)
    snapshot: Snapshot | None = None

    @field_validator("title")
    @classmethod
    def check_title(cls, value):
        return _required_text(value)

    @field_validator("source_url")
    @classmethod
    def check_url(cls, value):
        cleaned = value.strip()
        if not cleaned:
            return ""
        if any(c.isspace() or ord(c) < 32 for c in cleaned) or "\\" in cleaned:
            raise ValueError("Введите корректный URL.")
        parsed = urlsplit(cleaned)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username is not None:
            raise ValueError("Укажите публичную ссылку в формате http:// или https://.")
        parsed.port  # Reject malformed ports without resolving the host.
        return cleaned

    @model_validator(mode="after")
    def check_kind(self):
        if self.kind == "link" and not self.source_url:
            raise ValueError("Добавьте адрес сайта или страницы.")
        if self.kind == "note" and not self.note.strip():
            raise ValueError("Введите текст заметки.")
        if (self.kind == "image") != (self.image_base64 is not None):
            raise ValueError("Для скриншота требуется файл.")
        if (self.kind == "snapshot") != (self.snapshot is not None):
            raise ValueError("Для материала аудита требуется снимок.")
        return self


_MATERIAL_FIELDS = """
    id, kind, title, source_url, note, observed_on, created_at,
    image_mime, image_sha256, snapshot_fingerprint,
    (SELECT captured_at FROM snapshots WHERE fingerprint = snapshot_fingerprint) AS snapshot_at
"""


def _init_tables(db):
    db.execute("""
        CREATE TABLE IF NOT EXISTS osint_cases (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS osint_materials (
            id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL REFERENCES osint_cases(id),
            kind TEXT NOT NULL,
            title TEXT NOT NULL,
            source_url TEXT NOT NULL,
            note TEXT NOT NULL,
            observed_on TEXT,
            created_at TEXT NOT NULL,
            image_data BLOB,
            image_mime TEXT,
            image_sha256 TEXT,
            snapshot_fingerprint TEXT REFERENCES snapshots(fingerprint),
            UNIQUE(case_id, snapshot_fingerprint)
        )
    """)


def create_case(data):
    item = {
        "id": uuid4().hex,
        "title": data.title,
        "description": data.description.strip(),
        "created_at": datetime.now(UTC).isoformat(),
    }
    with _database() as db:
        _init_tables(db)
        db.execute("""INSERT INTO osint_cases VALUES (:id, :title, :description, :created_at)""", item)
    return item


def list_cases():
    with _database() as db:
        _init_tables(db)
        rows = db.execute("""
            SELECT c.*, COUNT(m.id) AS material_count FROM osint_cases c
            LEFT JOIN osint_materials m ON c.id = m.case_id
            GROUP BY c.id ORDER BY c.created_at DESC, c.id
        """).fetchall()
    return [dict(row) for row in rows]


def read_case(case_id):
    with _database() as db:
        _init_tables(db)
        case = db.execute("SELECT * FROM osint_cases WHERE id = ?", (case_id,)).fetchone()
        if case is None:
            return None
        rows = db.execute(f"""
            SELECT {_MATERIAL_FIELDS} FROM osint_materials
            WHERE case_id = ? ORDER BY created_at DESC, id
        """, (case_id,)).fetchall()
    return {**dict(case), "materials": [dict(row) for row in rows]}


def _decode_image(encoded):
    try:
        data = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError):
        raise ValueError("Не удалось прочитать изображение.") from None
    if not data or len(data) > MAX_IMAGE_SIZE:
        raise ValueError("Размер скриншота должен быть до 5 МиБ.")
    if len(data) >= 45 and data.startswith(b"\x89PNG\r\n\x1a\n") and data[12:16] == b"IHDR":
        mime = "image/png"
    elif len(data) >= 24 and data.startswith(b"\xff\xd8\xff") and data.endswith(b"\xff\xd9"):
        mime = "image/jpeg"
    elif len(data) >= 24 and data[:4] == b"RIFF" and data[8:16] in (b"WEBPVP8 ", b"WEBPVP8L", b"WEBPVP8X"):
        mime = "image/webp"
    else:
        raise ValueError("Поддерживаются скриншоты PNG, JPEG и WebP.")
    return data, mime, sha256(data).hexdigest()


def add_material(case_id, data):
    raw, mime, digest = _decode_image(data.image_base64) if data.image_base64 is not None else (None, None, None)
    identifier = uuid4().hex
    with _database() as db:
        _init_tables(db)
        if db.execute("SELECT 1 FROM osint_cases WHERE id = ?", (case_id,)).fetchone() is None:
            return None
        fingerprint = None
        source = data.source_url
        if data.snapshot is not None:
            store_snapshot(db, data.snapshot)
            fingerprint = data.snapshot.fingerprint
            if data.snapshot.mode == "web":
                source = MaterialInput.check_url(data.snapshot.scope)
        cursor = db.execute("""
            INSERT INTO osint_materials VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(case_id, snapshot_fingerprint) DO NOTHING
        """, (
            identifier, case_id, data.kind, data.title, source, data.note.strip(),
            data.observed_on.isoformat() if data.observed_on else None,
            datetime.now(UTC).isoformat(), raw, mime, digest, fingerprint,
        ))
        if cursor.rowcount:
            row = db.execute(f"SELECT {_MATERIAL_FIELDS} FROM osint_materials WHERE id = ?", (identifier,)).fetchone()
        else:
            row = db.execute(f"""
                SELECT {_MATERIAL_FIELDS} FROM osint_materials WHERE case_id = ? AND snapshot_fingerprint = ?
            """, (case_id, fingerprint)).fetchone()
    return dict(row)


def read_image(case_id, material_id):
    with _database() as db:
        _init_tables(db)
        row = db.execute("""
            SELECT image_data, image_mime FROM osint_materials
            WHERE case_id = ? AND id = ? AND kind = 'image'
        """, (case_id, material_id)).fetchone()
    return (row["image_data"], row["image_mime"]) if row else None
