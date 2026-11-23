"""Local static/API server for the TypePilot offline lesson cache."""
from __future__ import annotations

import base64
import json
import mimetypes
import os
import sqlite3
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent
CACHE_DIR = ROOT / "Data" / "api-cache"
CUSTOM_DB = Path(os.environ.get("TYPEPILOT_CUSTOM_DB", ROOT / "Data" / "custom-lessons.sqlite"))


def custom_db() -> sqlite3.Connection:
    CUSTOM_DB.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(CUSTOM_DB)
    db.row_factory = sqlite3.Row
    db.execute("""CREATE TABLE IF NOT EXISTS custom_lessons (
        lesson_id TEXT PRIMARY KEY,
        lesson_type TEXT NOT NULL,
        lesson_desc TEXT NOT NULL,
        lesson_data TEXT NOT NULL,
        duration TEXT NOT NULL DEFAULT '',
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""")
    return db


def load_cache() -> list[dict]:
    entries = []
    for path in CACHE_DIR.glob("*.json"):
        try:
            entry = json.loads(path.read_text(encoding="utf-8"))
            entry["_size"] = len(entry.get("payload", ""))
            entries.append(entry)
        except (OSError, ValueError):
            continue
    return entries


CACHE = load_cache()


def lesson_rows(lesson_type: str):
    db_path = (ROOT / "tgurudb.db").as_uri() + "?mode=ro"
    with sqlite3.connect(db_path, uri=True) as db:
        db.row_factory = sqlite3.Row
        rows = db.execute(
            "SELECT lesson_id, lesson_data, lesson_desc, lesson_type "
            "FROM lessons WHERE lesson_type = ? ORDER BY lesson_id",
            (lesson_type,),
        ).fetchall()
    result = {}
    for row in rows:
        item = dict(row)
        # The frontend calls .split(".") on lesson IDs when starting a lesson.
        item["lesson_id"] = str(item["lesson_id"])
        item["duration"] = ""
        result[item["lesson_id"]] = item
    with custom_db() as db:
        custom_rows = db.execute(
            "SELECT lesson_id, lesson_data, lesson_desc, lesson_type, duration "
            "FROM custom_lessons WHERE lesson_type = ? ORDER BY lesson_id",
            (lesson_type,),
        ).fetchall()
    for row in custom_rows:
        item = dict(row)
        item["lesson_id"] = str(item["lesson_id"])
        result[item["lesson_id"]] = item
    return sorted(result.values(), key=lambda item: float(item["lesson_id"]))


def get_lesson_by_id(lesson_id: str):
    with custom_db() as db:
        row = db.execute(
            "SELECT lesson_id, lesson_data, lesson_desc, lesson_type, duration "
            "FROM custom_lessons WHERE lesson_id = ?", (lesson_id,),
        ).fetchone()
    if row:
        return dict(row)
    try:
        numeric_id = float(lesson_id)
    except (TypeError, ValueError):
        return None
    db_path = (ROOT / "tgurudb.db").as_uri() + "?mode=ro"
    with sqlite3.connect(db_path, uri=True) as db:
        db.row_factory = sqlite3.Row
        row = db.execute(
            "SELECT lesson_id, lesson_data, lesson_desc, lesson_type "
            "FROM lessons WHERE lesson_id = ?", (numeric_id,),
        ).fetchone()
    if not row:
        return None
    item = dict(row)
    item["lesson_id"] = str(item["lesson_id"])
    item["duration"] = ""
    return item


