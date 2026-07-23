"""Проверки общего сценария запуска парсеров."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from run_demo_check import SourceChain, run_source_chain
from storage import database
from storage.checks import list_checks
from storage.documents import list_documents


class RunDemoCheckTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_directory = tempfile.TemporaryDirectory()
        self.base_dir = Path(self.temp_directory.name)

        (self.base_dir / "data").mkdir()

        self.original_database_path = database.DATABASE_PATH
        database.DATABASE_PATH = (
            self.base_dir / "data" / "test.db"
        )
        database.initialize_database()

        self.source_chain = SourceChain(
            source_id="mchs",
            source_name="МЧС России",
            inspect_script="inspect_mchs_docs.py",
            result_file="data/mchs_documents_filtered.json",
        )

    def tearDown(self) -> None:
        database.DATABASE_PATH = (
            self.original_database_path
        )
        self.temp_directory.cleanup()

    def test_successful_parser_result_is_imported(
        self,
    ) -> None:
        result_path = (
            self.base_dir
            / self.source_chain.result_file
        )

        def fake_run(*args, **kwargs):
            result_path.write_text(
                json.dumps(
                    [
                        {
                            "title": "Документ МЧС",
                            "url":
                                "https://example.test/mchs/1",
                        }
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            return True, "Парсер завершён"

        with patch(
            "run_demo_check.run_python_script",
            side_effect=fake_run,
        ):
            result = run_source_chain(
                self.source_chain,
                base_dir=self.base_dir,
            )

        self.assertTrue(result.success)
        self.assertEqual(
            result.import_result.added_count,
            1,
        )
        self.assertEqual(len(list_documents()), 1)
        self.assertEqual(
            list_checks()[0]["result"],
            "success",
        )

    def test_parser_error_is_written_to_sqlite(
        self,
    ) -> None:
        result_path = (
            self.base_dir
            / self.source_chain.result_file
        )

        def fake_run(*args, **kwargs):
            result_path.write_text(
                json.dumps(
                    {
                        "status": "error",
                        "error": "ReadTimeout",
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            return False, "ReadTimeout"

        with patch(
            "run_demo_check.run_python_script",
            side_effect=fake_run,
        ):
            result = run_source_chain(
                self.source_chain,
                base_dir=self.base_dir,
            )

        self.assertFalse(result.success)
        self.assertEqual(
            result.import_result.result,
            "error",
        )
        self.assertEqual(
            list_checks()[0]["error_message"],
            "ReadTimeout",
        )

    def test_stale_result_is_not_imported(
        self,
    ) -> None:
        result_path = (
            self.base_dir
            / self.source_chain.result_file
        )

        result_path.write_text(
            json.dumps(
                [
                    {
                        "title": "Старый документ",
                        "url":
                            "https://example.test/stale",
                    }
                ],
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        with patch(
            "run_demo_check.run_python_script",
            return_value=(False, "Аварийное завершение"),
        ):
            result = run_source_chain(
                self.source_chain,
                base_dir=self.base_dir,
            )

        self.assertFalse(result.success)
        self.assertEqual(list_documents(), [])
        self.assertEqual(
            list_checks()[0]["result"],
            "error",
        )


if __name__ == "__main__":
    unittest.main()
