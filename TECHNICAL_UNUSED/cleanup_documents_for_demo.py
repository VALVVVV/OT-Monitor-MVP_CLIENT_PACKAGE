#!/usr/bin/env python3
"""Безопасная очистка documents.json от документов Government.ru."""

from __future__ import annotations

import json
import os


DOCUMENTS_PATH = os.path.join("data", "documents.json")
BACKUP_PATH = os.path.join("data", "documents_backup_auto_before_cleanup_run.json")
REPORT_PATH = os.path.join("data", "documents_cleanup_result.txt")


def load_documents(file_path):
    """Читает список документов из JSON-файла."""
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


def save_json(file_path, data):
    """Сохраняет данные в JSON-файл."""
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def save_text(file_path, text):
    """Сохраняет текстовый отчёт."""
    with open(file_path, "w", encoding="utf-8") as file:
        file.write(text)


def is_government_document(document):
    """Определяет, относится ли документ к Government.ru."""
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


def build_report(before_count, removed_documents, remaining_documents):
    """Формирует текстовый отчёт по очистке."""
    removed_ids = [str(document.get("id", "")) for document in removed_documents]
    remaining_sources = sorted(
        {
            str(document.get("source", "Без источника")).strip() or "Без источника"
            for document in remaining_documents
        }
    )

    lines = []
    lines.append("Результат очистки documents.json для демонстрационного контура")
    lines.append("")
    lines.append("Документов до очистки: {0}".format(before_count))
    lines.append("Удалено документов Government.ru: {0}".format(len(removed_documents)))
    lines.append("Документов осталось: {0}".format(len(remaining_documents)))
    lines.append("")
    lines.append("Удалённые id:")

    if removed_ids:
        for document_id in removed_ids:
            lines.append("- {0}".format(document_id))
    else:
        lines.append("- нет")

    lines.append("")
    lines.append("Источники, оставшиеся после очистки:")

    if remaining_sources:
        for source in remaining_sources:
            lines.append("- {0}".format(source))
    else:
        lines.append("- нет")

    lines.append("")
    return "\n".join(lines)


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

    # Перед очисткой создаём дополнительную резервную копию.
    try:
        save_json(BACKUP_PATH, documents)
    except Exception as error:
        print("Ошибка при создании резервной копии {0}: {1}".format(BACKUP_PATH, error))
        return

    removed_documents = []
    remaining_documents = []

    # Удаляем только документы Government.ru, остальные записи сохраняем без изменений.
    for document in documents:
        if is_government_document(document):
            removed_documents.append(document)
        else:
            remaining_documents.append(document)

    try:
        save_json(DOCUMENTS_PATH, remaining_documents)
    except Exception as error:
        print("Ошибка при сохранении {0}: {1}".format(DOCUMENTS_PATH, error))
        return

    report_text = build_report(len(documents), removed_documents, remaining_documents)

    try:
        save_text(REPORT_PATH, report_text)
    except Exception as error:
        print("Ошибка при сохранении отчёта {0}: {1}".format(REPORT_PATH, error))
        return

    print("Документов до очистки: {0}".format(len(documents)))
    print("Удалено документов Government.ru: {0}".format(len(removed_documents)))
    print("Документов осталось: {0}".format(len(remaining_documents)))
    print("Резервная копия создана: {0}".format(BACKUP_PATH))
    print("Отчёт сохранён в: {0}".format(REPORT_PATH))


if __name__ == "__main__":
    main()
