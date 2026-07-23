#!/usr/bin/env python3
"""Ручная проверка трёх источников с сохранением в SQLite."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from storage.database import initialize_database
from storage.importers import ImportResult, import_source_file


BASE_DIR = Path(__file__).resolve().parent

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


@dataclass(frozen=True)
class SourceChain:
    """Настройки проверки одного источника."""

    source_id: str
    source_name: str
    inspect_script: str
    result_file: str


@dataclass(frozen=True)
class SourceRunResult:
    """Итог проверки одного источника."""

    source_id: str
    source_name: str
    inspect_success: bool
    import_result: ImportResult
    inspect_output: str

    @property
    def success(self) -> bool:
        return (
            self.inspect_success
            and self.import_result.result == "success"
        )


SOURCE_CHAINS = [
    SourceChain(
        source_id="mintrud",
        source_name="Минтруд России",
        inspect_script="inspect_mintrud_docs.py",
        result_file="data/mintrud_documents_filtered.json",
    ),
    SourceChain(
        source_id="mchs",
        source_name="МЧС России",
        inspect_script="inspect_mchs_docs.py",
        result_file="data/mchs_documents_filtered.json",
    ),
    SourceChain(
        source_id="minzdrav",
        source_name="Минздрав России",
        inspect_script="inspect_minzdrav_docs.py",
        result_file="data/minzdrav_documents_filtered.json",
    ),
]


def run_python_script(
    script_name: str,
    *,
    base_dir: Path = BASE_DIR,
) -> tuple[bool, str]:
    """Запускает парсер и возвращает статус и его вывод."""
    script_path = base_dir / script_name

    if not script_path.exists():
        return False, f"Скрипт не найден: {script_path}"

    completed = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=str(base_dir),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )

    output_parts: list[str] = []

    if completed.stdout.strip():
        output_parts.append(
            "STDOUT:\n" + completed.stdout.strip()
        )

    if completed.stderr.strip():
        output_parts.append(
            "STDERR:\n" + completed.stderr.strip()
        )

    output = "\n\n".join(output_parts)

    if not output:
        output = "Скрипт не вывел сообщений."

    return completed.returncode == 0, output


def run_source_chain(
    source_chain: SourceChain,
    *,
    base_dir: Path = BASE_DIR,
) -> SourceRunResult:
    """Запускает парсер и импортирует его результат в SQLite."""
    print("=" * 72)
    print(f"Источник: {source_chain.source_name}")

    result_path = base_dir / source_chain.result_file

    # Не позволяем случайно импортировать устаревший результат
    # предыдущей проверки, если текущий парсер аварийно завершится.
    if result_path.exists():
        result_path.unlink()

    inspect_success, inspect_output = run_python_script(
        source_chain.inspect_script,
        base_dir=base_dir,
    )

    print(
        "Парсер: "
        f"{'успешно' if inspect_success else 'ошибка'}"
    )
    print(inspect_output)

    import_result = import_source_file(
        source_chain.source_id,
        result_path,
        trigger_mode="manual",
    )

    print("Импорт в SQLite:")
    print(f"- результат: {import_result.result}")
    print(f"- найдено: {import_result.found_count}")
    print(f"- добавлено: {import_result.added_count}")
    print(
        "- пропущено как дубли: "
        f"{import_result.skipped_duplicates}"
    )
    print(
        "- некорректных записей: "
        f"{import_result.invalid_count}"
    )

    if import_result.error_message:
        print(f"- ошибка: {import_result.error_message}")

    return SourceRunResult(
        source_id=source_chain.source_id,
        source_name=source_chain.source_name,
        inspect_success=inspect_success,
        import_result=import_result,
        inspect_output=inspect_output,
    )


def print_final_summary(
    started_at: str,
    results: list[SourceRunResult],
) -> None:
    """Печатает общий результат проверки."""
    print("=" * 72)
    print("Общий итог проверки")
    print(f"Время запуска: {started_at}")

    total_added = sum(
        result.import_result.added_count
        for result in results
    )

    success_count = sum(
        1 for result in results if result.success
    )

    print(
        f"Успешно проверено источников: "
        f"{success_count}/{len(results)}"
    )
    print(f"Всего новых документов: {total_added}")
    print()
    print("Итоги по источникам:")

    for result in results:
        status = (
            "успешно"
            if result.success
            else result.import_result.result
        )

        print(
            f"- {result.source_name}: {status}; "
            f"добавлено "
            f"{result.import_result.added_count}"
        )

        if result.import_result.error_message:
            print(
                "  Ошибка: "
                f"{result.import_result.error_message}"
            )


def main() -> int:
    """Запускает ручную проверку всех источников."""
    initialize_database()

    started_at = datetime.now().isoformat(
        timespec="seconds"
    )

    print("=" * 72)
    print("Ручная проверка источников ОТ-Монитор")
    print(f"Старт: {started_at}")

    results = [
        run_source_chain(source_chain)
        for source_chain in SOURCE_CHAINS
    ]

    print_final_summary(started_at, results)

    return 0 if all(
        result.success for result in results
    ) else 1


if __name__ == "__main__":
    sys.exit(main())
