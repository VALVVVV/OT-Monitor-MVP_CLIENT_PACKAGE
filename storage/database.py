"""Слой работы с SQLite для проекта «ОТ-Монитор»."""

import sqlite3
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "data"
DATABASE_PATH = DATA_DIR / "ot_monitor.db"


def get_connection() -> sqlite3.Connection:
    """Открывает настроенное соединение с базой данных."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")

    return connection


def initialize_database() -> None:
    """Создаёт минимальную структуру базы Этапа 1."""
    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS schema_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sources (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                base_url TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1
                    CHECK (is_active IN (0, 1)),
                last_checked_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id TEXT NOT NULL,
                external_id TEXT,
                title TEXT NOT NULL,
                original_url TEXT NOT NULL,
                publication_date TEXT,
                discovered_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                summary TEXT NOT NULL DEFAULT '',
                file_url TEXT NOT NULL DEFAULT '',
                saved_file_path TEXT NOT NULL DEFAULT '',
                download_status TEXT NOT NULL DEFAULT 'not_requested'
                    CHECK (
                        download_status IN (
                            'not_requested',
                            'downloaded',
                            'failed',
                            'unavailable'
                        )
                    ),
                section TEXT NOT NULL DEFAULT '',
                topic TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'Новое',
                engineer_comment TEXT NOT NULL DEFAULT '',
                unique_key TEXT NOT NULL,
                raw_payload TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (source_id) REFERENCES sources(id),
                UNIQUE (source_id, original_url),
                UNIQUE (unique_key)
            );

            CREATE TABLE IF NOT EXISTS checks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id TEXT NOT NULL,
                trigger_mode TEXT NOT NULL DEFAULT 'manual'
                    CHECK (trigger_mode IN ('manual', 'scheduled', 'import')),
                started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                finished_at TEXT,
                result TEXT NOT NULL DEFAULT 'running'
                    CHECK (result IN ('running', 'success', 'partial', 'error')),
                found_count INTEGER NOT NULL DEFAULT 0,
                added_count INTEGER NOT NULL DEFAULT 0,
                skipped_duplicates INTEGER NOT NULL DEFAULT 0,
                error_message TEXT NOT NULL DEFAULT '',

                FOREIGN KEY (source_id) REFERENCES sources(id)
            );

            CREATE TABLE IF NOT EXISTS document_decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL,
                status TEXT NOT NULL,
                comment TEXT NOT NULL DEFAULT '',
                responsible TEXT NOT NULL DEFAULT 'Инженер по ОТ',
                decided_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (document_id)
                    REFERENCES documents(id)
                    ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_documents_source
                ON documents(source_id);

            CREATE INDEX IF NOT EXISTS idx_documents_status
                ON documents(status);

            CREATE INDEX IF NOT EXISTS idx_documents_publication_date
                ON documents(publication_date);

            CREATE INDEX IF NOT EXISTS idx_documents_discovered_at
                ON documents(discovered_at);

            CREATE INDEX IF NOT EXISTS idx_checks_source_started
                ON checks(source_id, started_at);

            CREATE INDEX IF NOT EXISTS idx_decisions_document
                ON document_decisions(document_id, decided_at);
            """
        )

        connection.executemany(
            """
            INSERT INTO sources (id, name, base_url)
            VALUES (?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                base_url = excluded.base_url,
                updated_at = CURRENT_TIMESTAMP
            """,
            [
                ("mintrud", "Минтруд России", "https://mintrud.gov.ru/docs"),
                (
                    "mchs",
                    "МЧС России",
                    "https://mchs.gov.ru/dokumenty/vse-dokumenty",
                ),
                (
                    "minzdrav",
                    "Минздрав России",
                    "https://minzdrav.gov.ru/documents",
                ),
            ],
        )

        connection.execute(
            """
            INSERT INTO schema_meta (key, value)
            VALUES ('schema_version', '1')
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """
        )


if __name__ == "__main__":
    initialize_database()
    print(f"База данных подготовлена: {DATABASE_PATH}")
