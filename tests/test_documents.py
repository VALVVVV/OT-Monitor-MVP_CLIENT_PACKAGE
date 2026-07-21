"""Проверки сохранения документов в SQLite."""

import tempfile
import unittest
from pathlib import Path

from storage import database
from storage.documents import get_document, list_documents, save_document


class DocumentStorageTestCase(unittest.TestCase):
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

    def test_document_is_saved_and_loaded(self) -> None:
        result = save_document(
            {
                "source_id": "mchs",
                "title": "Тестовый документ МЧС",
                "original_url": "https://example.test/mchs/1",
                "publication_date": "2026-07-20",
                "file_url": "https://example.test/file.pdf",
                "section": "Пожарная безопасность",
            }
        )

        self.assertTrue(result.created)

        document = get_document(result.document_id)

        self.assertIsNotNone(document)
        self.assertEqual(document["source_id"], "mchs")
        self.assertEqual(document["title"], "Тестовый документ МЧС")
        self.assertEqual(document["publication_date"], "2026-07-20")
        self.assertEqual(document["status"], "Новое")

    def test_duplicate_updates_metadata_without_new_row(self) -> None:
        first_result = save_document(
            {
                "source_id": "minzdrav",
                "title": "Первоначальное название",
                "original_url": "https://example.test/minzdrav/1",
                "status": "Принято в работу",
                "engineer_comment": "Нужно проверить",
            }
        )

        second_result = save_document(
            {
                "source_id": "minzdrav",
                "title": "Обновлённое название",
                "original_url": "https://example.test/minzdrav/1",
                "status": "Новое",
                "engineer_comment": "",
            }
        )

        documents = list_documents()
        stored = get_document(first_result.document_id)

        self.assertTrue(first_result.created)
        self.assertFalse(second_result.created)
        self.assertEqual(first_result.document_id, second_result.document_id)
        self.assertEqual(len(documents), 1)
        self.assertEqual(stored["title"], "Обновлённое название")
        self.assertEqual(stored["status"], "Принято в работу")
        self.assertEqual(stored["engineer_comment"], "Нужно проверить")

    def test_required_fields_are_validated(self) -> None:
        with self.assertRaises(ValueError):
            save_document(
                {
                    "source_id": "mchs",
                    "title": "",
                    "original_url": "https://example.test/mchs/2",
                }
            )


if __name__ == "__main__":
    unittest.main()
