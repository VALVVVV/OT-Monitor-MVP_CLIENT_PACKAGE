#!/usr/bin/env python3
"""Разведочный скрипт для проверки страницы документов Минтруда.

Скрипт:
1. Загружает страницу https://mintrud.gov.ru/docs
2. Сохраняет сырой HTML
3. Ищет возможные ссылки на документы
4. Выводит краткую сводку в терминал
5. Сохраняет результат в JSON
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse


TARGET_URL = "https://mintrud.gov.ru/docs"
SOURCE_NAME = "Минтруд России"
TIMEOUT_SECONDS = 20
HTML_OUTPUT_PATH = Path("runtime/parser_artifacts/mintrud_docs_page.html")
JSON_OUTPUT_PATH = Path("runtime/parser_artifacts/mintrud_links_inspection.json")
FILTERED_JSON_OUTPUT_PATH = Path("runtime/parser_artifacts/mintrud_documents_filtered.json")
REJECTED_JSON_OUTPUT_PATH = Path("runtime/parser_artifacts/mintrud_links_rejected.json")
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)
MAX_TERMINAL_LINKS = 20


def ensure_dependencies() -> tuple[Any, Any] | None:
    """Проверяет наличие requests и BeautifulSoup."""
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


def save_json(payload: Any, output_path: Path) -> None:
    """Сохраняет JSON в UTF-8 с отступами."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def is_relevant_link(href: str) -> bool:
    """Проверяет, похожа ли ссылка на внутреннюю страницу или документ Минтруда."""
    href_lower = href.lower().strip()
    if not href_lower or href_lower.startswith(("#", "javascript:", "mailto:", "tel:")):
        return False

    parsed = urlparse(href_lower)

    # Разрешаем относительные ссылки.
    if not parsed.netloc:
        return True

    # Разрешаем только ссылки на домен mintrud.gov.ru.
    return parsed.netloc.endswith("mintrud.gov.ru")


def looks_like_document_link(full_url: str, link_text: str) -> bool:
    """Грубая эвристика для отбора потенциально полезных ссылок."""
    url_lower = full_url.lower()
    text_lower = link_text.lower()

    url_markers = [
        "/docs",
        "/document",
        "/documents",
        ".pdf",
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
        ".rtf",
    ]
    text_markers = [
        "документ",
        "приказ",
        "постанов",
        "письмо",
        "проект",
        "утверж",
        "перечень",
        "правил",
        "поряд",
        "форма",
    ]

    if any(marker in url_lower for marker in url_markers):
        return True

    if any(marker in text_lower for marker in text_markers):
        return True

    return False


def find_possible_date(tag: Any) -> str:
    """Пытается найти дату рядом со ссылкой."""
    date_patterns = [
        r"\b\d{1,2}\.\d{1,2}\.\d{4}\b",
        r"\b\d{4}-\d{1,2}-\d{1,2}\b",
        (
            r"\b\d{1,2}\s+"
            r"(?:января|февраля|марта|апреля|мая|июня|июля|августа|"
            r"сентября|октября|ноября|декабря)\s+\d{4}\b"
        ),
    ]
    combined_pattern = re.compile("|".join(date_patterns), re.IGNORECASE)

    texts_to_check: list[str] = []
    current_text = tag.get_text(" ", strip=True)
    if current_text:
        texts_to_check.append(current_text)

    if tag.parent is not None:
        parent_text = tag.parent.get_text(" ", strip=True)
        if parent_text:
            texts_to_check.append(parent_text)

    for sibling in list(tag.previous_siblings)[:3]:
        sibling_text = sibling.get_text(" ", strip=True) if hasattr(sibling, "get_text") else str(sibling)
        if sibling_text:
            texts_to_check.append(sibling_text)

    for sibling in list(tag.next_siblings)[:3]:
        sibling_text = sibling.get_text(" ", strip=True) if hasattr(sibling, "get_text") else str(sibling)
        if sibling_text:
            texts_to_check.append(sibling_text)

    for text in texts_to_check:
        match = combined_pattern.search(text)
        if match:
            return match.group(0)

    return "-"


