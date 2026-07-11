#!/usr/bin/env python3
"""Безопасный перенос документов Минтруда в documents.json.

Скрипт:
1. Проверяет наличие нужных файлов.
2. Читает отфильтрованные документы Минтруда.
3. Добавляет только новые документы без дублей по URL.
4. Обновляет журнал проверок check_log.json.
"""

import json
import os
from datetime import datetime


MINTRUD_SOURCE_PATH = os.path.join("data", "mintrud_documents_filtered.json")
DOCUMENTS_PATH = os.path.join("data", "documents.json")
CHECK_LOG_PATH = os.path.join("data", "check_log.json")


def load_json_file(file_path):
    """Читает JSON-файл и возвращает его содержимое."""
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


def save_json_file(file_path, data):
    """Сохраняет данные в JSON-файл."""
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def build_existing_urls(documents):
    """Собирает все уже известные URL из documents.json."""
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


def build_next_document_id(documents, sequence_number):
    """Генерирует понятный идентификатор для нового документа Минтруда."""
    current_date = datetime.now().strftime("%Y%m%d")
    return "mintrud_{0}_{1:03d}".format(current_date, sequence_number)


def build_document_object(source_item, sequence_number):
    """Преобразует документ Минтруда в формат MVP."""
    found_date = datetime.now().date().isoformat()

    return {
        "id": build_next_document_id([], sequence_number),
        "found_date": found_date,
        "source_id": "mintrud",
        "source": "Минтруд России",
        "title": source_item.get("title", ""),
        "original_url": source_item.get("url", ""),
        "saved_file_path": "",
        "section": "Охрана труда",
        "topic": "Документы Минтруда",
        "summary": (
            "Документ найден на сайте Минтруда России. "
            "Требуется проверка инженером по охране труда."
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
        MINTRUD_SOURCE_PATH,
        DOCUMENTS_PATH,
        CHECK_LOG_PATH,
    ]

    # Сначала проверяем наличие всех обязательных файлов.
    for file_path in required_files:
        if not os.path.exists(file_path):
            print("Не найден обязательный файл: {0}".format(file_path))
            return

    try:
        mintrud_documents = load_json_file(MINTRUD_SOURCE_PATH)
        documents = load_json_file(DOCUMENTS_PATH)
        check_log = load_json_file(CHECK_LOG_PATH)
    except Exception as error:
        print("Ошибка при чтении JSON-файлов: {0}".format(error))
        return

    if not isinstance(mintrud_documents, list):
        print("Файл {0} должен содержать список документов.".format(MINTRUD_SOURCE_PATH))
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

    # Чтобы ID не пересекались с уже добавленными сегодня документами Минтруда,
    # ищем следующий свободный порядковый номер по существующим записям.
    current_date = datetime.now().strftime("%Y%m%d")
    existing_ids = set()
    for document in documents:
        if isinstance(document, dict):
            document_id = document.get("id", "")
            if document_id:
                existing_ids.add(document_id)

    while "mintrud_{0}_{1:03d}".format(current_date, next_sequence_number) in existing_ids:
        next_sequence_number += 1

    # Добавляем только те документы, URL которых ещё нет в documents.json.
    for source_item in mintrud_documents:
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

        while "mintrud_{0}_{1:03d}".format(current_date, next_sequence_number) in existing_ids:
            next_sequence_number += 1

    try:
        save_json_file(DOCUMENTS_PATH, documents)
    except Exception as error:
        print("Ошибка при сохранении {0}: {1}".format(DOCUMENTS_PATH, error))
        return

    # После обновления documents.json записываем результат проверки в журнал.
    check_log_entry = {
        "id": "check_mintrud_{0}".format(datetime.now().strftime("%Y%m%d%H%M%S")),
        "checked_at": datetime.now().isoformat(timespec="seconds"),
        "source_id": "mintrud",
        "source": "Минтруд России",
        "result": "success",
        "found_count": len(mintrud_documents),
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

    print("Документов найдено в mintrud_documents_filtered.json: {0}".format(len(mintrud_documents)))
    print("Добавлено новых документов: {0}".format(added_count))
    print("Пропущено как дубли: {0}".format(skipped_duplicates))
    print("Запись в check_log.json создана.")


if __name__ == "__main__":
    main()
