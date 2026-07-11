#!/usr/bin/env python3
"""Сравнение диагностических отчётов доступности источников.

Скрипт читает несколько JSON-отчётов, сопоставляет результаты по URL,
выводит краткую таблицу в терминал и сохраняет сводку в JSON и TXT.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


# Фиксированный список входных файлов согласно задаче.
REPORT_FILES = {
    "vpn_on": "source_access_report_vpn_on.json",
    "vpn_on_2": "source_access_report_vpn_on_2.json",
    "vpn_off": "source_access_report_vpn_off.json",
}


def load_report(report_path: Path) -> tuple[dict[str, Any] | None, str | None]:
    """Читает один JSON-отчёт.

    Возвращает:
    - словарь с данными, если файл удалось прочитать;
    - текст предупреждения, если файл отсутствует или повреждён.
    """
    if not report_path.exists():
        return None, f"Предупреждение: файл не найден: {report_path}"

    try:
        payload = json.loads(report_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, f"Предупреждение: файл повреждён или не является JSON: {report_path} ({exc})"
    except OSError as exc:
        return None, f"Предупреждение: не удалось прочитать файл: {report_path} ({exc})"

    if not isinstance(payload, dict):
        return None, f"Предупреждение: неожиданный формат отчёта: {report_path}"

    return payload, None


def index_results_by_url(report_payload: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    """Преобразует список results в словарь вида {url: result}."""
    if not report_payload:
        return {}

    raw_results = report_payload.get("results", [])
    if not isinstance(raw_results, list):
        return {}

    indexed: dict[str, dict[str, Any]] = {}
    for item in raw_results:
        if not isinstance(item, dict):
            continue
        url = item.get("url")
        if isinstance(url, str) and url:
            indexed[url] = item
    return indexed


def is_success(entry: dict[str, Any] | None) -> bool:
    """Считает источник успешно доступным только при корректном HTTP-ответе."""
    if not entry:
        return False

    status = entry.get("status")
    http_code = entry.get("http_status_code")
    return status == "ok" and isinstance(http_code, int) and 200 <= http_code < 400


def format_status(entry: dict[str, Any] | None) -> str:
    """Готовит короткое значение статуса для вывода в таблицу."""
    if entry is None:
        return "missing"

    status = entry.get("status") or "-"
    code = entry.get("http_status_code")
    if code is None:
        return str(status)
    return f"{status} ({code})"


def pick_value(entry: dict[str, Any] | None, key: str) -> Any:
    """Безопасно достаёт поле из результата одного запуска."""
    if entry is None:
        return None
    return entry.get(key)


def evaluate_source(
    vpn_on_entry: dict[str, Any] | None,
    vpn_on_2_entry: dict[str, Any] | None,
    vpn_off_entry: dict[str, Any] | None,
) -> str:
    """Даёт итоговую оценку по доступности источника.

    Логика:
    - успешным считается только ответ со статусом ok и HTTP 2xx/3xx;
    - если без VPN всё работает, а с VPN есть сбои, считаем, что без VPN лучше;
    - если доступность есть только в режимах VPN, так и пишем;
    - при смешанной картине без явного преимущества считаем источник нестабильным.
    """
    vpn_entries = [entry for entry in [vpn_on_entry, vpn_on_2_entry] if entry is not None]
    vpn_successes = [is_success(entry) for entry in vpn_entries]
    vpn_success_count = sum(vpn_successes)
    vpn_all_success = bool(vpn_entries) and all(vpn_successes)
    vpn_any_success = vpn_success_count > 0

    off_present = vpn_off_entry is not None
    off_success = is_success(vpn_off_entry)

    all_entries = [entry for entry in [vpn_on_entry, vpn_on_2_entry, vpn_off_entry] if entry is not None]
    total_success_count = sum(1 for entry in all_entries if is_success(entry))

    if total_success_count == 0:
        return "не работает ни в одном запуске"

    if off_success and vpn_all_success:
        return "стабильно доступен с VPN и без VPN"

    if off_success and not vpn_any_success:
        return "лучше работает без VPN"

    if vpn_any_success and not off_success:
        if vpn_all_success:
            return "работает только с VPN"
        return "нестабилен"

    if off_success and vpn_any_success and not vpn_all_success:
        return "лучше работает без VPN"

    if off_present or vpn_entries:
        return "нестабилен"

    return "не работает ни в одном запуске"


def build_summary_rows(report_indexes: dict[str, dict[str, dict[str, Any]]]) -> list[dict[str, Any]]:
    """Собирает итоговые строки сравнения по всем найденным URL."""
    urls = sorted(
        {
            url
            for report_index in report_indexes.values()
            for url in report_index.keys()
        }
    )

    summary_rows: list[dict[str, Any]] = []
    for url in urls:
        vpn_on_entry = report_indexes["vpn_on"].get(url)
        vpn_on_2_entry = report_indexes["vpn_on_2"].get(url)
        vpn_off_entry = report_indexes["vpn_off"].get(url)

        summary_rows.append(
            {
                "url": url,
                "vpn_on": {
                    "status": pick_value(vpn_on_entry, "status"),
                    "http_status_code": pick_value(vpn_on_entry, "http_status_code"),
                    "elapsed_seconds": pick_value(vpn_on_entry, "elapsed_seconds"),
                    "html_size": pick_value(vpn_on_entry, "html_size"),
                    "error": pick_value(vpn_on_entry, "error"),
                },
                "vpn_on_2": {
                    "status": pick_value(vpn_on_2_entry, "status"),
                    "http_status_code": pick_value(vpn_on_2_entry, "http_status_code"),
                    "elapsed_seconds": pick_value(vpn_on_2_entry, "elapsed_seconds"),
                    "html_size": pick_value(vpn_on_2_entry, "html_size"),
                    "error": pick_value(vpn_on_2_entry, "error"),
                },
                "vpn_off": {
                    "status": pick_value(vpn_off_entry, "status"),
                    "http_status_code": pick_value(vpn_off_entry, "http_status_code"),
                    "elapsed_seconds": pick_value(vpn_off_entry, "elapsed_seconds"),
                    "html_size": pick_value(vpn_off_entry, "html_size"),
                    "error": pick_value(vpn_off_entry, "error"),
                },
                "summary": evaluate_source(vpn_on_entry, vpn_on_2_entry, vpn_off_entry),
            }
        )

    return summary_rows


def print_table(summary_rows: list[dict[str, Any]]) -> None:
    """Выводит краткую таблицу в терминал."""
    headers = ["URL", "vpn_on", "vpn_on_2", "vpn_off", "вывод"]
    rows: list[list[str]] = []

    for item in summary_rows:
        rows.append(
            [
                item["url"],
                format_status(item.get("vpn_on")),
                format_status(item.get("vpn_on_2")),
                format_status(item.get("vpn_off")),
                item["summary"],
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


def build_text_summary(summary_rows: list[dict[str, Any]], warnings: list[str]) -> str:
    """Собирает текстовую версию отчёта для TXT-файла."""
    lines: list[str] = []
    lines.append("Сводка сравнения доступности источников")
    lines.append("")

    if warnings:
        lines.append("Предупреждения:")
        for warning in warnings:
            lines.append(f"- {warning}")
        lines.append("")

    for item in summary_rows:
        lines.append(f"URL: {item['url']}")
        lines.append(
            "vpn_on: "
            f"status={item['vpn_on']['status']}, "
            f"http={item['vpn_on']['http_status_code']}, "
            f"sec={item['vpn_on']['elapsed_seconds']}, "
            f"size={item['vpn_on']['html_size']}"
        )
        lines.append(
            "vpn_on_2: "
            f"status={item['vpn_on_2']['status']}, "
            f"http={item['vpn_on_2']['http_status_code']}, "
            f"sec={item['vpn_on_2']['elapsed_seconds']}, "
            f"size={item['vpn_on_2']['html_size']}"
        )
        lines.append(
            "vpn_off: "
            f"status={item['vpn_off']['status']}, "
            f"http={item['vpn_off']['http_status_code']}, "
            f"sec={item['vpn_off']['elapsed_seconds']}, "
            f"size={item['vpn_off']['html_size']}"
        )
        lines.append(f"Вывод: {item['summary']}")
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def save_outputs(data_dir: Path, payload: dict[str, Any], text_summary: str) -> None:
    """Сохраняет JSON- и TXT-версии сводного отчёта."""
    json_path = data_dir / "source_access_summary.json"
    txt_path = data_dir / "source_access_summary.txt"

    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    txt_path.write_text(text_summary, encoding="utf-8")


def main() -> int:
    """Точка входа."""
    script_dir = Path(__file__).resolve().parent
    data_dir = script_dir / "data"

    warnings: list[str] = []
    loaded_reports: dict[str, dict[str, Any] | None] = {}

    # Загружаем каждый отчёт отдельно, чтобы не падать, если какого-то файла нет.
    for report_key, report_filename in REPORT_FILES.items():
        report_path = data_dir / report_filename
        report_payload, warning = load_report(report_path)
        loaded_reports[report_key] = report_payload
        if warning:
            warnings.append(warning)

    report_indexes = {
        report_key: index_results_by_url(report_payload)
        for report_key, report_payload in loaded_reports.items()
    }

    summary_rows = build_summary_rows(report_indexes)
    payload = {
        "source_files": REPORT_FILES,
        "warnings": warnings,
        "sources_compared": len(summary_rows),
        "results": summary_rows,
    }

    text_summary = build_text_summary(summary_rows, warnings)
    save_outputs(data_dir, payload, text_summary)

    for warning in warnings:
        print(warning)

    if warnings:
        print()

    print_table(summary_rows)
    print()
    print(f"JSON-отчёт сохранён: {data_dir / 'source_access_summary.json'}")
    print(f"Текстовый отчёт сохранён: {data_dir / 'source_access_summary.txt'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
