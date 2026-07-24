"""Проверки определения даты публикации."""

import unittest

from storage.publication_dates import (
    extract_publication_date,
    normalize_date_value,
)


class PublicationDateTestCase(unittest.TestCase):
    def test_iso_date_is_preserved(self) -> None:
        self.assertEqual(
            normalize_date_value("2026-05-15"),
            "2026-05-15",
        )

    def test_russian_date_is_converted(self) -> None:
        self.assertEqual(
            normalize_date_value("1 июня 2026 г."),
            "2026-06-01",
        )

    def test_mintrud_possible_date_is_used(self) -> None:
        self.assertEqual(
            extract_publication_date(
                {
                    "title": "Приказ Минтруда",
                    "possible_date": "17 апреля 2026",
                }
            ),
            "2026-04-17",
        )

    def test_mchs_file_url_date_is_used(self) -> None:
        self.assertEqual(
            extract_publication_date(
                {
                    "title": "Документ МЧС",
                    "file_url": (
                        "https://mchs.gov.ru/uploads/document/"
                        "2026-06-08/file.pdf"
                    ),
                }
            ),
            "2026-06-08",
        )

    def test_date_can_be_extracted_from_title(self) -> None:
        self.assertEqual(
            extract_publication_date(
                {
                    "title": (
                        "Приказ МЧС России "
                        "от 10 июня 2026 г. № 434"
                    ),
                }
            ),
            "2026-06-10",
        )

    def test_invalid_date_returns_none(self) -> None:
        self.assertIsNone(
            normalize_date_value("31 февраля 2026")
        )


if __name__ == "__main__":
    unittest.main()
