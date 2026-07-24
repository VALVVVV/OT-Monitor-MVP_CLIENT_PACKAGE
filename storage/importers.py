"""Импорт результатов парсеров в SQLite."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from storage.checks import finish_check, start_check
from storage.documents import save_document
from storage.publication_dates import extract_publication_date


SOURCE_SETTINGS = {
    "mintrud": {
        "section": "Охрана труда",
        "topic": "Документы Минтруда",
        "summary": (
            "Документ найден на сайте Минтруда России. "
            "Требуется проверка инженером по охране труда."
        ),
    },
    "mchs": {
        "section": "Пожарная безопасность / ГО и ЧС",
        "topic": "Документы МЧС",
        "summary": (
            "Документ найден на сайте МЧС России. "
            "Требуется проверка ответственным специалистом."
        ),
    },
    "minzdrav": {
        "section": "Медицина",
        "topic": "Документы Минздрава",
        "summary": (
            "Документ найден на сайте Минздрава России. "
            "Требуется проверка ответственным за медосмотры."
        ),
    },
}


@dataclass(frozen=True)
class ImportResult:
    """Результат импорта одного источника."""

    check_id: int
    source_id: str
    result: str
    found_count: int
    added_count: int
    skipped_duplicates: int
    invalid_count: int
    error_message: str


def normalize_identity_text(value: object) -> str:
    """Нормализует текст для сравнения документов."""
    return " ".join(str(value or "").lower().split())


def build_document_unique_key(
    source_id: str,
    item: Mapping[str, object],
    original_url: str,
) -> str:
    """Формирует ключ для защиты от логических дублей."""
    title = normalize_identity_text(item.get("title"))

    if source_id == "mintrud":
        number_match = re.search(
            r"№\s*([0-9а-яa-z/-]+)",
            title,
            flags=re.IGNORECASE,
        )
        document_date = normalize_identity_text(
            item.get("possible_date")
            or item.get("document_date")
            or item.get("publication_date")
        )

        if number_match and document_date:
            document_number = number_match.group(1)
            return (
                f"{source_id}:number:{document_number}:"
                f"date:{document_date}"
            )

    return f"{source_id}:url:{original_url}"


def build_document(
    source_id: str,
    item: Mapping[str, object],
) -> dict[str, object]:
    """Преобразует результат парсера в общий формат документа."""
    if source_id not in SOURCE_SETTINGS:
        raise ValueError(f"Неизвестный источник: {source_id}")

    title = str(item.get("title") or "").strip()
    original_url = str(
        item.get("url")
        or item.get("original_url")
        or ""
    ).strip()

    if not title:
        raise ValueError("У документа отсутствует название")

    if not original_url:
        raise ValueError("У документа отсутствует URL")

    settings = SOURCE_SETTINGS[source_id]
    unique_key = build_document_unique_key(
        source_id,
        item,
        original_url,
    )

    return {
        "source_id": source_id,
        "external_id": item.get("id"),
        "title": title,
        "original_url": original_url,
        "publication_date": extract_publication_date(item),
        "summary": settings["summary"],
        "file_url": str(item.get("file_url") or ""),
        "saved_file_path": "",
        "download_status": "not_requested",
        "section": settings["section"],
        "topic": settings["topic"],
        "status": "Новое",
        "engineer_comment": "",
        "unique_key": unique_key,
        "raw_payload": dict(item),
    }


def import_source_payload(
    source_id: str,
    payload: object,
    *,
    trigger_mode: str = "manual",
) -> ImportResult:
    """Импортирует уже загруженный результат парсера."""
    check_id = start_check(source_id, trigger_mode)

    if isinstance(payload, dict) and payload.get("status") == "error":
        error_message = str(
            payload.get("error")
            or "Парсер вернул ошибку"
        )

        finish_check(
            check_id,
            result="error",
            error_message=error_message,
        )

        return ImportResult(
            check_id=check_id,
            source_id=source_id,
            result="error",
            found_count=0,
            added_count=0,
            skipped_duplicates=0,
            invalid_count=0,
            error_message=error_message,
        )

    if not isinstance(payload, list):
        error_message = "Результат парсера должен содержать список документов"

        finish_check(
            check_id,
            result="error",
            error_message=error_message,
        )

        return ImportResult(
            check_id=check_id,
            source_id=source_id,
            result="error",
            found_count=0,
            added_count=0,
            skipped_duplicates=0,
            invalid_count=0,
            error_message=error_message,
        )

    added_count = 0
    skipped_duplicates = 0
    invalid_count = 0

    for item in payload:
        if not isinstance(item, dict):
            invalid_count += 1
            continue

        try:
            document = build_document(source_id, item)
            save_result = save_document(document)
        except ValueError:
            invalid_count += 1
            continue

        if save_result.created:
            added_count += 1
        else:
            skipped_duplicates += 1

    result = "partial" if invalid_count else "success"
    error_message = (
        f"Пропущено некорректных записей: {invalid_count}"
        if invalid_count
        else ""
    )

    finish_check(
        check_id,
        result=result,
        found_count=len(payload),
        added_count=added_count,
        skipped_duplicates=skipped_duplicates,
        error_message=error_message,
    )

    return ImportResult(
        check_id=check_id,
        source_id=source_id,
        result=result,
        found_count=len(payload),
        added_count=added_count,
        skipped_duplicates=skipped_duplicates,
        invalid_count=invalid_count,
        error_message=error_message,
    )


def import_source_file(
    source_id: str,
    file_path: str | Path,
    *,
    trigger_mode: str = "manual",
) -> ImportResult:
    """Читает JSON-файл парсера и импортирует его в SQLite."""
    path = Path(file_path)

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        check_id = start_check(source_id, trigger_mode)
        error_message = f"Ошибка чтения {path}: {error}"

        finish_check(
            check_id,
            result="error",
            error_message=error_message,
        )

        return ImportResult(
            check_id=check_id,
            source_id=source_id,
            result="error",
            found_count=0,
            added_count=0,
            skipped_duplicates=0,
            invalid_count=0,
            error_message=error_message,
        )

    return import_source_payload(
        source_id,
        payload,
        trigger_mode=trigger_mode,
    )
