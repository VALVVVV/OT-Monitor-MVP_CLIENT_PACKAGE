"""Проверки импорта результатов парсеров в SQLite."""

import tempfile
import unittest
from pathlib import Path

from storage import database
from storage.checks import get_check
from storage.documents import list_documents
from storage.importers import import_source_payload


class ParserImportTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_directory = tempfile.TemporaryDirectory()
        self.original_database_path = database.DATABASE_PATH
        database.DATABASE_PATH = (
            Path(self.temp_directory.name) / "test_ot_monitor.db"
        )
        database.initialize_database()

    def tearDown(self) -> None:
        database.DATABASE_PATH = self.original_database_path
        self.temp_directory.cleanup()

    def test_mchs_document_is_imported(self) -> None:
        result = import_source_payload(
            "mchs",
            [
                {
                    "title": "Документ МЧС",
                    "url": "https://example.test/mchs/1",
                    "file_url": "https://example.test/mchs/1.pdf",
                }
            ],
        )

        documents = list_documents()

        self.assertEqual(result.result, "success")
        self.assertEqual(result.added_count, 1)
        self.assertEqual(documents[0]["source_id"], "mchs")
        self.assertEqual(
            documents[0]["file_url"],
            "https://example.test/mchs/1.pdf",
        )

    def test_minzdrav_publication_date_is_preserved(self) -> None:
        import_source_payload(
            "minzdrav",
            [
                {
                    "title": "Документ Минздрава",
                    "url": "https://example.test/minzdrav/1",
                    "document_date": "2026-05-15",
                }
            ],
        )

        document = list_documents()[0]

        self.assertEqual(
            document["publication_date"],
            "2026-05-15",
        )

    def test_duplicate_is_not_added_twice(self) -> None:
        payload = [
            {
                "title": "Документ Минтруда",
                "url": "https://example.test/mintrud/1",
            }
        ]

        first = import_source_payload("mintrud", payload)
        second = import_source_payload("mintrud", payload)

        self.assertEqual(first.added_count, 1)
        self.assertEqual(second.added_count, 0)
        self.assertEqual(second.skipped_duplicates, 1)
        self.assertEqual(len(list_documents()), 1)

    def test_same_document_with_different_urls_is_deduplicated(self) -> None:
        title = (
            "Приказ Минтруда России № 236 от 1 июня 2026 г. "
            "О внесении изменений"
        )

        first = import_source_payload(
            "mintrud",
            [
                {
                    "title": title,
                    "url": "https://mintrud.gov.ru/docs/mintrud/orders/3216",
                    "possible_date": "1 июня 2026",
                }
            ],
        )

        second = import_source_payload(
            "mintrud",
            [
                {
                    "title": title,
                    "url": "https://mintrud.gov.ru/docs/mintrud/orders/3217",
                    "possible_date": "1 июня 2026",
                }
            ],
        )

        documents = list_documents()

        self.assertEqual(first.added_count, 1)
        self.assertEqual(second.added_count, 0)
        self.assertEqual(second.skipped_duplicates, 1)
        self.assertEqual(len(documents), 1)

    def test_parser_error_is_written_to_check_log(self) -> None:
        result = import_source_payload(
            "mintrud",
            {
                "status": "error",
                "error": "ReadTimeout",
            },
        )

        check = get_check(result.check_id)

        self.assertEqual(result.result, "error")
        self.assertEqual(check["result"], "error")
        self.assertEqual(check["error_message"], "ReadTimeout")

    def test_invalid_document_produces_partial_result(self) -> None:
        result = import_source_payload(
            "mchs",
            [
                {
                    "title": "Корректный документ",
                    "url": "https://example.test/mchs/2",
                },
                {
                    "title": "",
                    "url": "",
                },
            ],
        )

        self.assertEqual(result.result, "partial")
        self.assertEqual(result.added_count, 1)
        self.assertEqual(result.invalid_count, 1)


if __name__ == "__main__":
    unittest.main()
