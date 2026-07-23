"""Скачивание файлов документов и сохранение результата в SQLite."""

from __future__ import annotations

import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlparse

import requests

from storage import database
from storage.documents import get_document


PROJECT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DOWNLOAD_DIR = PROJECT_DIR / "data" / "downloaded_documents"

ALLOWED_EXTENSIONS = {
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
}

CONTENT_TYPE_EXTENSIONS = {
    "application/pdf": ".pdf",
    "application/msword": ".doc",
    (
        "application/vnd.openxmlformats-officedocument."
        "wordprocessingml.document"
    ): ".docx",
    "application/vnd.ms-excel": ".xls",
    (
        "application/vnd.openxmlformats-officedocument."
        "spreadsheetml.sheet"
    ): ".xlsx",
}

DEFAULT_MAX_FILE_SIZE = 100 * 1024 * 1024


@dataclass(frozen=True)
class DownloadResult:
    """Результат скачивания файла документа."""

    document_id: int
    status: str
    saved_file_path: str
    message: str
    downloaded: bool


def update_download_state(
    document_id: int,
    *,
    status: str,
    saved_file_path: str = "",
) -> None:
    """Обновляет состояние скачивания документа."""
    with database.get_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE documents
            SET download_status = ?,
                saved_file_path = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                status,
                saved_file_path,
                document_id,
            ),
        )

        if cursor.rowcount == 0:
            raise ValueError(
                f"Документ с ID {document_id} не найден"
            )


def sanitize_filename(value: str) -> str:
    """Удаляет опасные символы из имени файла."""
    cleaned = re.sub(
        r"[^\w.\-]+",
        "_",
        value,
        flags=re.UNICODE,
    )
    cleaned = cleaned.strip("._")

    return cleaned or "document"


def filename_from_content_disposition(
    header_value: str,
) -> str:
    """Извлекает имя файла из Content-Disposition."""
    if not header_value:
        return ""

    match = re.search(
        r"filename\*?=(?:UTF-8''|\"?)([^\";]+)",
        header_value,
        flags=re.IGNORECASE,
    )

    if match is None:
        return ""

    return unquote(match.group(1).strip())


def resolve_filename(
    document_id: int,
    file_url: str,
    response: requests.Response,
) -> str:
    """Определяет безопасное имя и расширение файла."""
    header_filename = filename_from_content_disposition(
        response.headers.get("Content-Disposition", "")
    )

    url_filename = unquote(
        Path(urlparse(file_url).path).name
    )

    original_filename = (
        header_filename
        or url_filename
        or f"document_{document_id}"
    )

    extension = Path(original_filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        content_type = (
            response.headers
            .get("Content-Type", "")
            .split(";", 1)[0]
            .strip()
            .lower()
        )
        extension = CONTENT_TYPE_EXTENSIONS.get(
            content_type,
            "",
        )

    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError(
            "Неподдерживаемый тип файла"
        )

    stem = Path(original_filename).stem
    safe_stem = sanitize_filename(stem)

    return f"document_{document_id}_{safe_stem}{extension}"


def path_for_database(file_path: Path) -> str:
    """Возвращает путь, пригодный для хранения в базе."""
    try:
        return file_path.relative_to(
            PROJECT_DIR
        ).as_posix()
    except ValueError:
        return str(file_path)


def download_document_file(
    document_id: int,
    *,
    destination_dir: str | Path | None = None,
    max_file_size: int = DEFAULT_MAX_FILE_SIZE,
) -> DownloadResult:
    """Скачивает прикреплённый файл документа."""
    document = get_document(document_id)

    if document is None:
        raise ValueError(
            f"Документ с ID {document_id} не найден"
        )

    current_path_text = str(
        document.get("saved_file_path") or ""
    )
    current_status = str(
        document.get("download_status") or ""
    )

    if current_status == "downloaded" and current_path_text:
        current_path = Path(current_path_text)

        if not current_path.is_absolute():
            current_path = PROJECT_DIR / current_path

        if current_path.exists():
            return DownloadResult(
                document_id=document_id,
                status="downloaded",
                saved_file_path=current_path_text,
                message="Файл уже был скачан",
                downloaded=False,
            )

    file_url = str(
        document.get("file_url") or ""
    ).strip()

    if not file_url:
        update_download_state(
            document_id,
            status="unavailable",
        )
        return DownloadResult(
            document_id=document_id,
            status="unavailable",
            saved_file_path="",
            message="У документа нет ссылки на файл",
            downloaded=False,
        )

    output_dir = Path(
        destination_dir or DEFAULT_DOWNLOAD_DIR
    )
    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    temp_path: Path | None = None

    try:
        with requests.get(
            file_url,
            stream=True,
            timeout=(10, 60),
            headers={
                "User-Agent": (
                    "OT-Monitor/1.0 "
                    "(local document monitor)"
                )
            },
        ) as response:
            response.raise_for_status()

            content_length = response.headers.get(
                "Content-Length"
            )

            if (
                content_length
                and int(content_length) > max_file_size
            ):
                raise ValueError(
                    "Размер файла превышает допустимый лимит"
                )

            filename = resolve_filename(
                document_id,
                file_url,
                response,
            )
            output_path = output_dir / filename

            file_descriptor, temp_path_text = (
                tempfile.mkstemp(
                    prefix=f"{filename}.",
                    suffix=".part",
                    dir=str(output_dir),
                )
            )
            temp_path = Path(temp_path_text)

            downloaded_size = 0

            with os.fdopen(
                file_descriptor,
                "wb",
            ) as temp_file:
                for chunk in response.iter_content(
                    chunk_size=64 * 1024
                ):
                    if not chunk:
                        continue

                    downloaded_size += len(chunk)

                    if downloaded_size > max_file_size:
                        raise ValueError(
                            "Размер файла превышает "
                            "допустимый лимит"
                        )

                    temp_file.write(chunk)

            os.replace(
                temp_path,
                output_path,
            )
            temp_path = None

        saved_path = path_for_database(
            output_path
        )

        update_download_state(
            document_id,
            status="downloaded",
            saved_file_path=saved_path,
        )

        return DownloadResult(
            document_id=document_id,
            status="downloaded",
            saved_file_path=saved_path,
            message="Файл успешно скачан",
            downloaded=True,
        )

    except (
        requests.RequestException,
        OSError,
        ValueError,
    ) as error:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()

        update_download_state(
            document_id,
            status="failed",
        )

        return DownloadResult(
            document_id=document_id,
            status="failed",
            saved_file_path="",
            message=str(error),
            downloaded=False,
        )
