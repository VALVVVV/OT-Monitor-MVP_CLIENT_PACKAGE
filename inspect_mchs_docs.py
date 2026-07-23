#!/usr/bin/env python3
"""Разведочный скрипт для страницы документов МЧС России."""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse


TARGET_URL = "https://mchs.gov.ru/dokumenty/vse-dokumenty"
SOURCE_NAME = "МЧС России"
HTML_OUTPUT_PATH = Path("runtime/parser_artifacts/mchs_docs_page.html")
ALL_LINKS_OUTPUT_PATH = Path("runtime/parser_artifacts/mchs_links_inspection.json")
FILTERED_OUTPUT_PATH = Path("runtime/parser_artifacts/mchs_documents_filtered.json")
FILES_OUTPUT_PATH = Path("runtime/parser_artifacts/mchs_document_files.json")
REJECTED_OUTPUT_PATH = Path("runtime/parser_artifacts/mchs_links_rejected.json")
TIMEOUT_SECONDS = 20
MIN_DOCUMENT_DATE = date(2026, 6, 1)
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


def make_link_item(title: str, url: str, file_url: str = "") -> dict[str, str]:
    """Формирует объект ссылки в нужном формате."""
    item = {
        "source": SOURCE_NAME,
        "title": title,
        "url": url,
        "note": "Найдена ссылка на странице МЧС",
    }
    if file_url:
        item["file_url"] = file_url
    return item


def make_rejected_link_item(title: str, url: str, reason: str) -> dict[str, str]:
    """Формирует объект отклонённой ссылки с причиной."""
    return {
        "source": SOURCE_NAME,
        "title": title,
        "url": url,
        "note": reason,
    }


def is_document_file(url: str) -> bool:
    """Проверяет, является ли ссылка файлом-вложением."""
    url_lower = url.lower()
    return url_lower.endswith((".pdf", ".doc", ".docx", ".xls", ".xlsx"))


def normalize_text(text: str) -> str:
    """Нормализует пробелы в тексте."""
    return " ".join(text.split())


def resolve_link_title(tag: Any) -> str:
    """Пытается получить полезный заголовок даже для ссылок вида Скачать."""
    raw_title = normalize_text(tag.get_text(" ", strip=True))
    if raw_title.lower() not in {"", "скачать", "документ"}:
        return raw_title

    candidates: list[str] = []
    for attr_name in ("title", "aria-label"):
        attr_value = normalize_text(str(tag.get(attr_name, "")).strip())
        if attr_value:
            candidates.append(attr_value)

    if tag.parent is not None:
        candidates.append(normalize_text(tag.parent.get_text(" ", strip=True)))

    for sibling in list(tag.previous_siblings)[:3]:
        sibling_text = sibling.get_text(" ", strip=True) if hasattr(sibling, "get_text") else str(sibling)
        candidates.append(normalize_text(sibling_text))

    for sibling in list(tag.next_siblings)[:3]:
        sibling_text = sibling.get_text(" ", strip=True) if hasattr(sibling, "get_text") else str(sibling)
        candidates.append(normalize_text(sibling_text))

    for candidate in candidates:
        candidate_lower = candidate.lower()
        if candidate_lower in {"", "скачать", "документ"}:
            continue
        if len(candidate) <= 2:
            continue
        return candidate

    return raw_title


def extract_doc_item_date(doc_item: Any) -> date | None:
    """Извлекает дату документа из блока doc-item."""
    date_tag = doc_item.select_one(".doc-item__date")
    if date_tag is None:
        return None

    date_text = normalize_text(date_tag.get_text(" ", strip=True))
    import re

    match = re.search(r"(\d{2})\.(\d{2})\.(\d{4})", date_text)
    if match is None:
        return None

    day_value, month_value, year_value = match.groups()
    try:
        return date(int(year_value), int(month_value), int(day_value))
    except ValueError:
        return None


def classify_document_page(title: str, url: str, document_date: date | None) -> str | None:
    """Возвращает причину отклонения или None, если это подходящая страница документа."""
    clean_title = normalize_text(title.strip())
    url_lower = url.lower()

    if not clean_title:
        return "Отклонено: пустой заголовок"

    if "/dokumenty/vse-dokumenty/" not in url_lower:
        return "Отклонено: ссылка вне раздела документов"

    if document_date is None:
        return "Отклонено: не удалось определить дату документа"

    if document_date < MIN_DOCUMENT_DATE:
        return "Отклонено: документ раньше 2026-06-01"

    return None