def save_lesson(request: dict):
    lesson_type = str(request.get("lesson_type", "")).strip().lower()
    description = str(request.get("lesson_desc", "")).strip()
    data = str(request.get("lesson_data", "")).strip()
    duration = str(request.get("duration", "")).strip()
    if not lesson_type or not description or not data:
        return {"error": "Language, description, and lesson text are required."}, 400
    if len(description) > 160 or len(data) > 1_000_000:
        return {"error": "Description or lesson text is too long."}, 400
    allowed_durations = {"01:00 Mins", "02:00 Mins", "03:00 Mins", "05:00 Mins",
                         "10:00 Mins", "15:00 Mins", "20:00 Mins", "30:00 Mins"}
    if duration and duration not in allowed_durations:
        return {"error": "Choose a valid lesson duration."}, 400

    lesson_id = str(request.get("lesson_id", "")).strip()
    if not lesson_id:
        existing = lesson_rows(lesson_type)
        max_milli_id = max((int(round(float(row["lesson_id"]) * 1000)) for row in existing), default=0)
        next_milli_id = max_milli_id + 1
        lesson_id = f"{next_milli_id // 1000}.{next_milli_id % 1000:03d}"
    try:
        float(lesson_id)
    except ValueError:
        return {"error": "Invalid lesson ID."}, 400
    with custom_db() as db:
        db.execute("""INSERT INTO custom_lessons
            (lesson_id, lesson_type, lesson_desc, lesson_data, duration, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(lesson_id) DO UPDATE SET
                lesson_type=excluded.lesson_type,
                lesson_desc=excluded.lesson_desc,
                lesson_data=excluded.lesson_data,
                duration=excluded.duration,
                updated_at=CURRENT_TIMESTAMP""",
            (lesson_id, lesson_type, description, data, duration))
    return {"success": True, "lesson_id": lesson_id}, 200


def get_payload(api_path: str, request: dict | None = None):
    matches = []
    for entry in CACHE:
        if entry.get("api_path") != api_path:
            continue
        try:
            saved_request = json.loads(entry.get("request_body") or "{}")
        except ValueError:
            continue
        if request is None or saved_request == request:
            matches.append(entry)
    if not matches:
        return None
    entry = max(matches, key=lambda item: item.get("_size", 0))
    try:
        return json.loads(base64.b64decode(entry["payload"]))
    except (ValueError, KeyError, json.JSONDecodeError):
        return None


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, fmt, *args):
        print("[TypePilot] " + fmt % args)

    def _send_json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self._send_json({})

    def do_POST(self):
        parsed = urlparse(self.path)
        if not parsed.path.startswith("/api/"):
            return self._send_json({"error": "not found"}, 404)
        length = int(self.headers.get("Content-Length", "0"))
        try:
            request = json.loads(self.rfile.read(length) or b"{}")
        except ValueError:
            return self._send_json({"error": "invalid JSON"}, 400)
        endpoint = parsed.path.removeprefix("/api/")
        # The bundled Axios client already has /api/ as its base URL, while
        # the app also prefixes requests with /api/. Accept that doubled path.
        if endpoint.startswith("api/"):
            endpoint = endpoint.removeprefix("api/")
        lesson_type = request.get("lesson_type") if isinstance(request, dict) else None
        if endpoint == "savelesson" and isinstance(request, dict):
            payload, status = save_lesson(request)
            return self._send_json(payload, status)
        if endpoint == "getalllessonsbytype" and lesson_type:
            return self._send_json(lesson_rows(str(lesson_type)))
        if endpoint == "getlessonidsbytype" and lesson_type:
            return self._send_json([
                {"lesson_id": row["lesson_id"]} for row in lesson_rows(str(lesson_type))
            ])
        if endpoint == "getlessonbyid" and isinstance(request, dict):
            item = get_lesson_by_id(str(request.get("lessonid", "")))
            return self._send_json([item] if item else [])
        result = get_payload(endpoint, request)
        if result is not None:
            return self._send_json(result)
        # No local cache exists for account history or performance. Keep those
        # guest views empty rather than failing the whole dashboard.
        if parsed.path.rsplit("/", 1)[-1] in {
            "getperformance", "getlessonperformance", "getuserdetail", "checkvalidity"
        }:
            return self._send_json([])
        return self._send_json({"error": "no local lesson cache for this request"}, 404)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path in {"/api/showlessonpractice", "/api/api/showlessonpractice"}:
            lesson_type = parse_qs(parsed.query).get("lesson_type", [""])[0]
            rows = lesson_rows(lesson_type)
            # The Exam Practice view uses legacy property names.
            return self._send_json([
                {
                    "lessonid": str(row["lesson_id"]),
                    "lessondesc": row["lesson_desc"],
                    "lessondata": row["lesson_data"],
                    "timelesson": row.get("duration", ""),
                }
                for row in rows
            ])
        return super().do_GET()


if __name__ == "__main__":
    host = "0.0.0.0"
    port = int(os.environ.get("PORT", "8765"))
    print(f"TypePilot server ready on {host}:{port} (lesson cache: {len(CACHE)} entries)")
    ThreadingHTTPServer((host, port), Handler).serve_forever()
