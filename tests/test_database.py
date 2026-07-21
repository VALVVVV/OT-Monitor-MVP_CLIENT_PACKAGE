"""Проверки начальной SQLite-схемы ОТ-Монитор."""

import tempfile
import unittest
from pathlib import Path

from storage import database


class DatabaseSchemaTestCase(unittest.TestCase):
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

    def test_required_tables_exist(self) -> None:
        with database.get_connection() as connection:
            rows = connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                  AND name NOT LIKE 'sqlite_%'
                """
            ).fetchall()

        table_names = {row["name"] for row in rows}

        self.assertEqual(
            table_names,
            {
                "schema_meta",
                "sources",
                "documents",
                "checks",
                "document_decisions",
            },
        )

    def test_default_sources_exist(self) -> None:
        with database.get_connection() as connection:
            rows = connection.execute(
                "SELECT id FROM sources ORDER BY id"
            ).fetchall()

        self.assertEqual(
            [row["id"] for row in rows],
            ["mchs", "mintrud", "minzdrav"],
        )

    def test_foreign_keys_are_enabled(self) -> None:
        with database.get_connection() as connection:
            foreign_keys_enabled = connection.execute(
                "PRAGMA foreign_keys"
            ).fetchone()[0]

        self.assertEqual(foreign_keys_enabled, 1)

    def test_schema_version_is_one(self) -> None:
        with database.get_connection() as connection:
            row = connection.execute(
                """
                SELECT value
                FROM schema_meta
                WHERE key = 'schema_version'
                """
            ).fetchone()

        self.assertIsNotNone(row)
        self.assertEqual(row["value"], "1")


if __name__ == "__main__":
    unittest.main()
