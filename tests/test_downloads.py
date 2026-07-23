"""Проверки скачивания файлов документов."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import requests

from storage import database
from storage.documents import get_document, save_document
from storage.downloads import download_document_file


class FakeResponse:
    """Минимальный HTTP-ответ для тестов."""

    def __init__(
        self,
        *,
        content: bytes = b"test",
        headers: dict[str, str] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.content = content
        self.headers = headers or {}
        self.error = error

    def __enter__(self):
        return self

    def __exit__(
        self,
        exception_type,
        exception,
        traceback,
    ) -> None:
        return None

    def raise_for_status(self) -> None:
        if self.error is not None:
            raise self.error

    def iter_content(
        self,
        chunk_size: int,
    ):
        del chunk_size
        yield self.content


class DocumentDownloadTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_directory = tempfile.TemporaryDirectory()
        self.base_dir = Path(self.temp_directory.name)
        self.download_dir = (
            self.base_dir / "downloads"
        )

        self.original_database_path = (
            database.DATABASE_PATH
        )
        database.DATABASE_PATH = (
            self.base_dir / "test.db"
        )
        database.initialize_database()

    def tearDown(self) -> None:
        database.DATABASE_PATH = (
            self.original_database_path
        )
        self.temp_directory.cleanup()

    def create_document(
        self,
        *,
        file_url: str,
    ) -> int:
        return save_document(
            {
                "source_id": "mchs",
                "title": "Документ с файлом",
                "original_url": (
                    "https://example.test/document/"
                    + str(file_url)
                ),
                "file_url": file_url,
            }
        ).document_id

    def test_pdf_is_downloaded_and_saved_in_database(
        self,
    ) -> None:
        document_id = self.create_document(
            file_url="https://example.test/file.pdf"
        )

        response = FakeResponse(
            content=b"%PDF-test",
            headers={
                "Content-Type": "application/pdf"
            },
        )

        with patch(
            "storage.downloads.requests.get",
            return_value=response,
        ):
            result = download_document_file(
                document_id,
                destination_dir=self.download_dir,
            )

        document = get_document(document_id)
        saved_path = Path(result.saved_file_path)

        self.assertTrue(result.downloaded)
        self.assertEqual(
            result.status,
            "downloaded",
        )
        self.assertTrue(saved_path.exists())
        self.assertEqual(
            saved_path.read_bytes(),
            b"%PDF-test",
        )
        self.assertEqual(
            document["download_status"],
            "downloaded",
        )

    def test_missing_file_url_is_unavailable(
        self,
    ) -> None:
        document_id = self.create_document(
            file_url=""
        )

        result = download_document_file(
            document_id,
            destination_dir=self.download_dir,
        )

        document = get_document(document_id)

        self.assertEqual(
            result.status,
            "unavailable",
        )
        self.assertEqual(
            document["download_status"],
            "unavailable",
        )

    def test_request_error_is_saved_as_failed(
        self,
    ) -> None:
        document_id = self.create_document(
            file_url="https://example.test/file.doc"
        )

        response = FakeResponse(
            error=requests.HTTPError("HTTP 500")
        )

        with patch(
            "storage.downloads.requests.get",
            return_value=response,
        ):
            result = download_document_file(
                document_id,
                destination_dir=self.download_dir,
            )

        document = get_document(document_id)

        self.assertEqual(result.status, "failed")
        self.assertEqual(
            document["download_status"],
            "failed",
        )

    def test_unsupported_file_type_is_rejected(
        self,
    ) -> None:
        document_id = self.create_document(
            file_url="https://example.test/file.zip"
        )

        response = FakeResponse(
            headers={
                "Content-Type":
                    "application/octet-stream"
            },
        )

        with patch(
            "storage.downloads.requests.get",
            return_value=response,
        ):
            result = download_document_file(
                document_id,
                destination_dir=self.download_dir,
            )

        self.assertEqual(result.status, "failed")
        self.assertIn(
            "Неподдерживаемый",
            result.message,
        )

    def test_existing_file_is_not_downloaded_again(
        self,
    ) -> None:
        document_id = self.create_document(
            file_url="https://example.test/file.xlsx"
        )

        response = FakeResponse(
            content=b"xlsx",
            headers={
                "Content-Type": (
                    "application/vnd.openxmlformats-"
                    "officedocument.spreadsheetml.sheet"
                )
            },
        )

        with patch(
            "storage.downloads.requests.get",
            return_value=response,
        ) as mocked_get:
            first = download_document_file(
                document_id,
                destination_dir=self.download_dir,
            )
            second = download_document_file(
                document_id,
                destination_dir=self.download_dir,
            )

        self.assertTrue(first.downloaded)
        self.assertFalse(second.downloaded)
        self.assertEqual(mocked_get.call_count, 1)


if __name__ == "__main__":
    unittest.main()
