#!/usr/bin/env python3
"""Безопасный перенос документов Минздрава в documents.json."""

import json
import os
from datetime import datetime


MINZDRAV_SOURCE_PATH = os.path.join("data", "minzdrav_documents_filtered.json")
DOCUMENTS_PATH = os.path.join("data", "documents.json")
CHECK_LOG_PATH = os.path.join("data", "check_log.json")


def load_json_file(file_path):
    """Читает JSON-файл и возвращает данные."""
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


def save_json_file(file_path, data):
    """Сохраняет данные в JSON-файл."""
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def build_existing_urls(documents):
    """Собирает все URL, которые уже есть в documents.json."""
    existing_urls = set()

    for document in documents:
        if not isinstance(document, dict):
            continue

        original_url = document.get("original_url", "")
        url = document.get("url", "")

        if original_url:
            existing_urls.add(original_url)
        if url:
            existing_urls.add(url)

    return existing_urls


def build_document_id(sequence_number):
    """Формирует ID нового документа Минздрава."""
    current_date = datetime.now().strftime("%Y%m%d")
    return "minzdrav_{0}_{1:03d}".format(current_date, sequence_number)


def build_document_object(source_item, sequence_number):
    """Преобразует запись Минздрава в формат документа MVP."""
    return {
        "id": build_document_id(sequence_number),
        "found_date": datetime.now().date().isoformat(),
        "source_id": "minzdrav",
        "source": "Минздрав России",
        "title": source_item.get("title", ""),
        "original_url": source_item.get("url", ""),
        "saved_file_path": "",
        "section": "Медицина",
        "topic": "Документы Минздрава",
        "summary": (
            "Документ найден на сайте Минздрава России. "
            "Требуется проверка инженером по охране труда "
            "или ответственным за медосмотры."
        ),
        "linked_doc_types": [],
        "status": "Новое",
        "engineer_comment": "",
        "clean_text": "",
        "key_requirements": [],
        "draft_recommendation": "",
        "draft_warning": "Черновик, требует проверки инженером",
    }


def main():
    """Основная логика скрипта."""
    required_files = [
        MINZDRAV_SOURCE_PATH,
        DOCUMENTS_PATH,
        CHECK_LOG_PATH,
    ]

    # Сначала проверяем наличие обязательных файлов.
    for file_path in required_files:
        if not os.path.exists(file_path):
            print("Не найден обязательный файл: {0}".format(file_path))
            return

    try:
        minzdrav_documents = load_json_file(MINZDRAV_SOURCE_PATH)
        documents = load_json_file(DOCUMENTS_PATH)
        check_log = load_json_file(CHECK_LOG_PATH)
    except Exception as error:
        print("Ошибка при чтении JSON-файлов: {0}".format(error))
        return

    if not isinstance(minzdrav_documents, list):
        print("Файл {0} должен содержать список документов.".format(MINZDRAV_SOURCE_PATH))
        return

    if not isinstance(documents, list):
        print("Файл {0} должен содержать список документов.".format(DOCUMENTS_PATH))
        return

    if not isinstance(check_log, list):
        print("Файл {0} должен содержать список записей.".format(CHECK_LOG_PATH))
        return

    existing_urls = build_existing_urls(documents)
    added_count = 0
    skipped_duplicates = 0
    next_sequence_number = 1
    current_date = datetime.now().strftime("%Y%m%d")

    # Находим следующий свободный номер ID для документов Минздрава за текущий день.
    existing_ids = set()
    for document in documents:
        if isinstance(document, dict):
            document_id = document.get("id", "")
            if document_id:
                existing_ids.add(document_id)

    while "minzdrav_{0}_{1:03d}".format(current_date, next_sequence_number) in existing_ids:
        next_sequence_number += 1

    # Добавляем только новые документы без дублей по URL.
    for source_item in minzdrav_documents:
        if not isinstance(source_item, dict):
            continue

        source_url = source_item.get("url", "")
        if not source_url:
            continue

        if source_url in existing_urls:
            skipped_duplicates += 1
            continue

        new_document = build_document_object(source_item, next_sequence_number)
        documents.append(new_document)
        existing_urls.add(source_url)
        existing_ids.add(new_document["id"])
        added_count += 1
        next_sequence_number += 1

        while "minzdrav_{0}_{1:03d}".format(current_date, next_sequence_number) in existing_ids:
            next_sequence_number += 1

    try:
        save_json_file(DOCUMENTS_PATH, documents)
    except Exception as error:
        print("Ошибка при сохранении {0}: {1}".format(DOCUMENTS_PATH, error))
        return

    # После обновления documents.json записываем результат проверки в check_log.json.
    check_log_entry = {
        "id": "check_minzdrav_{0}".format(datetime.now().strftime("%Y%m%d%H%M%S")),
        "checked_at": datetime.now().isoformat(timespec="seconds"),
        "source_id": "minzdrav",
        "source": "Минздрав России",
        "result": "success",
        "found_count": len(minzdrav_documents),
        "added_count": added_count,
        "skipped_duplicates": skipped_duplicates,
        "error": "",
    }
    check_log.append(check_log_entry)

    try:
        save_json_file(CHECK_LOG_PATH, check_log)
    except Exception as error:
        print("Ошибка при сохранении {0}: {1}".format(CHECK_LOG_PATH, error))
        return

    print(
        "Документов найдено в minzdrav_documents_filtered.json: {0}".format(
            len(minzdrav_documents)
        )
    )
    print("Добавлено новых документов: {0}".format(added_count))
    print("Пропущено как дубли: {0}".format(skipped_duplicates))
    print("Запись в check_log.json создана.")


if __name__ == "__main__":
    main()
