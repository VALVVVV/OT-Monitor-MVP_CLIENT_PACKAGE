#!/usr/bin/env python3
"""Разведочный скрипт для страницы документов Минздрава России."""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse


TARGET_URL = "https://minzdrav.gov.ru/documents"
SOURCE_NAME = "Минздрав России"
HTML_OUTPUT_PATH = Path("runtime/parser_artifacts/minzdrav_docs_page.html")
ALL_LINKS_OUTPUT_PATH = Path("runtime/parser_artifacts/minzdrav_links_inspection.json")
FILTERED_OUTPUT_PATH = Path("runtime/parser_artifacts/minzdrav_documents_filtered.json")
REJECTED_OUTPUT_PATH = Path("runtime/parser_artifacts/minzdrav_links_rejected.json")
TIMEOUT_SECONDS = 20
MINZDRAV_MIN_DATE = date(2026, 5, 1)
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)


def ensure_dependencies() -> tuple[Any, Any] | None:
    """Проверяет, что requests и bs4 доступны."""
    try:
        import requests  # type: ignore
    except ImportError:
        print("Не удалось запустить скрипт: библиотека requests не установлена.")
        print("Установите зависимости командой:")
        print("pip install requests beautifulsoup4")
        return None

    try:
        from bs4 import BeautifulSoup  # type: ignore
    except ImportError:
        print("Не удалось запустить скрипт: библиотека beautifulsoup4 не установлена.")
        print("Установите зависимости командой:")
        print("pip install requests beautifulsoup4")
        return None

    return requests, BeautifulSoup


