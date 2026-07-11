#!/usr/bin/env python3
"""Тестовый скрипт для анализа сохранённой страницы government.ru/docs/.

Скрипт читает локальный файл `government_docs.html`, парсит его через
BeautifulSoup, находит ссылки вида `/docs/число/` или
`http://government.ru/docs/число/` и выводит первые 10 уникальных
документов с ближайшей найденной датой рядом с ссылкой.

Если файл не найден — выводится понятное сообщение.
"""

import re
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup
import json
from datetime import date


BASE_URL = "http://government.ru"
LOCAL_FILENAME = "government_docs.html"


def find_nearest_date(tag):
    """Ищет ближайшую к тегу дату в нескольких форматах.

    Алгоритм: проверяем текст самого тега, затем родителя и соседние
    элементы (previous/next siblings) в поисках совпадения по шаблону.
    Возвращаем строку с датой или None.
    """
    # Шаблоны дат: 01.02.2020, 2020-02-01, '1 января 2020' (русские месяцы)
    date_patterns = [
        r"\b\d{1,2}\.\d{1,2}\.\d{4}\b",
        r"\b\d{4}-\d{1,2}-\d{1,2}\b",
        r"\b\d{1,2}\s+(?:января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\s+\d{4}\b",
    ]
    pattern = re.compile("(|)".join(date_patterns))  # объединённый паттерн

    # Проверяем текст текущего тега
    texts_to_check = [tag.get_text(" ", strip=True)]

    # Добавляем тексты родителей (1 уровень) и соседей
    if tag.parent is not None:
        texts_to_check.append(tag.parent.get_text(" ", strip=True))

    for sibling in list(tag.previous_siblings)[:3]:
        if hasattr(sibling, "get_text"):
            texts_to_check.append(sibling.get_text(" ", strip=True))
        else:
            texts_to_check.append(str(sibling))

    for sibling in list(tag.next_siblings)[:3]:
        if hasattr(sibling, "get_text"):
            texts_to_check.append(sibling.get_text(" ", strip=True))
        else:
            texts_to_check.append(str(sibling))

    # Ищем совпадение
    for txt in texts_to_check:
        if not txt:
            continue
        m = pattern.search(txt)
        if m:
            return m.group(0)
    return None


def main():
    # Определяем путь к локальному файлу рядом со скриптом
    local_path = Path(__file__).resolve().parent / LOCAL_FILENAME

    if not local_path.exists():
        print(f"Файл {LOCAL_FILENAME} не найден по пути: {local_path}")
        print("Поместите сохранённую страницу government_docs.html в ту же папку, что и скрипт.")
        return

    # Читаем содержимое файла
    try:
        html = local_path.read_text(encoding="utf-8")
    except Exception as e:
        print("Ошибка при чтении файла:", e)
        return

    soup = BeautifulSoup(html, "html.parser")

    # Шаблон для ссылок: /docs/число/ или http(s)://government.ru/docs/число/
    link_re = re.compile(r"^(?:https?://(?:www\.)?government\.ru)?(/docs/(\d+)/)$")

    found = []
    seen = set()

    # Проходим по всем ссылкам на странице
    for a in soup.find_all("a", href=True):
        href_raw = a["href"].strip()
        # Приводим к виду с возможным абсолютным путем
        # Если есть полный URL, оставим как есть; если относительный, оставим относительным
        m = link_re.match(href_raw)
        if not m:
            # Также может быть абсолютная ссылка без www и с протоколом
            # Попробуем извлечь путь, если ссылка содержит government.ru в середине
            if "government.ru/docs/" in href_raw:
                # Найдём часть начиная с /docs/
                idx = href_raw.find("/docs/")
                href_path = href_raw[idx:]
                m2 = re.match(r"^(/docs/(\d+)/)$", href_path)
                if m2:
                    href_path_only = m2.group(1)
                    doc_num = m2.group(2)
                    full_url = urljoin(BASE_URL, href_path_only)
                else:
                    continue
            else:
                continue
        else:
            href_path_only = m.group(1)
            doc_num = m.group(2)
            full_url = urljoin(BASE_URL, href_path_only)

        # Уникальность по полному URL
        if full_url in seen:
            continue
        seen.add(full_url)

        link_text = a.get_text(strip=True) or "(текст ссылки отсутствует)"
        date_near = find_nearest_date(a) or "(дата не найдена)"

        found.append((doc_num, full_url, link_text, date_near))
        if len(found) >= 10:
            break

    if not found:
        print("Не найдено ссылок на документы вида /docs/число/ в локальном файле.")
        return

    # Формируем объекты для сохранения в JSON по требуемой структуре
    results = []
    today = date.today().isoformat()  # формат YYYY-MM-DD
    for doc_num, full_url, link_text, date_near in found:
        obj = {
            "id": f"gov_{doc_num}",
            "source": "Правительство РФ",
            "title": link_text,
            "original_url": full_url,
            "doc_number": doc_num,
            "found_date": today,
            "section": "Общее",
            "topic": "Документы Правительства РФ",
            "summary": "Документ найден на сайте Правительства РФ. Требуется проверка инженером.",
            "status": "Новое",
        }
        results.append(obj)

    # Убедимся, что директория data существует, затем сохраним файл
    data_dir = Path(__file__).resolve().parent / "data"
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

    out_path = data_dir / "government_found_test.json"
    try:
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("Ошибка при сохранении JSON:", e)
        return

    # Выводим краткую сводку
    print(f"Найдено документов: {len(found)}")
    print(f"Сохранено документов: {len(results)}")
    print(f"Файл сохранён: {out_path}")


if __name__ == "__main__":
    main()

# Если библиотеки не установлены, выполните:
# pip install beautifulsoup4
