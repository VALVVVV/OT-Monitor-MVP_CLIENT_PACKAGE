"""Интеграционные проверки SQLite API сервера."""

import json
import tempfile
import threading
import unittest
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from unittest.mock import patch
from types import SimpleNamespace
from urllib.request import Request, urlopen

from server import OTMonitorRequestHandler
from storage import database
from storage.documents import get_document, save_document
from storage.downloads import DownloadResult
from storage.checks import finish_check, start_check


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

    def test_download_endpoint_returns_result(
        self,
    ) -> None:
        fake_result = DownloadResult(
            document_id=self.document_id,
            status="downloaded",
            saved_file_path=(
                "data/downloaded_documents/test.pdf"
            ),
            message="Файл успешно скачан",
            downloaded=True,
        )

        with patch(
            "api_routes.download_document_file",
            return_value=fake_result,
        ):
            status, payload = self.post_json(
                (
                    f"/api/documents/"
                    f"{self.document_id}/download"
                ),
                {},
            )

        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        self.assertEqual(
            payload["download"]["status"],
            "downloaded",
        )
        self.assertEqual(
            payload["download"]["saved_file_path"],
            "data/downloaded_documents/test.pdf",
        )

    def test_download_failure_returns_422(
        self,
    ) -> None:
        fake_result = DownloadResult(
            document_id=self.document_id,
            status="failed",
            saved_file_path="",
            message="HTTP 500",
            downloaded=False,
        )

        with patch(
            "api_routes.download_document_file",
            return_value=fake_result,
        ):
            request = Request(
                (
                    f"{self.base_url}/api/documents/"
                    f"{self.document_id}/download"
                ),
                data=b"{}",
                headers={
                    "Content-Type": "application/json"
                },
                method="POST",
            )

            with self.assertRaises(HTTPError) as context:
                urlopen(request)

        self.assertEqual(
            context.exception.code,
            422,
        )

    def test_download_unknown_document_returns_404(
        self,
    ) -> None:
        with patch(
            "api_routes.download_document_file",
            side_effect=ValueError(
                "Документ с ID 999 не найден"
            ),
        ):
            request = Request(
                (
                    f"{self.base_url}/api/documents/"
                    "999/download"
                ),
                data=b"{}",
                headers={
                    "Content-Type": "application/json"
                },
                method="POST",
            )

            with self.assertRaises(HTTPError) as context:
                urlopen(request)

        self.assertEqual(
            context.exception.code,
            404,
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

    def test_run_check_returns_source_results(
        self,
    ) -> None:
        def fake_run(*args, **kwargs):
            del args, kwargs

            for source_id in (
                "mintrud",
                "mchs",
                "minzdrav",
            ):
                check_id = start_check(source_id)
                finish_check(
                    check_id,
                    result="success",
                    found_count=2,
                    added_count=1,
                )

            return SimpleNamespace(
                returncode=0,
                stdout="Проверка завершена",
                stderr="",
            )

        with patch(
            "server.subprocess.run",
            side_effect=fake_run,
        ):
            status, payload = self.post_json(
                "/api/run-demo-check",
                {},
            )

        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        self.assertEqual(
            payload["overall_result"],
            "success",
        )
        self.assertEqual(
            len(payload["source_results"]),
            3,
        )
        self.assertEqual(
            payload["message"],
            "Все источники проверены успешно.",
        )

    def test_run_check_can_return_partial_result(
        self,
    ) -> None:
        def fake_run(*args, **kwargs):
            del args, kwargs

            successful_check = start_check("mchs")
            finish_check(
                successful_check,
                result="success",
                found_count=2,
                added_count=1,
            )

            failed_check = start_check("mintrud")
            finish_check(
                failed_check,
                result="error",
                error_message="ReadTimeout",
            )

            return SimpleNamespace(
                returncode=1,
                stdout="",
                stderr="ReadTimeout",
            )

        with patch(
            "server.subprocess.run",
            side_effect=fake_run,
        ):
            status, payload = self.post_json(
                "/api/run-demo-check",
                {},
            )

        self.assertEqual(status, 200)
        self.assertFalse(payload["ok"])
        self.assertEqual(
            payload["overall_result"],
            "partial",
        )
        self.assertEqual(
            payload["message"],
            "Проверка завершена частично.",
        )

        errors = [
            item
            for item in payload["source_results"]
            if item["result"] == "error"
        ]

        self.assertEqual(len(errors), 1)
        self.assertEqual(
            errors[0]["source_id"],
            "mintrud",
        )
        self.assertEqual(
            errors[0]["error_message"],
            "ReadTimeout",
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
