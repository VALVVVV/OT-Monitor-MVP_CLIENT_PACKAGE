"""Операции со статусами и комментариями инженера в SQLite."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from storage import database


ALLOWED_STATUSES = {
    "Новое",
    "Проверка актуальности",
    "Принято в работу",
    "Неактуально / не относится",
    "Закрыто",
}


@dataclass(frozen=True)
class DecisionResult:
    """Результат сохранения решения инженера."""

    decision_id: int
    document_id: int
    status: str
    comment: str
    responsible: str
    decided_at: str


def save_decision(
    document_id: int,
    *,
    status: str,
    comment: str = "",
    responsible: str = "Инженер по ОТ",
) -> DecisionResult:
    """Обновляет документ и сохраняет запись в истории решений."""
    status = status.strip()
    comment = comment.strip()
    responsible = responsible.strip()

    if status not in ALLOWED_STATUSES:
        raise ValueError(f"Недопустимый статус документа: {status}")

    if not responsible:
        raise ValueError("Не указан ответственный специалист")

    decided_at = datetime.now().isoformat(timespec="seconds")

    with database.get_connection() as connection:
        document = connection.execute(
            """
            SELECT id
            FROM documents
            WHERE id = ?
            """,
            (document_id,),
        ).fetchone()

        if document is None:
            raise ValueError(
                f"Документ с ID {document_id} не найден"
            )

        connection.execute(
            """
            UPDATE documents
            SET status = ?,
                engineer_comment = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                status,
                comment,
                document_id,
            ),
        )

        cursor = connection.execute(
            """
            INSERT INTO document_decisions (
                document_id,
                status,
                comment,
                responsible,
                decided_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                document_id,
                status,
                comment,
                responsible,
                decided_at,
            ),
        )

        decision_id = int(cursor.lastrowid)

    return DecisionResult(
        decision_id=decision_id,
        document_id=document_id,
        status=status,
        comment=comment,
        responsible=responsible,
        decided_at=decided_at,
    )


def get_decision_history(
    document_id: int,
) -> list[dict[str, object]]:
    """Возвращает историю решений по документу."""
    with database.get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                document_id,
                status,
                comment,
                responsible,
                decided_at
            FROM document_decisions
            WHERE document_id = ?
            ORDER BY decided_at DESC, id DESC
            """,
            (document_id,),
        ).fetchall()

    return [dict(row) for row in rows]


def list_recent_decisions(
    limit: int = 100,
) -> list[dict[str, object]]:
    """Возвращает последние решения по всем документам."""
    if limit <= 0:
        raise ValueError("Лимит должен быть больше нуля")

    with database.get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                decision.id,
                decision.document_id,
                document.title AS document_title,
                decision.status,
                decision.comment,
                decision.responsible,
                decision.decided_at
            FROM document_decisions AS decision
            JOIN documents AS document
              ON document.id = decision.document_id
            ORDER BY decision.decided_at DESC, decision.id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return [dict(row) for row in rows]