def fetch_page(requests_module: Any) -> Any:
    """Загружает целевую страницу через requests."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    return requests_module.get(TARGET_URL, headers=headers, timeout=TIMEOUT_SECONDS)


def build_output_item(title: str, url: str, possible_date: str) -> dict[str, str]:
    """Формирует объект результата в требуемом формате."""
    return {
        "source": SOURCE_NAME,
        "title": title,
        "url": url,
        "possible_date": possible_date,
        "note": "Предварительная ссылка, требуется проверка структуры",
    }


def determine_document_kind(url: str) -> str:
    """Определяет тип документа по URL."""
    url_lower = url.lower()

    if "/docs/mintrud/orders/" in url_lower:
        return "order"

    if "/docs/agreements/" in url_lower:
        return "agreement"

    return "unknown"


def passes_document_filter(url: str) -> bool:
    """Мягкий фильтр для ссылок, похожих на реальные документы Минтруда."""
    url_lower = url.lower()
    allowed_fragments = [
        "/docs/mintrud/orders/",
        "/docs/agreements/",
    ]
    return any(fragment in url_lower for fragment in allowed_fragments)


def build_filtered_document_item(item: dict[str, str]) -> dict[str, str]:
    """Формирует объект для итогового списка отфильтрованных документов."""
    return {
        "source": SOURCE_NAME,
        "title": item["title"],
        "url": item["url"],
        "possible_date": item["possible_date"],
        "document_kind": determine_document_kind(item["url"]),
        "note": "Отфильтровано как возможный документ Минтруда",
    }


def main() -> int:
    """Точка входа."""
    dependencies = ensure_dependencies()
    if dependencies is None:
        return 1

    requests_module, beautiful_soup_class = dependencies

    try:
        response = fetch_page(requests_module)
    except Exception as exc:
        error_payload = {
            "status": "error",
            "source": SOURCE_NAME,
            "url": TARGET_URL,
            "error": f"{type(exc).__name__}: {exc}",
        }
        print(f"Не удалось получить страницу {TARGET_URL}")
        print(error_payload["error"])
        save_json(error_payload, JSON_OUTPUT_PATH)
        save_json(error_payload, FILTERED_JSON_OUTPUT_PATH)
        save_json(error_payload, REJECTED_JSON_OUTPUT_PATH)
        print(f"Ошибка сохранена в: {JSON_OUTPUT_PATH}")
        print(f"Ошибка сохранена в: {FILTERED_JSON_OUTPUT_PATH}")
        print(f"Ошибка сохранена в: {REJECTED_JSON_OUTPUT_PATH}")
        return 1

    html_text = response.text
    html_bytes = response.content
    title = None

    HTML_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    HTML_OUTPUT_PATH.write_text(html_text, encoding="utf-8")

    soup = beautiful_soup_class(html_text, "html.parser")
    if soup.title and soup.title.string:
        title = soup.title.string.strip() or None

    print(f"HTTP-код: {response.status_code}")
    print(f"Размер HTML: {len(html_bytes)} байт")
    print(f"Title: {title or '-'}")
    print(f"HTML сохранён в: {HTML_OUTPUT_PATH}")

    found_links: list[dict[str, str]] = []
    seen_urls: set[str] = set()

    # Проходим по всем ссылкам и оставляем только потенциально полезные.
    for link in soup.find_all("a", href=True):
        href = str(link.get("href", "")).strip()
        link_text = link.get_text(" ", strip=True)

        if not href or not link_text:
            continue

        if not is_relevant_link(href):
            continue

        full_url = urljoin(TARGET_URL, href)
        if not looks_like_document_link(full_url, link_text):
            continue

        if full_url in seen_urls:
            continue
        seen_urls.add(full_url)

        possible_date = find_possible_date(link)
        found_links.append(build_output_item(link_text, full_url, possible_date))

    filtered_documents = [
        build_filtered_document_item(item)
        for item in found_links
        if passes_document_filter(item["url"])
    ]
    rejected_links = [
        item
        for item in found_links
        if not passes_document_filter(item["url"])
    ]

    if not found_links:
        print("Подходящие ссылки на странице не найдены.")
    else:
        print()
        print(f"Найдено уникальных ссылок: {len(found_links)}")
        print(f"Первые {min(MAX_TERMINAL_LINKS, len(found_links))} ссылок:")
        for index, item in enumerate(found_links[:MAX_TERMINAL_LINKS], start=1):
            print(f"{index}. {item['title']}")
            print(f"   URL: {item['url']}")
            print(f"   Дата: {item['possible_date']}")

    save_json(found_links, JSON_OUTPUT_PATH)
    save_json(filtered_documents, FILTERED_JSON_OUTPUT_PATH)
    save_json(rejected_links, REJECTED_JSON_OUTPUT_PATH)
    print()
    print(f"Все предварительные ссылки сохранены в: {JSON_OUTPUT_PATH}")
    print(f"Всего предварительных ссылок найдено: {len(found_links)}")
    print(f"Ссылок сохранено как документы: {len(filtered_documents)}")
    print(f"Ссылок отброшено: {len(rejected_links)}")
    print(f"Файл документов: {FILTERED_JSON_OUTPUT_PATH}")
    print(f"Файл отброшенных ссылок: {REJECTED_JSON_OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