def save_json(output_path: Path, payload: Any) -> None:
    """Сохраняет JSON в UTF-8."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def make_link_item(title: str, url: str) -> dict[str, str]:
    """Формирует объект ссылки в нужном формате."""
    return {
        "source": SOURCE_NAME,
        "title": title,
        "url": url,
        "note": "Найдена ссылка на странице Минздрава",
    }


def make_rejected_link_item(title: str, url: str, reason: str) -> dict[str, str]:
    """Формирует объект отклонённой ссылки с причиной."""
    return {
        "source": SOURCE_NAME,
        "title": title,
        "url": url,
        "note": reason,
    }


def is_allowed_href(href: str) -> bool:
    """Отсекает пустые и служебные href."""
    href = href.strip().lower()
    if not href:
        return False
    if href.startswith(("#", "javascript:", "mailto:", "tel:")):
        return False
    return True


def is_document_page_url(url: str) -> bool:
    """Проверяет, что ссылка ведёт на страницу документа Минздрава."""
    parsed_url = urlparse(url)
    if parsed_url.netloc != urlparse(TARGET_URL).netloc:
        return False
    if parsed_url.query:
        return False

    path = parsed_url.path.rstrip("/")
    return path.startswith("/documents/") and path != "/documents"


def parse_document_date(raw_value: str) -> date | None:
    """Пытается извлечь дату документа из ISO-атрибута."""
    clean_value = raw_value.strip()
    if not clean_value:
        return None

    try:
        return date.fromisoformat(clean_value[:10])
    except ValueError:
        return None


def build_document_metadata_map(soup: Any) -> dict[str, dict[str, str]]:
    """Собирает метаданные документов из основного списка на странице."""
    metadata_map: dict[str, dict[str, str]] = {}

    for document_tag in soup.find_all("document"):
        link_tag = document_tag.find("a", href=True)
        if link_tag is None:
            continue

        href = str(link_tag.get("href", "")).strip()
        if not is_allowed_href(href):
            continue

        absolute_url = urljoin(TARGET_URL, href)
        if not is_document_page_url(absolute_url):
            continue

        title = link_tag.get_text(" ", strip=True)
        time_tag = document_tag.find("time")
        document_date = ""
        if time_tag is not None:
            document_date = str(time_tag.get("datetime", "")).strip()

        metadata_map[absolute_url] = {
            "title": title,
            "document_date": document_date,
        }

    return metadata_map


def classify_document_link(title: str, url: str, metadata_map: dict[str, dict[str, str]]) -> str | None:
    """Возвращает причину отклонения или None, если ссылка подходит для filtered."""
    clean_title = title.strip()

    if not is_document_page_url(url):
        return "Отклонено: служебная ссылка"

    if not clean_title:
        return "Отклонено: служебная ссылка"

    metadata = metadata_map.get(url)
    if metadata is None:
        return "Отклонено: не удалось определить дату документа"

    document_date = parse_document_date(metadata.get("document_date", ""))
    if document_date is None:
        return "Отклонено: не удалось определить дату документа"

    if document_date < MINZDRAV_MIN_DATE:
        return (
            "Отклонено: дата документа раньше "
            f"{MINZDRAV_MIN_DATE.isoformat()}"
        )

    return None


def main() -> int:
    """Точка входа."""
    dependencies = ensure_dependencies()
    if dependencies is None:
        return 1

    requests_module, beautiful_soup_class = dependencies

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    try:
        response = requests_module.get(TARGET_URL, headers=headers, timeout=TIMEOUT_SECONDS)
    except Exception as exc:
        error_payload = {
            "status": "error",
            "source": SOURCE_NAME,
            "url": TARGET_URL,
            "error": f"{type(exc).__name__}: {exc}",
        }
        print(f"Не удалось получить страницу {TARGET_URL}")
        print(error_payload["error"])
        save_json(ALL_LINKS_OUTPUT_PATH, error_payload)
        save_json(FILTERED_OUTPUT_PATH, error_payload)
        save_json(REJECTED_OUTPUT_PATH, error_payload)
        print(f"Ошибка сохранена в: {ALL_LINKS_OUTPUT_PATH}")
        print(f"Ошибка сохранена в: {FILTERED_OUTPUT_PATH}")
        print(f"Ошибка сохранена в: {REJECTED_OUTPUT_PATH}")
        return 1

    html_text = response.text
    HTML_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    HTML_OUTPUT_PATH.write_text(html_text, encoding="utf-8")

    soup = beautiful_soup_class(html_text, "html.parser")

    document_metadata_map = build_document_metadata_map(soup)

    all_links: list[dict[str, str]] = []
    filtered_links: list[dict[str, str]] = []
    rejected_links: list[dict[str, str]] = []
    seen_urls: set[str] = set()

    # Собираем все уникальные ссылки со страницы.
    for tag in soup.find_all("a", href=True):
        href = str(tag.get("href", "")).strip()
        title = tag.get_text(" ", strip=True)

        if not is_allowed_href(href):
            continue

        absolute_url = urljoin(TARGET_URL, href)
        parsed_url = urlparse(absolute_url)
        if not parsed_url.scheme or not parsed_url.netloc:
            continue

        if absolute_url in seen_urls:
            continue
        seen_urls.add(absolute_url)

        metadata = document_metadata_map.get(absolute_url, {})
        effective_title = metadata.get("title") or title

        link_item = make_link_item(effective_title, absolute_url)
        document_date = metadata.get("document_date", "").strip()
        if document_date:
            link_item["document_date"] = document_date
        all_links.append(link_item)

        rejection_reason = classify_document_link(effective_title, absolute_url, document_metadata_map)
        if rejection_reason is None:
            filtered_links.append(link_item)
        else:
            rejected_item = make_rejected_link_item(effective_title, absolute_url, rejection_reason)
            if document_date:
                rejected_item["document_date"] = document_date
            rejected_links.append(rejected_item)

    save_json(ALL_LINKS_OUTPUT_PATH, all_links)
    save_json(FILTERED_OUTPUT_PATH, filtered_links)
    save_json(REJECTED_OUTPUT_PATH, rejected_links)

    print(f"HTTP-статус ответа: {response.status_code}")
    print(f"Всего ссылок найдено: {len(all_links)}")
    print(f"Ссылок попало в filtered: {len(filtered_links)}")
    print(f"Ссылок попало в rejected: {len(rejected_links)}")
    print(f"HTML сохранён в: {HTML_OUTPUT_PATH}")
    print(f"Все ссылки сохранены в: {ALL_LINKS_OUTPUT_PATH}")
    print(f"Filtered сохранён в: {FILTERED_OUTPUT_PATH}")
    print(f"Rejected сохранён в: {REJECTED_OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