def build_doc_item_records(soup: Any) -> tuple[list[dict[str, str]], list[dict[str, str]], dict[str, str]]:
    """Собирает документы по блокам doc-item и связывает страницу документа с файлом."""
    filtered_links: list[dict[str, str]] = []
    document_files: list[dict[str, str]] = []
    preferred_titles_by_url: dict[str, str] = {}
    seen_page_urls: set[str] = set()
    seen_file_urls: set[str] = set()

    for doc_item in soup.select(".doc-item"):
        title_tag = doc_item.select_one(".doc-item__title[href]")
        if title_tag is None:
            continue

        title = normalize_text(title_tag.get_text(" ", strip=True))
        page_href = str(title_tag.get("href", "")).strip()
        if not title or not page_href:
            continue

        page_url = urljoin(TARGET_URL, page_href)
        preferred_titles_by_url[page_url] = title
        document_date = extract_doc_item_date(doc_item)

        file_tag = doc_item.select_one(".doc-item__file-link[href]")
        file_url = ""
        if file_tag is not None:
            file_href = str(file_tag.get("href", "")).strip()
            if file_href:
                candidate_file_url = urljoin(TARGET_URL, file_href)
                if is_document_file(candidate_file_url):
                    file_url = candidate_file_url
                    preferred_titles_by_url[file_url] = title
                    if file_url not in seen_file_urls:
                        document_files.append(make_link_item(title, file_url))
                        seen_file_urls.add(file_url)

        rejection_reason = classify_document_page(title, page_url, document_date)
        if rejection_reason is None and page_url not in seen_page_urls:
            filtered_links.append(make_link_item(title, page_url, file_url=file_url))
            seen_page_urls.add(page_url)

    return filtered_links, document_files, preferred_titles_by_url


def is_allowed_href(href: str) -> bool:
    """Отсекает пустые и служебные href."""
    href = href.strip().lower()
    if not href:
        return False
    if href.startswith(("#", "javascript:", "mailto:", "tel:")):
        return False
    return True


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
        save_json(FILES_OUTPUT_PATH, error_payload)
        save_json(REJECTED_OUTPUT_PATH, error_payload)
        print(f"Ошибка сохранена в: {ALL_LINKS_OUTPUT_PATH}")
        print(f"Ошибка сохранена в: {FILTERED_OUTPUT_PATH}")
        print(f"Ошибка сохранена в: {FILES_OUTPUT_PATH}")
        print(f"Ошибка сохранена в: {REJECTED_OUTPUT_PATH}")
        return 1

    html_text = response.text
    HTML_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    HTML_OUTPUT_PATH.write_text(html_text, encoding="utf-8")

    soup = beautiful_soup_class(html_text, "html.parser")

    all_links: list[dict[str, str]] = []
    filtered_links, document_files, preferred_titles_by_url = build_doc_item_records(soup)
    rejected_links: list[dict[str, str]] = []
    seen_urls: set[str] = set()

    # Собираем все уникальные ссылки со страницы.
    for tag in soup.find_all("a", href=True):
        href = str(tag.get("href", "")).strip()

        if not is_allowed_href(href):
            continue

        absolute_url = urljoin(TARGET_URL, href)
        parsed_url = urlparse(absolute_url)
        if not parsed_url.scheme or not parsed_url.netloc:
            continue

        if absolute_url in seen_urls:
            continue
        seen_urls.add(absolute_url)

        title = preferred_titles_by_url.get(absolute_url, resolve_link_title(tag))

        link_item = make_link_item(title, absolute_url)
        all_links.append(link_item)

        rejection_reason = "Отклонено: ссылка вне списка документов по дате"
        if absolute_url in preferred_titles_by_url and not is_document_file(absolute_url):
            rejection_reason = None
        if rejection_reason is not None:
            rejected_links.append(make_rejected_link_item(title, absolute_url, rejection_reason))

    save_json(ALL_LINKS_OUTPUT_PATH, all_links)
    save_json(FILTERED_OUTPUT_PATH, filtered_links)
    save_json(FILES_OUTPUT_PATH, document_files)
    save_json(REJECTED_OUTPUT_PATH, rejected_links)

    print(f"HTTP-статус ответа: {response.status_code}")
    print(f"Всего ссылок найдено: {len(all_links)}")
    print(f"Документов в filtered: {len(filtered_links)}")
    print(f"Файлов-вложений найдено: {len(document_files)}")
    print(f"Ссылок попало в rejected: {len(rejected_links)}")
    print(f"HTML сохранён в: {HTML_OUTPUT_PATH}")
    print(f"Все ссылки сохранены в: {ALL_LINKS_OUTPUT_PATH}")
    print(f"Filtered сохранён в: {FILTERED_OUTPUT_PATH}")
    print(f"Файлы сохранены в: {FILES_OUTPUT_PATH}")
    print(f"Rejected сохранён в: {REJECTED_OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
