"""Проверки журнала запусков источников в SQLite."""

import sqlite3
import tempfile
import unittest
from pathlib import Path

from storage import database
from storage.checks import (
    finish_check,
    get_check,
    list_checks,
    start_check,
)


class CheckStorageTestCase(unittest.TestCase):
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

    def test_check_is_started_and_finished_successfully(self) -> None:
        check_id = start_check("mchs")

        running_check = get_check(check_id)

        self.assertIsNotNone(running_check)
        self.assertEqual(running_check["result"], "running")
        self.assertIsNone(running_check["finished_at"])

        result = finish_check(
            check_id,
            result="success",
            found_count=10,
            added_count=7,
            skipped_duplicates=3,
        )

        finished_check = get_check(check_id)

        self.assertEqual(result.result, "success")
        self.assertEqual(result.found_count, 10)
        self.assertEqual(result.added_count, 7)
        self.assertEqual(result.skipped_duplicates, 3)
        self.assertEqual(finished_check["result"], "success")
        self.assertIsNotNone(finished_check["finished_at"])

    def test_error_is_saved_in_log(self) -> None:
        check_id = start_check("mintrud")

        finish_check(
            check_id,
            result="error",
            error_message="ReadTimeout",
        )

        stored = get_check(check_id)

        self.assertEqual(stored["result"], "error")
        self.assertEqual(stored["error_message"], "ReadTimeout")

    def test_checks_can_be_filtered_by_source(self) -> None:
        mchs_check_id = start_check("mchs")
        finish_check(mchs_check_id, result="success")

        minzdrav_check_id = start_check("minzdrav")
        finish_check(minzdrav_check_id, result="success")

        mchs_checks = list_checks("mchs")

        self.assertEqual(len(mchs_checks), 1)
        self.assertEqual(mchs_checks[0]["source_id"], "mchs")

    def test_unknown_source_is_rejected(self) -> None:
        with self.assertRaises(sqlite3.IntegrityError):
            start_check("unknown-source")

    def test_invalid_result_is_rejected(self) -> None:
        check_id = start_check("mchs")

        with self.assertRaises(ValueError):
            finish_check(
                check_id,
                result="unexpected",
            )

    def test_negative_counts_are_rejected(self) -> None:
        check_id = start_check("mchs")

        with self.assertRaises(ValueError):
            finish_check(
                check_id,
                result="success",
                found_count=-1,
            )

    def test_missing_check_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            finish_check(
                999,
                result="error",
                error_message="Проверка не найдена",
            )


if __name__ == "__main__":
    unittest.main()
