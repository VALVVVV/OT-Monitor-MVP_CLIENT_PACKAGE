import json
from pathlib import Path


# Пути к исходным данным относительно корня проекта.
BASE_DIR = Path(__file__).resolve().parent
GOVERNMENT_FOUND_PATH = BASE_DIR / "data" / "government_found_test.json"
DOCUMENTS_PATH = BASE_DIR / "data" / "documents.json"


def load_json_array(file_path: Path, file_label: str) -> list:
    """Безопасно загружает JSON-массив из файла."""
    if not file_path.exists():
        raise FileNotFoundError(f"Файл не найден: {file_path}")

    with file_path.open("r", encoding="utf-8") as file:
        content = file.read().strip()

    # Пустой файл трактуем как пустой список только для documents.json.
    if not content:
        if file_label == "documents":
            return []
        raise ValueError(f"Файл {file_path} пустой.")

    try:
        data = json.loads(content)
    except json.JSONDecodeError as error:
        raise ValueError(f"Некорректный JSON в файле {file_path}: {error}") from error

    if data is None and file_label == "documents":
        return []

    if not isinstance(data, list):
        raise ValueError(f"Ожидался JSON-массив в файле {file_path}.")

    return data


def main() -> None:
    # Проверяем наличие обоих файлов до начала обработки.
    if not GOVERNMENT_FOUND_PATH.exists():
        raise FileNotFoundError(f"Файл не найден: {GOVERNMENT_FOUND_PATH}")
    if not DOCUMENTS_PATH.exists():
        raise FileNotFoundError(f"Файл не найден: {DOCUMENTS_PATH}")

    government_documents = load_json_array(GOVERNMENT_FOUND_PATH, "government")
    documents = load_json_array(DOCUMENTS_PATH, "documents")

    documents_before_count = len(documents)
    government_found_count = len(government_documents)

    # Собираем URL уже существующих документов, чтобы не добавить дубликаты.
    existing_urls = {
        item.get("original_url")
        for item in documents
        if isinstance(item, dict) and item.get("original_url")
    }

    added_count = 0
    for item in government_documents:
        # Добавляем только корректные объекты документов.
        if not isinstance(item, dict):
            continue

        original_url = item.get("original_url")

        # Если URL отсутствует, считаем документ недопустимым для безопасного merge.
        if not original_url:
            continue

        if original_url in existing_urls:
            continue

        documents.append(item)
        existing_urls.add(original_url)
        added_count += 1

    with DOCUMENTS_PATH.open("w", encoding="utf-8") as file:
        json.dump(documents, file, ensure_ascii=False, indent=2)
        file.write("\n")

    documents_after_count = len(documents)

    print(f"Документов в documents.json до добавления: {documents_before_count}")
    print(f"Документов найдено в government_found_test.json: {government_found_count}")
    print(f"Новых документов добавлено: {added_count}")
    print(f"Документов в documents.json после добавления: {documents_after_count}")


if __name__ == "__main__":
    main()
