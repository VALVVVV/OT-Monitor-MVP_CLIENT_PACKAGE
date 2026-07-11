#!/usr/bin/env python3
"""Диагностический скрипт проверки доступности нормативных источников.

Скрипт можно запускать вручную, например:
    python check_sources_access.py --label vpn_on
    python check_sources_access.py --label vpn_off

Он проверяет доступность заданных URL через HTTP GET, выводит краткую
таблицу в терминал и сохраняет полный JSON-отчёт в папку data.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


URLS_TO_CHECK = [
    "https://government.ru/docs/",
    "https://publication.pravo.gov.ru/",
    "https://publication.pravo.gov.ru/api/Documents?PageSize=5&Index=1",
    "https://mintrud.gov.ru/docs",
    "https://mchs.gov.ru/",
    "https://rospotrebnadzor.ru/",
    "https://rostrud.gov.ru/",
    "https://minzdrav.gov.ru/documents",
    "https://www.rst.gov.ru/",
    "https://regulation.gov.ru/",
    "https://nac.gov.ru/",
]

REQUEST_TIMEOUT_SECONDS = 20
DEFAULT_LABEL = "default"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)


def parse_args() -> argparse.Namespace:
    """Читает параметры командной строки."""
    parser = argparse.ArgumentParser(
        description=(
            "Проверка доступности нормативных источников и сохранение "
            "диагностического JSON-отчёта."
        )
    )
    parser.add_argument(
        "--label",
        default=DEFAULT_LABEL,
        help=(
            "Метка запуска для имени JSON-файла. "
            "Например: vpn_on, vpn_off. По умолчанию: default."
        ),
    )
    return parser.parse_args()


def ensure_dependencies() -> tuple[Any, Any] | None:
    """Проверяет наличие requests и BeautifulSoup.

    Если библиотек нет, выводит понятную подсказку по установке.
    """
    missing_packages: list[str] = []

    try:
        import requests  # type: ignore
    except ImportError:
        requests = None
        missing_packages.append("requests")

    try:
        from bs4 import BeautifulSoup  # type: ignore
    except ImportError:
        BeautifulSoup = None
        missing_packages.append("beautifulsoup4")

    if missing_packages:
        print("Не удалось запустить проверку: отсутствуют нужные библиотеки.")
        print("Установите зависимости командой:")
        print(f"pip install {' '.join(missing_packages)}")
        return None

    return requests, BeautifulSoup


def normalize_label(label: str) -> str:
    """Приводит метку к безопасному виду для имени файла."""
    cleaned = re.sub(r"[^0-9A-Za-z_-]+", "_", label.strip())
    return cleaned or DEFAULT_LABEL


def extract_title(content_type: str | None, response_text: str, soup_class: Any) -> str | None:
    """Извлекает title только для HTML-документов."""
    if not content_type:
        return None

    if "html" not in content_type.lower():
        return None

    try:
        soup = soup_class(response_text, "html.parser")
        if soup.title and soup.title.string:
            title = soup.title.string.strip()
            return title or None
    except Exception:
        return None

    return None


def check_url(url: str, requests_module: Any, soup_class: Any) -> dict[str, Any]:
    """Проверяет один URL и возвращает результат в виде словаря."""
    result: dict[str, Any] = {
        "url": url,
        "status": "error",
        "http_status_code": None,
        "elapsed_seconds": None,
        "content_type": None,
        "html_size": None,
        "page_title": None,
        "error": None,
    }

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/json,application/xhtml+xml,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    try:
        response = requests_module.get(url, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)
        content_type = response.headers.get("Content-Type")
        response_text = response.text
        html_size = len(response.content)
        elapsed_seconds = round(response.elapsed.total_seconds(), 3)

        result.update(
            {
                "status": "ok",
                "http_status_code": response.status_code,
                "elapsed_seconds": elapsed_seconds,
                "content_type": content_type,
                "html_size": html_size,
                "page_title": extract_title(content_type, response_text, soup_class),
            }
        )
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"

    return result


def print_results_table(results: list[dict[str, Any]]) -> None:
    """Печатает краткую таблицу результатов в терминал."""
    headers = ["URL", "status", "HTTP", "sec", "size"]
    rows: list[list[str]] = []

    for item in results:
        rows.append(
            [
                item["url"],
                item["status"],
                str(item["http_status_code"] or "-"),
                (
                    f"{item['elapsed_seconds']:.3f}"
                    if isinstance(item["elapsed_seconds"], (int, float))
                    else "-"
                ),
                str(item["html_size"] or "-"),
            ]
        )

    col_widths = []
    for index, header in enumerate(headers):
        max_width = len(header)
        for row in rows:
            max_width = max(max_width, len(row[index]))
        col_widths.append(max_width)

    def format_row(values: list[str]) -> str:
        return " | ".join(
            value.ljust(col_widths[index]) for index, value in enumerate(values)
        )

    print(format_row(headers))
    print("-+-".join("-" * width for width in col_widths))
    for row in rows:
        print(format_row(row))


def save_report(report_path: Path, payload: dict[str, Any]) -> None:
    """Сохраняет JSON-отчёт на диск."""
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> int:
    """Точка входа скрипта."""
    args = parse_args()
    dependencies = ensure_dependencies()
    if dependencies is None:
        return 1

    requests_module, soup_class = dependencies

    script_dir = Path(__file__).resolve().parent
    label = normalize_label(args.label)
    report_path = script_dir / "data" / f"source_access_report_{label}.json"

    started_at = datetime.now(timezone.utc).astimezone().isoformat()
    results = []

    for url in URLS_TO_CHECK:
        results.append(check_url(url, requests_module, soup_class))

    payload = {
        "label": label,
        "started_at": started_at,
        "timeout_seconds": REQUEST_TIMEOUT_SECONDS,
        "sources_checked": len(URLS_TO_CHECK),
        "results": results,
    }

    save_report(report_path, payload)
    print_results_table(results)
    print()
    print(f"Полный отчёт сохранён в: {report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
