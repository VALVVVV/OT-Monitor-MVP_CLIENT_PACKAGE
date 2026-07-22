"""SQLite API-маршруты локального сервера ОТ-Монитор."""

from __future__ import annotations

import json
import re
from http import HTTPStatus

from storage.checks import list_checks
from storage.decisions import list_recent_decisions, save_decision
from storage.documents import get_document, list_documents


DECISION_PATH_PATTERN = re.compile(
    r"^/api/documents/(\d+)/decision$"
)


class SQLiteApiMixin:
    """Добавляет HTTP-обработчику API для данных SQLite."""

    def handle_sqlite_get(self, request_path: str) -> bool:
        """Обрабатывает GET-маршруты SQLite."""
        if request_path == "/api/documents":
            documents = list_documents()
            self.send_json(
                HTTPStatus.OK,
                {
                    "ok": True,
                    "count": len(documents),
                    "documents": documents,
                },
            )
            return True

        if request_path == "/api/checks":
            checks = list_checks()
            self.send_json(
                HTTPStatus.OK,
                {
                    "ok": True,
                    "count": len(checks),
                    "checks": checks,
                },
            )
            return True

        if request_path == "/api/decisions":
            decisions = list_recent_decisions()
            self.send_json(
                HTTPStatus.OK,
                {
                    "ok": True,
                    "count": len(decisions),
                    "decisions": decisions,
                },
            )
            return True

        return False

    def handle_sqlite_post(self, request_path: str) -> bool:
        """Обрабатывает POST-маршруты SQLite."""
        match = DECISION_PATH_PATTERN.fullmatch(request_path)
        if match is None:
            return False

        document_id = int(match.group(1))

        try:
            payload = self.read_json_body()
            result = save_decision(
                document_id,
                status=str(payload.get("status") or ""),
                comment=str(payload.get("comment") or ""),
                responsible=str(
                    payload.get("responsible")
                    or "Инженер по ОТ"
                ),
            )
        except (
            json.JSONDecodeError,
            UnicodeDecodeError,
            ValueError,
        ) as error:
            self.send_json(
                HTTPStatus.BAD_REQUEST,
                {
                    "ok": False,
                    "message": str(error)
                    or "Некорректный запрос",
                },
            )
            return True

        document = get_document(document_id)

        self.send_json(
            HTTPStatus.OK,
            {
                "ok": True,
                "message": "Решение сохранено",
                "decision": {
                    "id": result.decision_id,
                    "document_id": result.document_id,
                    "status": result.status,
                    "comment": result.comment,
                    "responsible": result.responsible,
                    "decided_at": result.decided_at,
                },
                "document": document,
            },
        )
        return True

    def read_json_body(self) -> dict[str, object]:
        """Читает JSON-объект из тела запроса."""
        content_length = self.headers.get("Content-Length")

        if not content_length:
            raise ValueError("Пустой запрос")

        raw_body = self.rfile.read(int(content_length))
        payload = json.loads(raw_body.decode("utf-8"))

        if not isinstance(payload, dict):
            raise ValueError(
                "JSON-запрос должен содержать объект"
            )

        return payload
