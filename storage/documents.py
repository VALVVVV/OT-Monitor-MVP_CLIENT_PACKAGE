"""Операции с документами в SQLite."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Mapping

from storage import database


@dataclass(frozen=True)
class SaveDocumentResult:
    """Результат сохранения документа."""

    document_id: int
    created: bool


def build_unique_key(source_id: str, original_url: str) -> str:
    """Формирует устойчивый ключ документа."""
    return f"{source_id}:{original_url}"


def save_document(document: Mapping[str, object]) -> SaveDocumentResult:
    """Добавляет документ или обновляет его технические данные.

    При повторном обнаружении сохраняет ранее назначенные пользователем
    статус и комментарий.
    """
    source_id = str(document.get("source_id") or "").strip()
    title = str(document.get("title") or "").strip()
    original_url = str(document.get("original_url") or "").strip()

    if not source_id:
        raise ValueError("Не указан source_id документа")
    if not title:
        raise ValueError("Не указано название документа")
    if not original_url:
        raise ValueError("Не указан original_url документа")

    discovered_at = str(
        document.get("discovered_at")
        or datetime.now().isoformat(timespec="seconds")
    )
    unique_key = str(
        document.get("unique_key")
        or build_unique_key(source_id, original_url)
    )

    raw_payload = document.get("raw_payload")
    if raw_payload is None:
        raw_payload = dict(document)

    raw_payload_json = json.dumps(
        raw_payload,
        ensure_ascii=False,
        sort_keys=True,
    )

    with database.get_connection() as connection:
        existing = connection.execute(
            """
            SELECT id
            FROM documents
            WHERE source_id = ?
              AND original_url = ?
            """,
            (source_id, original_url),
        ).fetchone()

        if existing is not None:
            document_id = int(existing["id"])

            connection.execute(
                """
                UPDATE documents
                SET external_id = ?,
                    title = ?,
                    publication_date = ?,
                    summary = ?,
                    file_url = ?,
                    saved_file_path = ?,
                    download_status = ?,
                    section = ?,
                    topic = ?,
                    unique_key = ?,
                    raw_payload = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    document.get("external_id"),
                    title,
                    document.get("publication_date"),
                    str(document.get("summary") or ""),
                    str(document.get("file_url") or ""),
                    str(document.get("saved_file_path") or ""),
                    str(
                        document.get("download_status")
                        or "not_requested"
                    ),
                    str(document.get("section") or ""),
                    str(document.get("topic") or ""),
                    unique_key,
                    raw_payload_json,
                    document_id,
                ),
            )

            return SaveDocumentResult(
                document_id=document_id,
                created=False,
            )

        cursor = connection.execute(
            """
            INSERT INTO documents (
                source_id,
                external_id,
                title,
                original_url,
                publication_date,
                discovered_at,
                summary,
                file_url,
                saved_file_path,
                download_status,
                section,
                topic,
                status,
                engineer_comment,
                unique_key,
                raw_payload
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source_id,
                document.get("external_id"),
                title,
                original_url,
                document.get("publication_date"),
                discovered_at,
                str(document.get("summary") or ""),
                str(document.get("file_url") or ""),
                str(document.get("saved_file_path") or ""),
                str(
                    document.get("download_status")
                    or "not_requested"
                ),
                str(document.get("section") or ""),
                str(document.get("topic") or ""),
                str(document.get("status") or "Новое"),
                str(document.get("engineer_comment") or ""),
                unique_key,
                raw_payload_json,
            ),
        )

        return SaveDocumentResult(
            document_id=int(cursor.lastrowid),
            created=True,
        )


def get_document(document_id: int) -> dict[str, object] | None:
    """Возвращает один документ по идентификатору."""
    with database.get_connection() as connection:
        row = connection.execute(
            """
            SELECT *
            FROM documents
            WHERE id = ?
            """,
            (document_id,),
        ).fetchone()

    return dict(row) if row is not None else None


def list_documents() -> list[dict[str, object]]:
    """Возвращает документы от новых к старым."""
    with database.get_connection() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM documents
            ORDER BY discovered_at DESC, id DESC
            """
        ).fetchall()

    return [dict(row) for row in rows]
