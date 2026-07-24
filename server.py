#!/usr/bin/env python3
"""Минимальный локальный сервер для MVP ОТ-Монитор.

Сервер:
1. Раздаёт статические файлы проекта из папки проекта.
2. Отвечает на GET /api/health.
3. Запускает run_demo_check.py через POST /api/run-demo-check.
4. Не допускает параллельный запуск проверки.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from datetime import datetime
from functools import partial
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import tempfile

from api_routes import SQLiteApiMixin
from storage.database import initialize_database
from storage.checks import list_checks
from storage.documents import list_documents


HOST = "127.0.0.1"
PORT = 8000
BASE_DIR = Path(__file__).resolve().parent
RUN_DEMO_CHECK_PATH = BASE_DIR / "run_demo_check.py"
REVIEW_COMMENTS_PATH = BASE_DIR / "data" / "review_comments.json"
CLIENT_TXT_REPORT_PATH = BASE_DIR / "data" / "ZAMECHANIYA_DLYA_RAZRABOTCHIKA.txt"
CLIENT_RTF_REPORT_PATH = BASE_DIR / "data" / "ZAMECHANIYA_DLYA_RAZRABOTCHIKA.rtf"
CLIENT_OUTPUT_DIR = BASE_DIR / "CLIENT_OUTPUT"
CLIENT_OUTPUT_RTF_REPORT_PATH = CLIENT_OUTPUT_DIR / "ZAMECHANIYA_DLYA_RAZRABOTCHIKA.rtf"

DOCUMENT_RELATED_REVIEW_ZONES = {
    "document_card",
    "document_statuses",
    "engineer_comment",
    "documents_list",
}

run_lock = threading.Lock()
is_check_running = False
review_comments_lock = threading.Lock()


def ensure_review_comments_file() -> None:
    """Создаёт файл замечаний, если он ещё не существует."""
    REVIEW_COMMENTS_PATH.parent.mkdir(parents=True, exist_ok=True)

    if not REVIEW_COMMENTS_PATH.exists():
        REVIEW_COMMENTS_PATH.write_text("[]\n", encoding="utf-8")


def load_review_comments() -> list[dict[str, object]]:
    """Читает список замечаний из JSON-файла."""
    ensure_review_comments_file()

    try:
        data = json.loads(REVIEW_COMMENTS_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        data = []

    return data if isinstance(data, list) else []


def save_review_comments(comments: list[dict[str, object]]) -> None:
    """Сохраняет список замечаний в JSON-файл."""
    ensure_review_comments_file()
    REVIEW_COMMENTS_PATH.write_text(
        json.dumps(comments, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def format_review_comment_datetime(value: object) -> str:
    """Преобразует ISO-время замечания в читаемый формат."""
    text = str(value or "").strip()
    if not text:
        return "—"

    try:
        normalized = text.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        return parsed.strftime("%d.%m.%Y %H:%M")
    except ValueError:
        return text


def should_show_document_in_report(comment: dict[str, object]) -> bool:
    """Показывает документ в отчёте только для документных зон."""
    zone_id = str(comment.get("zone_id") or "").strip()
    if zone_id not in DOCUMENT_RELATED_REVIEW_ZONES:
        return False

    document_title = str(comment.get("document_title") or "").strip()
    return bool(document_title)


def build_grouped_review_lines(comments: list[dict[str, object]]) -> list[str]:
    """Собирает общую текстовую структуру отчёта по замечаниям."""
    if not comments:
        return ["Замечаний пока нет.", ""]

    grouped_comments: dict[str, list[dict[str, object]]] = {}
    group_titles: list[str] = []
    for comment in comments:
        zone_title = str(comment.get("zone_title") or "Без названия").strip()
        if zone_title not in grouped_comments:
            grouped_comments[zone_title] = []
            group_titles.append(zone_title)
        grouped_comments[zone_title].append(comment)

    lines: list[str] = []
    item_index = 1
    for group_number, zone_title in enumerate(group_titles, start=1):
        lines.append(f"{group_number}. {zone_title}")
        lines.append("")

        for comment in grouped_comments[zone_title]:
            lines.append(f"[{item_index}]")
            lines.append(f"Дата: {format_review_comment_datetime(comment.get('created_at'))}")
            lines.append(f"Блок: {zone_title}")

            if should_show_document_in_report(comment):
                lines.append(f"Документ: {str(comment.get('document_title') or '').strip()}")

            lines.append("Текст замечания:")
            lines.append(str(comment.get("comment_text") or "").strip() or "—")
            lines.append("")
            item_index += 1

    return lines


def build_review_report_text(comments: list[dict[str, object]]) -> str:
    """Собирает человекочитаемый TXT-отчёт по замечаниям."""
    generated_at = datetime.now().strftime("%d.%m.%Y %H:%M")
    lines = [
        "ОТ-Монитор — отчёт по замечаниям заказчика",
        "",
        f"Дата формирования: {generated_at}",
        f"Всего замечаний: {len(comments)}",
        "",
    ]
    lines.extend(build_grouped_review_lines(comments))
    return "\n".join(lines)


def escape_rtf_text(text: object) -> str:
    """Экранирует текст для безопасной вставки в RTF."""
    value = str(text or "")
    escaped_parts: list[str] = []

    for char in value:
        code_point = ord(char)
        if char == "\\":
            escaped_parts.append("\\\\")
        elif char == "{":
            escaped_parts.append("\\{")
        elif char == "}":
            escaped_parts.append("\\}")
        elif char == "\n":
            escaped_parts.append("\\par\n")
        elif code_point > 127:
            signed_value = code_point if code_point <= 32767 else code_point - 65536
            escaped_parts.append(f"\\u{signed_value}?")
        else:
            escaped_parts.append(char)

    return "".join(escaped_parts)


def build_review_report_rtf(comments: list[dict[str, object]]) -> str:
    """Собирает Word-совместимый RTF-отчёт по замечаниям."""
    generated_at = datetime.now().strftime("%d.%m.%Y %H:%M")
    plain_lines = [
        "ЗАМЕЧАНИЯ ДЛЯ РАЗРАБОТЧИКА",
        "",
        "ОТ-Монитор — отчёт по замечаниям заказчика",
        f"Дата формирования: {generated_at}",
        f"Всего замечаний: {len(comments)}",
        "",
    ]
    plain_lines.extend(build_grouped_review_lines(comments))

    rtf_lines = [
        r"{\rtf1\ansi\deff0",
        r"{\fonttbl{\f0 Arial;}}",
        r"\viewkind4\uc1\pard\lang1049\f0\fs24 ",
    ]

    for line in plain_lines:
        if line:
            rtf_lines.append(f"{escape_rtf_text(line)}\\par")
        else:
            rtf_lines.append(r"\par")

    rtf_lines.append("}")
    return "\n".join(rtf_lines)


def safe_write_text_file(target_path: Path, content: str, encoding: str) -> bool:
    """Пытается безопасно обновить текстовый файл без падения сервера."""
    target_path.parent.mkdir(parents=True, exist_ok=True)

    temp_fd, temp_path_str = tempfile.mkstemp(
        prefix=f"{target_path.stem}_",
        suffix=target_path.suffix,
        dir=str(target_path.parent),
        text=True,
    )

    temp_path = Path(temp_path_str)
    try:
        with os.fdopen(temp_fd, "w", encoding=encoding, newline="") as temp_file:
            temp_file.write(content)

        try:
            os.replace(temp_path, target_path)
            return True
        except OSError as error:
            sys.stderr.write(f"Не удалось обновить файл отчёта {target_path}: {error}\n")
            return False
    finally:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass


def refresh_client_review_reports() -> dict[str, bool]:
    """Обновляет клиентские копии TXT и RTF-отчётов из текущего JSON."""
    comments = load_review_comments()
    txt_report = build_review_report_text(comments)
    rtf_report = build_review_report_rtf(comments)
    txt_updated = safe_write_text_file(CLIENT_TXT_REPORT_PATH, txt_report, "utf-8-sig")
    rtf_updated = safe_write_text_file(CLIENT_RTF_REPORT_PATH, rtf_report, "utf-8")
    return {
        "txt_updated": txt_updated,
        "rtf_updated": rtf_updated,
    }


class OTMonitorRequestHandler(SQLiteApiMixin, SimpleHTTPRequestHandler):
    """HTTP handler для статических файлов и минимального API."""

    def do_GET(self) -> None:
        request_path = self.path.split("?", 1)[0]
        if self.handle_sqlite_get(request_path):
            return

        if self.path == "/api/review-comments/report-rtf":
            self.handle_review_comments_report_rtf()
            return

        if self.path == "/api/review-comments/report":
            self.handle_review_comments_report()
            return

        if self.path == "/api/review-comments":
            self.handle_get_review_comments()
            return

        if self.path == "/api/review-comments/export":
            self.handle_export_review_comments()
            return

        if self.path == "/api/health":
            self.send_json(
                HTTPStatus.OK,
                {
                    "ok": True,
                    "message": "OT-Monitor local server is running",
                },
            )
            return

        super().do_GET()

    def do_POST(self) -> None:
        request_path = self.path.split("?", 1)[0]
        if self.handle_sqlite_post(request_path):
            return

        if self.path == "/api/run-demo-check":
            self.handle_run_demo_check()
            return

        if self.path == "/api/review-comments":
            self.handle_save_review_comment()
            return

        if self.path != "/api/run-demo-check":
            self.send_json(
                HTTPStatus.NOT_FOUND,
                {
                    "ok": False,
                    "message": "Endpoint not found",
                },
            )
            return

    def handle_run_demo_check(self) -> None:
        """Запускает run_demo_check.py и возвращает результат."""
        global is_check_running

        content_length = self.headers.get("Content-Length")
        if content_length:
            try:
                _ = self.rfile.read(int(content_length))
            except Exception:
                # Тело запроса здесь не используется, поэтому безопасно игнорируем.
                pass

        with run_lock:
            if is_check_running:
                self.send_json(
                    HTTPStatus.CONFLICT,
                    {
                        "ok": False,
                        "message": "Проверка уже выполняется",
                    },
                )
                return

            is_check_running = True

        try:
            documents_count_before = len(list_documents())
            existing_check_ids = {
                int(check["id"])
                for check in list_checks()
            }

            child_env = os.environ.copy()
            child_env["PYTHONIOENCODING"] = "utf-8"
            child_env["PYTHONUTF8"] = "1"

            completed = subprocess.run(
                [sys.executable, "-X", "utf8", str(RUN_DEMO_CHECK_PATH)],
                cwd=str(BASE_DIR),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=child_env,
                check=False,
            )

            documents_count_after = len(list_documents())

            source_results = [
                check
                for check in list_checks()
                if int(check["id"]) not in existing_check_ids
            ]
            source_results.reverse()

            successful_sources = [
                result
                for result in source_results
                if result["result"] == "success"
            ]
            failed_sources = [
                result
                for result in source_results
                if result["result"] in {"partial", "error"}
            ]

            if source_results and not failed_sources:
                overall_result = "success"
                message = "Все источники проверены успешно."
            elif successful_sources:
                overall_result = "partial"
                message = "Проверка завершена частично."
            else:
                overall_result = "error"
                message = "Не удалось успешно проверить источники."

            self.send_json(
                HTTPStatus.OK,
                {
                    "ok": overall_result == "success",
                    "overall_result": overall_result,
                    "message": message,
                    "returncode": completed.returncode,
                    "documents_count_before": documents_count_before,
                    "documents_count_after": documents_count_after,
                    "added_count": (
                        documents_count_after
                        - documents_count_before
                    ),
                    "source_results": source_results,
                    "stdout": completed.stdout,
                    "stderr": completed.stderr,
                },
            )
        except Exception as error:
            self.send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {
                    "ok": False,
                    "message": "Не удалось выполнить backend-проверку.",
                    "returncode": -1,
                    "documents_count_before": None,
                    "documents_count_after": None,
                    "check_log_count_before": None,
                    "check_log_count_after": None,
                    "stdout": "",
                    "stderr": f"{type(error).__name__}: {error}",
                },
            )
        finally:
            with run_lock:
                is_check_running = False

    def handle_save_review_comment(self) -> None:
        """Сохраняет одно замечание заказчика в JSON-файл."""
        content_length = self.headers.get("Content-Length")
        if not content_length:
            self.send_json(
                HTTPStatus.BAD_REQUEST,
                {
                    "ok": False,
                    "message": "Пустой запрос",
                },
            )
            return

        try:
            raw_body = self.rfile.read(int(content_length))
            payload = json.loads(raw_body.decode("utf-8"))
        except (ValueError, json.JSONDecodeError):
            self.send_json(
                HTTPStatus.BAD_REQUEST,
                {
                    "ok": False,
                    "message": "Не удалось прочитать замечание",
                },
            )
            return

        if not isinstance(payload, dict):
            self.send_json(
                HTTPStatus.BAD_REQUEST,
                {
                    "ok": False,
                    "message": "Некорректный формат замечания",
                },
            )
            return

        comment_text = str(payload.get("comment_text", "")).strip()
        if not comment_text:
            self.send_json(
                HTTPStatus.BAD_REQUEST,
                {
                    "ok": False,
                    "message": "Текст замечания пустой",
                },
            )
            return

        with review_comments_lock:
            comments = load_review_comments()
            comments.append(payload)
            save_review_comments(comments)
            report_update_result = refresh_client_review_reports()

        response_payload: dict[str, object] = {
            "ok": True,
            "message": "Замечание сохранено",
            "saved_count": len(comments),
        }

        if not report_update_result.get("rtf_updated", True):
            response_payload["warning"] = "report_file_locked"

        self.send_json(HTTPStatus.OK, response_payload)

    def handle_export_review_comments(self) -> None:
        """Отдаёт JSON-файл замечаний для скачивания."""
        with review_comments_lock:
            ensure_review_comments_file()
            response_bytes = REVIEW_COMMENTS_PATH.read_bytes()

        file_name = (
            "TECHNICHESKIY_FAIL_ZAMECHANIY_DLYA_RAZRABOTCHIKA_"
            f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.json"
        )

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Disposition", f'attachment; filename="{file_name}"')
        self.send_header("Content-Length", str(len(response_bytes)))
        self.end_headers()
        self.wfile.write(response_bytes)

    def handle_get_review_comments(self) -> None:
        """Возвращает текущий список замечаний и их количество."""
        with review_comments_lock:
            comments = load_review_comments()

        self.send_json(
            HTTPStatus.OK,
            {
                "ok": True,
                "count": len(comments),
                "comments": comments,
            },
        )

    def handle_review_comments_report(self) -> None:
        """Формирует и отдаёт TXT-отчёт по замечаниям."""
        with review_comments_lock:
            comments = load_review_comments()

        report_text = build_review_report_text(comments)
        response_bytes = report_text.encode("utf-8-sig")
        file_name = f"ZAMECHANIYA_DLYA_RAZRABOTCHIKA_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt"

        with review_comments_lock:
            safe_write_text_file(CLIENT_TXT_REPORT_PATH, report_text, "utf-8-sig")

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Disposition", f'attachment; filename="{file_name}"')
        self.send_header("Content-Length", str(len(response_bytes)))
        self.end_headers()
        self.wfile.write(response_bytes)

    def handle_review_comments_report_rtf(self) -> None:
        """Формирует и отдаёт Word-совместимый RTF-отчёт по замечаниям."""
        with review_comments_lock:
            comments = load_review_comments()

        report_rtf = build_review_report_rtf(comments)
        response_bytes = report_rtf.encode("utf-8")
        file_name = f"ZAMECHANIYA_DLYA_RAZRABOTCHIKA_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.rtf"

        with review_comments_lock:
            safe_write_text_file(CLIENT_RTF_REPORT_PATH, report_rtf, "utf-8")
            safe_write_text_file(CLIENT_OUTPUT_RTF_REPORT_PATH, report_rtf, "utf-8")

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/rtf; charset=utf-8")
        self.send_header("Content-Disposition", f'attachment; filename="{file_name}"')
        self.send_header("Content-Length", str(len(response_bytes)))
        self.end_headers()
        self.wfile.write(response_bytes)

    def send_json(self, status_code: HTTPStatus, payload: dict[str, object]) -> None:
        """Отправляет JSON-ответ."""
        response_bytes = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.end_headers()
        self.wfile.write(response_bytes)

    def log_message(self, format: str, *args: object) -> None:
        """Пишет короткий лог в stdout."""
        sys.stdout.write("%s - - [%s] %s\n" % (self.address_string(), self.log_date_time_string(), format % args))


def main() -> None:
    """Точка входа сервера."""
    initialize_database()
    handler_class = partial(OTMonitorRequestHandler, directory=str(BASE_DIR))
    server = ThreadingHTTPServer((HOST, PORT), handler_class)

    print(f"OT-Monitor local server is running at http://{HOST}:{PORT}")
    print(f"Serving files from: {BASE_DIR}")
    print("Available endpoints:")
    print("  GET  /api/health")
    print("  GET  /api/documents")
    print("  GET  /api/checks")
    print("  GET  /api/decisions")
    print("  POST /api/documents/<id>/decision")
    print("  POST /api/documents/<id>/download")
    print("  GET  /api/review-comments")
    print("  GET  /api/review-comments/report")
    print("  GET  /api/review-comments/report-rtf")
    print("  GET  /api/review-comments/export")
    print("  POST /api/review-comments")
    print("  POST /api/run-demo-check")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
