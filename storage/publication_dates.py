"""Определение даты публикации документа."""

from __future__ import annotations

import re
from datetime import date
from typing import Mapping


RUSSIAN_MONTHS = {
    "января": 1,
    "февраля": 2,
    "марта": 3,
    "апреля": 4,
    "мая": 5,
    "июня": 6,
    "июля": 7,
    "августа": 8,
    "сентября": 9,
    "октября": 10,
    "ноября": 11,
    "декабря": 12,
}


def normalize_date_value(value: object) -> str | None:
    """Преобразует поддерживаемое значение даты в YYYY-MM-DD."""
    text = str(value or "").strip().lower()

    if not text:
        return None

    iso_match = re.search(
        r"\b(20\d{2})-(0[1-9]|1[0-2])-([0-2]\d|3[01])\b",
        text,
    )

    if iso_match:
        year, month, day = map(int, iso_match.groups())

        try:
            return date(year, month, day).isoformat()
        except ValueError:
            return None

    russian_match = re.search(
        (
            r"\b([0-3]?\d)\s+"
            r"(января|февраля|марта|апреля|мая|июня|"
            r"июля|августа|сентября|октября|ноября|декабря)"
            r"\s+(20\d{2})\b"
        ),
        text,
    )

    if russian_match:
        day_text, month_text, year_text = russian_match.groups()

        try:
            parsed_date = date(
                int(year_text),
                RUSSIAN_MONTHS[month_text],
                int(day_text),
            )
        except ValueError:
            return None

        return parsed_date.isoformat()

    return None


def extract_publication_date(
    item: Mapping[str, object],
) -> str | None:
    """Определяет дату публикации из данных парсера."""
    candidates = [
        item.get("publication_date"),
        item.get("document_date"),
        item.get("possible_date"),
        item.get("date"),
        item.get("title"),
        item.get("file_url"),
        item.get("url"),
    ]

    for candidate in candidates:
        normalized = normalize_date_value(candidate)

        if normalized:
            return normalized

    return None
