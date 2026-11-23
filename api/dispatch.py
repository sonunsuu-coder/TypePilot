"""Route TypePilot's legacy /api/* endpoints through a Vercel Function."""
from __future__ import annotations

import os
from urllib.parse import parse_qs, urlencode, urlparse

# Vercel's deployed source tree is read-only. Keep custom lesson writes in the
# function's writable temp area; they remain available only while that instance
# stays warm. The bundled lesson database remains the durable read-only source.
os.environ.setdefault("TYPEPILOT_CUSTOM_DB", "/tmp/typepilot-custom-lessons.sqlite")

from local_server import Handler as LocalHandler  # noqa: E402


class handler(LocalHandler):
    def _restore_api_path(self) -> None:
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query, keep_blank_values=True)
        original = query.pop("__typepilot_route", [""])[0].strip("/")
        if not original:
            return
        remaining_query = urlencode(query, doseq=True)
        self.path = f"/api/{original}"
        if remaining_query:
            self.path += f"?{remaining_query}"

    def do_GET(self):
        self._restore_api_path()
        return super().do_GET()

    def do_POST(self):
        self._restore_api_path()
        return super().do_POST()
