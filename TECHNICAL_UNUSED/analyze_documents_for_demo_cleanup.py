#!/usr/bin/env python3
"""Безопасный анализ documents.json перед очисткой демонстрационных данных."""

from __future__ import annotations

import json
import os


DOCUMENTS_PATH = os.path.join("data", "documents.json")
REPORT_PATH = os.path.join("data", "documents_demo_cleanup_report.txt")


def load_documents(file_path):
    """Читает список документов из JSON-файла."""
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


def is_government_document(document):
    """Проверяет, относится ли документ к Government.ru."""
    source = str(document.get("source", ""))
    document_id = str(document.get("id", ""))
    original_url = str(document.get("original_url", ""))

    if "Правительство" in source:
        return True

    if "Government" in source:
        return True

    if document_id.startswith("gov_"):
        return True

    if "government.ru" in original_url:
        return True

    return False


def group_by_source(documents):
    """Считает количество документов по каждому источнику."""
    grouped = {}

    for document in documents:
        source = str(document.get("source", "Без источника")).strip()
        if not source:
            source = "Без источника"
        grouped[source] = grouped.get(source, 0) + 1

    return grouped


def build_report_lines(documents):
    """Формирует строки текстового отчёта."""
    total_count = len(documents)
    grouped_sources = group_by_source(documents)
    government_documents = [document for document in documents if is_government_document(document)]
    remaining_count = total_count - len(government_documents)

    lines = []
    lines.append("Анализ documents.json перед очисткой демонстрационных данных")
    lines.append("")
    lines.append("Общая статистика")
    lines.append("Всего документов: {0}".format(total_count))
    lines.append("")
    lines.append("Группировка по источникам")

    for source_name in sorted(grouped_sources):
        lines.append("- {0}: {1}".format(source_name, grouped_sources[source_name]))

    lines.append("")
    lines.append("Документы Government.ru")
    lines.append("Найдено документов Government.ru: {0}".format(len(government_documents)))

    for index, document in enumerate(government_documents, start=1):
        lines.append(
            "{0}. id={1} | source={2} | original_url={3} | title={4}".format(
                index,
                document.get("id", ""),
                document.get("source", ""),
                document.get("original_url", ""),
                document.get("title", ""),
            )
        )

    lines.append("")
    lines.append("Если убрать Government.ru")
    lines.append("Останется документов: {0}".format(remaining_count))
    lines.append("")

    return lines


def save_report(file_path, lines):
    """Сохраняет текстовый отчёт на диск."""
    with open(file_path, "w", encoding="utf-8") as file:
        file.write("\n".join(lines) + "\n")


def main():
    """Точка входа."""
    if not os.path.exists(DOCUMENTS_PATH):
        print("Не найден файл: {0}".format(DOCUMENTS_PATH))
        return

    try:
        documents = load_documents(DOCUMENTS_PATH)
    except Exception as error:
        print("Ошибка при чтении {0}: {1}".format(DOCUMENTS_PATH, error))
        return

    if not isinstance(documents, list):
        print("Файл {0} должен содержать список документов.".format(DOCUMENTS_PATH))
        return

    report_lines = build_report_lines(documents)
    save_report(REPORT_PATH, report_lines)

    for line in report_lines:
        print(line)

    print("Отчёт сохранён в: {0}".format(REPORT_PATH))


if __name__ == "__main__":
    main()
