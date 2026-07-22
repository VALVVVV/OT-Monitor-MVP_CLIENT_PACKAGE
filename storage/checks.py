"""Операции с журналом проверок источников в SQLite."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from storage import database


ALLOWED_RESULTS = {"running", "success", "partial", "error"}
ALLOWED_TRIGGER_MODES = {"manual", "scheduled", "import"}


@dataclass(frozen=True)
class CheckResult:
    """Итоговая запись проверки источника."""

    check_id: int
    source_id: str
    result: str
    found_count: int
    added_count: int
    skipped_duplicates: int
    error_message: str


def start_check(
    source_id: str,
    trigger_mode: str = "manual",
) -> int:
    """Создаёт запись о начале проверки и возвращает её ID."""
    source_id = source_id.strip()

    if not source_id:
        raise ValueError("Не указан source_id проверки")

    if trigger_mode not in ALLOWED_TRIGGER_MODES:
        raise ValueError(
            f"Недопустимый режим запуска проверки: {trigger_mode}"
        )

    started_at = datetime.now().isoformat(timespec="seconds")

    with database.get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO checks (
                source_id,
                trigger_mode,
                started_at,
                result
            )
            VALUES (?, ?, ?, 'running')
            """,
            (source_id, trigger_mode, started_at),
        )

        return int(cursor.lastrowid)


def finish_check(
    check_id: int,
    *,
    result: str,
    found_count: int = 0,
    added_count: int = 0,
    skipped_duplicates: int = 0,
    error_message: str = "",
) -> CheckResult:
    """Завершает ранее начатую проверку."""
    if result not in ALLOWED_RESULTS - {"running"}:
        raise ValueError(
            f"Недопустимый итог проверки: {result}"
        )

    counts = {
        "found_count": found_count,
        "added_count": added_count,
        "skipped_duplicates": skipped_duplicates,
    }

    for field_name, value in counts.items():
        if value < 0:
            raise ValueError(
                f"{field_name} не может быть отрицательным"
            )

    finished_at = datetime.now().isoformat(timespec="seconds")

    with database.get_connection() as connection:
        existing = connection.execute(
            """
            SELECT id
            FROM checks
            WHERE id = ?
            """,
            (check_id,),
        ).fetchone()

        if existing is None:
            raise ValueError(
                f"Проверка с ID {check_id} не найдена"
            )

        connection.execute(
            """
            UPDATE checks
            SET finished_at = ?,
                result = ?,
                found_count = ?,
                added_count = ?,
                skipped_duplicates = ?,
                error_message = ?
            WHERE id = ?
            """,
            (
                finished_at,
                result,
                found_count,
                added_count,
                skipped_duplicates,
                error_message,
                check_id,
            ),
        )

        row = connection.execute(
            """
            SELECT
                id,
                source_id,
                result,
                found_count,
                added_count,
                skipped_duplicates,
                error_message
            FROM checks
            WHERE id = ?
            """,
            (check_id,),
        ).fetchone()

    return CheckResult(
        check_id=int(row["id"]),
        source_id=str(row["source_id"]),
        result=str(row["result"]),
        found_count=int(row["found_count"]),
        added_count=int(row["added_count"]),
        skipped_duplicates=int(row["skipped_duplicates"]),
        error_message=str(row["error_message"]),
    )


def get_check(check_id: int) -> dict[str, object] | None:
    """Возвращает одну проверку по идентификатору."""
    with database.get_connection() as connection:
        row = connection.execute(
            """
            SELECT *
            FROM checks
            WHERE id = ?
            """,
            (check_id,),
        ).fetchone()

    return dict(row) if row is not None else None


def list_checks(
    source_id: str | None = None,
) -> list[dict[str, object]]:
    """Возвращает журнал проверок от новых к старым."""
    with database.get_connection() as connection:
        if source_id:
            rows = connection.execute(
                """
                SELECT *
                FROM checks
                WHERE source_id = ?
                ORDER BY started_at DESC, id DESC
                """,
                (source_id,),
            ).fetchall()
        else:
            rows = connection.execute(
                """
                SELECT *
                FROM checks
                ORDER BY started_at DESC, id DESC
                """
            ).fetchall()

    return [dict(row) for row in rows]
