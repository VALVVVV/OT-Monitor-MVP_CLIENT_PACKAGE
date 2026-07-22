"""Интеграционные проверки SQLite API сервера."""

import json
import tempfile
import threading
import unittest
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from server import OTMonitorRequestHandler
from storage import database
from storage.documents import get_document, save_document


class SQLiteApiTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_directory = tempfile.TemporaryDirectory()
        self.original_database_path = database.DATABASE_PATH

        database.DATABASE_PATH = (
            Path(self.temp_directory.name)
            / "test_ot_monitor.db"
        )
        database.initialize_database()

        self.document_id = save_document(
            {
                "source_id": "mchs",
                "title": "API-тестовый документ",
                "original_url":
                    "https://example.test/api-document",
            }
        ).document_id

        handler = partial(
            OTMonitorRequestHandler,
            directory=self.temp_directory.name,
        )

        self.server = ThreadingHTTPServer(
            ("127.0.0.1", 0),
            handler,
        )

        self.server_thread = threading.Thread(
            target=self.server.serve_forever,
            daemon=True,
        )
        self.server_thread.start()

        host, port = self.server.server_address
        self.base_url = f"http://{host}:{port}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.server_thread.join(timeout=2)

        database.DATABASE_PATH = (
            self.original_database_path
        )
        self.temp_directory.cleanup()

    def get_json(
        self,
        path: str,
    ) -> tuple[int, dict[str, object]]:
        with urlopen(
            f"{self.base_url}{path}"
        ) as response:
            return response.status, json.load(response)

    def post_json(
        self,
        path: str,
        payload: dict[str, object],
    ) -> tuple[int, dict[str, object]]:
        request = Request(
            f"{self.base_url}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json"
            },
            method="POST",
        )

        with urlopen(request) as response:
            return response.status, json.load(response)

    def test_documents_endpoint_returns_rows(self) -> None:
        status, payload = self.get_json(
            "/api/documents"
        )

        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["count"], 1)
        self.assertEqual(
            payload["documents"][0]["title"],
            "API-тестовый документ",
        )

    def test_decision_endpoint_updates_document(
        self,
    ) -> None:
        status, payload = self.post_json(
            (
                f"/api/documents/"
                f"{self.document_id}/decision"
            ),
            {
                "status": "Принято в работу",
                "comment":
                    "Проверить локальный акт",
            },
        )

        stored = get_document(self.document_id)

        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        self.assertEqual(
            stored["status"],
            "Принято в работу",
        )
        self.assertEqual(
            stored["engineer_comment"],
            "Проверить локальный акт",
        )

        _, decisions_payload = self.get_json(
            "/api/decisions"
        )
        self.assertEqual(
            decisions_payload["count"],
            1,
        )

    def test_invalid_decision_returns_bad_request(
        self,
    ) -> None:
        request = Request(
            (
                f"{self.base_url}/api/documents/"
                f"{self.document_id}/decision"
            ),
            data=json.dumps(
                {"status": "Несуществующий"}
            ).encode("utf-8"),
            headers={
                "Content-Type": "application/json"
            },
            method="POST",
        )

        with self.assertRaises(HTTPError) as context:
            urlopen(request)

        self.assertEqual(
            context.exception.code,
            400,
        )

    def test_checks_endpoint_returns_empty_list(
        self,
    ) -> None:
        status, payload = self.get_json(
            "/api/checks"
        )

        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["count"], 0)
        self.assertEqual(payload["checks"], [])


if __name__ == "__main__":
    unittest.main()
