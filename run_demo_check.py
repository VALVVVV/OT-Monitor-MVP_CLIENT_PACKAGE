#!/usr/bin/env python3
"""Ручной запуск проверки трёх источников для демо-контура ОТ-Монитор.

Скрипт:
1. Создаёт backup data/documents.json и data/check_log.json.
2. Последовательно запускает inspect_* и merge_* для трёх источников.
3. Показывает понятный отчёт по каждому источнику.
4. Не останавливает весь прогон, если один источник завершился ошибкой.

Скрипт пока предназначен только для ручного запуска из терминала.
Подключение к интерфейсу MVP и автозапуск по расписанию не реализуются здесь.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class SourceChain:
    """Описание цепочки проверки одного источника."""

    source_name: str
    inspect_script: str
    merge_script: str


@dataclass
class SourceRunResult:
    """Итог выполнения цепочки одного источника."""

    source_name: str
    inspect_script: str
    merge_script: str
    inspect_success: bool
    merge_success: bool
    documents_before: int | None
    documents_after: int | None
    added_documents: int | None
    check_log_before: int | None
    check_log_after: int | None
    added_check_log_entries: int | None
    error_message: str

    @property
    def success(self) -> bool:
        return self.inspect_success and self.merge_success


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DOCUMENTS_PATH = DATA_DIR / "documents.json"
CHECK_LOG_PATH = DATA_DIR / "check_log.json"
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

SOURCE_CHAINS = [
    SourceChain(
        source_name="Минтруд России",
        inspect_script="inspect_mintrud_docs.py",
        merge_script="merge_mintrud_to_documents.py",
    ),
    SourceChain(
        source_name="МЧС России",
        inspect_script="inspect_mchs_docs.py",
        merge_script="merge_mchs_to_documents.py",
    ),
    SourceChain(
        source_name="Минздрав России",
        inspect_script="inspect_minzdrav_docs.py",
        merge_script="merge_minzdrav_to_documents.py",
    ),
]


def load_json_list_count(file_path: Path) -> int:
    """Возвращает длину JSON-списка в файле."""
    with file_path.open("r", encoding="utf-8-sig") as file:
        payload = json.load(file)

    if not isinstance(payload, list):
        raise ValueError(f"Файл {file_path} должен содержать JSON-список.")

    return len(payload)


def ensure_required_files_exist() -> None:
    """Проверяет наличие обязательных файлов до старта."""
    required_files = [DOCUMENTS_PATH, CHECK_LOG_PATH]

    for file_path in required_files:
        if not file_path.exists():
            raise FileNotFoundError(f"Не найден обязательный файл: {file_path}")


def create_backup(file_path: Path, timestamp: str) -> Path:
    """Создаёт backup-файл рядом с оригиналом."""
    backup_name = f"{file_path.stem}_backup_before_run_demo_check_{timestamp}{file_path.suffix}"
    backup_path = file_path.parent / backup_name
    shutil.copy2(file_path, backup_path)
    return backup_path


def run_python_script(script_name: str) -> tuple[bool, str]:
    """Запускает Python-скрипт и возвращает флаг успеха и текст вывода."""
    script_path = BASE_DIR / script_name

    if not script_path.exists():
        return False, f"Скрипт не найден: {script_path}"

    completed = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=str(BASE_DIR),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )

    output_parts = []
    if completed.stdout.strip():
        output_parts.append("STDOUT:\n" + completed.stdout.strip())
    if completed.stderr.strip():
        output_parts.append("STDERR:\n" + completed.stderr.strip())

    output_text = "\n\n".join(output_parts).strip()
    if not output_text:
        output_text = "Скрипт не вывел сообщений."

    return completed.returncode == 0, output_text


def print_section_separator() -> None:
    """Печатает разделитель для терминального отчёта."""
    print("=" * 72)


def print_script_result(script_name: str, success: bool, output_text: str) -> None:
    """Печатает результат выполнения дочернего скрипта."""
    status_text = "успешно" if success else "ошибка"
    print(f"Скрипт: {script_name}")
    print(f"Статус: {status_text}")
    print(output_text)


def format_count(value: int | None) -> str:
    """Форматирует числовые значения для отчёта."""
    return str(value) if value is not None else "не удалось определить"


def run_source_chain(source_chain: SourceChain) -> SourceRunResult:
    """Запускает inspect и merge для одного источника."""
    print_section_separator()
    print(f"Источник: {source_chain.source_name}")

    documents_before: int | None = None
    check_log_before: int | None = None
    documents_after: int | None = None
    check_log_after: int | None = None
    added_documents: int | None = None
    added_check_log_entries: int | None = None
    error_messages: list[str] = []

    try:
        documents_before = load_json_list_count(DOCUMENTS_PATH)
        check_log_before = load_json_list_count(CHECK_LOG_PATH)
    except Exception as error:
        error_messages.append(f"Не удалось прочитать входные JSON-файлы: {error}")

    if error_messages:
        print("Статус: ошибка до запуска цепочки")
        print(error_messages[-1])
        return SourceRunResult(
            source_name=source_chain.source_name,
            inspect_script=source_chain.inspect_script,
            merge_script=source_chain.merge_script,
            inspect_success=False,
            merge_success=False,
            documents_before=documents_before,
            documents_after=documents_after,
            added_documents=added_documents,
            check_log_before=check_log_before,
            check_log_after=check_log_after,
            added_check_log_entries=added_check_log_entries,
            error_message="; ".join(error_messages),
        )

    inspect_success, inspect_output = run_python_script(source_chain.inspect_script)
    print_script_result(source_chain.inspect_script, inspect_success, inspect_output)

    merge_success = False
    if inspect_success:
        merge_success, merge_output = run_python_script(source_chain.merge_script)
        print_script_result(source_chain.merge_script, merge_success, merge_output)
    else:
        merge_output = "Merge пропущен, потому что inspect завершился ошибкой."
        print_script_result(source_chain.merge_script, False, merge_output)
        error_messages.append("Inspect завершился ошибкой, merge не запускался.")

    try:
        documents_after = load_json_list_count(DOCUMENTS_PATH)
        check_log_after = load_json_list_count(CHECK_LOG_PATH)
        added_documents = documents_after - documents_before
        added_check_log_entries = check_log_after - check_log_before
    except Exception as error:
        error_messages.append(f"Не удалось прочитать итоговые JSON-файлы: {error}")

    if not inspect_success:
        error_messages.append(f"Ошибка в {source_chain.inspect_script}.")
    if inspect_success and not merge_success:
        error_messages.append(f"Ошибка в {source_chain.merge_script}.")

    print("Сводка по источнику:")
    print(f"- documents.json до запуска: {format_count(documents_before)}")
    print(f"- documents.json после запуска: {format_count(documents_after)}")
    print(f"- новых документов добавлено: {format_count(added_documents)}")
    print(f"- check_log.json до запуска: {format_count(check_log_before)}")
    print(f"- check_log.json после запуска: {format_count(check_log_after)}")
    print(f"- новых записей в check_log.json: {format_count(added_check_log_entries)}")
    print(f"- итог по источнику: {'успешно' if inspect_success and merge_success else 'ошибка'}")

    return SourceRunResult(
        source_name=source_chain.source_name,
        inspect_script=source_chain.inspect_script,
        merge_script=source_chain.merge_script,
        inspect_success=inspect_success,
        merge_success=merge_success,
        documents_before=documents_before,
        documents_after=documents_after,
        added_documents=added_documents,
        check_log_before=check_log_before,
        check_log_after=check_log_after,
        added_check_log_entries=added_check_log_entries,
        error_message="; ".join(error_messages),
    )


def print_final_summary(
    started_at: str,
    documents_backup_path: Path,
    check_log_backup_path: Path,
    results: list[SourceRunResult],
) -> None:
    """Печатает общий итог выполнения."""
    print_section_separator()
    print("Общий итог запуска")
    print(f"Время запуска: {started_at}")
    print(f"Backup documents.json: {documents_backup_path}")
    print(f"Backup check_log.json: {check_log_backup_path}")

    success_count = sum(1 for result in results if result.success)
    error_count = len(results) - success_count
    total_added_documents = sum(
        result.added_documents for result in results if result.added_documents is not None
    )
    total_added_log_entries = sum(
        result.added_check_log_entries
        for result in results
        if result.added_check_log_entries is not None
    )

    print(f"Успешно завершено источников: {success_count}")
    print(f"С ошибкой завершено источников: {error_count}")
    print(f"Всего новых документов добавлено: {total_added_documents}")
    print(f"Всего новых записей в check_log.json: {total_added_log_entries}")
    print()
    print("Итоги по источникам:")

    for result in results:
        status_text = "успешно" if result.success else "ошибка"
        print(f"- {result.source_name}: {status_text}")
        print(
            "  "
            f"documents {format_count(result.documents_before)} -> "
            f"{format_count(result.documents_after)}, "
            f"добавлено {format_count(result.added_documents)}; "
            f"check_log {format_count(result.check_log_before)} -> "
            f"{format_count(result.check_log_after)}"
        )
        if result.error_message:
            print(f"  Детали ошибки: {result.error_message}")


def main() -> int:
    """Точка входа."""
    started_at = datetime.now().isoformat(timespec="seconds")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    print_section_separator()
    print("Ручной запуск проверки demo-контура ОТ-Монитор")
    print(f"Старт: {started_at}")

    try:
        ensure_required_files_exist()
        documents_backup_path = create_backup(DOCUMENTS_PATH, timestamp)
        check_log_backup_path = create_backup(CHECK_LOG_PATH, timestamp)
    except Exception as error:
        print("Не удалось создать backup перед запуском merge-скриптов.")
        print(str(error))
        return 1

    print(f"Backup создан: {documents_backup_path}")
    print(f"Backup создан: {check_log_backup_path}")

    results: list[SourceRunResult] = []
    for source_chain in SOURCE_CHAINS:
        results.append(run_source_chain(source_chain))

    print_final_summary(
        started_at=started_at,
        documents_backup_path=documents_backup_path,
        check_log_backup_path=check_log_backup_path,
        results=results,
    )

    return 0 if all(result.success for result in results) else 1


if __name__ == "__main__":
    sys.exit(main())
