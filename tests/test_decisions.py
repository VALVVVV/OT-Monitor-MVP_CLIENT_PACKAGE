"""Проверки хранения решений инженера в SQLite."""

import tempfile
import unittest
from pathlib import Path

from storage import database
from storage.decisions import (
    get_decision_history,
    list_recent_decisions,
    save_decision,
)
from storage.documents import get_document, save_document


class DecisionStorageTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_directory = tempfile.TemporaryDirectory()
        self.original_database_path = database.DATABASE_PATH
        database.DATABASE_PATH = (
            Path(self.temp_directory.name) / "test_ot_monitor.db"
        )
        database.initialize_database()

        self.document_id = save_document(
            {
                "source_id": "mchs",
                "title": "Тестовый документ",
                "original_url": "https://example.test/document/1",
            }
        ).document_id

    def tearDown(self) -> None:
        database.DATABASE_PATH = self.original_database_path
        self.temp_directory.cleanup()

    def test_decision_updates_document(self) -> None:
        result = save_decision(
            self.document_id,
            status="Принято в работу",
            comment="Проверить внутреннюю инструкцию",
        )

        document = get_document(self.document_id)

        self.assertEqual(result.document_id, self.document_id)
        self.assertEqual(result.status, "Принято в работу")
        self.assertEqual(
            document["engineer_comment"],
            "Проверить внутреннюю инструкцию",
        )
        self.assertEqual(
            document["status"],
            "Принято в работу",
        )

    def test_each_change_is_saved_in_history(self) -> None:
        save_decision(
            self.document_id,
            status="Проверка актуальности / На проверке",
            comment="Начата проверка",
        )

        save_decision(
            self.document_id,
            status="Закрыто",
            comment="Изменения внесены",
        )

        history = get_decision_history(self.document_id)

        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["status"], "Закрыто")
        self.assertEqual(
            history[1]["status"],
            "Проверка актуальности / На проверке",
        )

    def test_recent_decisions_include_document_title(self) -> None:
        save_decision(
            self.document_id,
            status="Неактуально / не относится",
        )

        decisions = list_recent_decisions()

        self.assertEqual(len(decisions), 1)
        self.assertEqual(
            decisions[0]["document_title"],
            "Тестовый документ",
        )

    def test_unknown_document_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            save_decision(
                999,
                status="Закрыто",
            )

    def test_unknown_status_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            save_decision(
                self.document_id,
                status="Неизвестный статус",
            )

    def test_empty_responsible_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            save_decision(
                self.document_id,
                status="Новое",
                responsible="",
            )

    def test_invalid_limit_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            list_recent_decisions(0)


if __name__ == "__main__":
    unittest.main()
