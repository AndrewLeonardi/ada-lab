"""Ada, live: a small read-only web service that streams what she is doing to the 3D lab as it happens.

    ada live [--port 8787]

Runs next to the work loop on the server (behind Caddy for HTTPS). It only reads her database:
- GET /live/state           her state now (working, resting, idle) and today's spend against the caps
- GET /live/recent?n=60     her most recent room events, to set the scene when someone opens the lab
- GET /live/stream?after=ID her room events as they happen (server-sent events; resumes after a dropped connection)

Room events are already public (the website replays them); nothing else is exposed.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from . import db

ORIGINS = os.environ.get("ADA_LIVE_ORIGINS", "https://andrewleonardi.github.io,http://localhost:5180").split(",")
MAX_STREAMS = 40
PING_SECONDS = 15
STATE_FILE = db.DB_PATH.with_name("state.json")
_streams = threading.BoundedSemaphore(MAX_STREAMS)


def _connect() -> sqlite3.Connection:
    con = sqlite3.connect(f"file:{db.DB_PATH}?mode=ro", uri=True, timeout=5)
    con.row_factory = sqlite3.Row
    return con


def _events(con, after: int, limit: int = 200) -> list[dict]:
    return [{"id": r["id"], "at": r["at"], **json.loads(r["event"])} for r in
            con.execute("SELECT id, at, event FROM events WHERE id > ? ORDER BY id LIMIT ?", (after, limit))]


def state(con) -> dict:
    s = json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}
    return {"state": s.get("state"), "since": s.get("since"), "daily_usd": s.get("daily_usd"),
            "total_usd": s.get("total_usd"), "spend_today": round(db.spent(con, db.budget_day()), 4),
            "spend_total": round(db.spent(con), 4), "budget_day": db.budget_day(),
            "resets_at": db.next_day_start(), "now": time.time()}


class Handler(BaseHTTPRequestHandler):
    server_version = "ada-live"

    def log_message(self, *args):  # keep the service quiet; Caddy logs requests
        pass

    def _head(self, code: int, ctype: str):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        origin = self.headers.get("Origin", "")
        if origin in ORIGINS:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.send_header("Cache-Control", "no-store")

    def _json(self, obj, code: int = 200):
        body = json.dumps(obj).encode()
        self._head(code, "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        url = urlparse(self.path)
        q = parse_qs(url.query)
        try:
            if url.path == "/live/state":
                with _connect() as con:
                    return self._json(state(con))
            if url.path == "/live/recent":
                n = max(1, min(400, int(q.get("n", ["60"])[0])))
                with _connect() as con:
                    last = con.execute("SELECT COALESCE(MAX(id), 0) FROM events").fetchone()[0]
                    return self._json(_events(con, last - n, n))
            if url.path == "/live/stream":
                return self._stream(int(self.headers.get("Last-Event-ID") or q.get("after", ["0"])[0]))
            return self._json({"error": "not found"}, 404)
        except (BrokenPipeError, ConnectionResetError):
            return None
        except ValueError:
            return self._json({"error": "bad request"}, 400)

    def _stream(self, after: int):
        if not _streams.acquire(blocking=False):
            return self._json({"error": "too many viewers, try again soon"}, 503)
        try:
            self._head(200, "text/event-stream")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            self.wfile.write(b"retry: 3000\n\n")
            con = _connect()
            if not after:  # a new viewer starts from now (recent history comes from /live/recent)
                after = con.execute("SELECT COALESCE(MAX(id), 0) FROM events").fetchone()[0]
            ping = time.time()
            while True:
                for e in _events(con, after):
                    after = e["id"]
                    self.wfile.write(f"id: {after}\ndata: {json.dumps(e)}\n\n".encode())
                if time.time() - ping > PING_SECONDS:
                    self.wfile.write(f"event: state\ndata: {json.dumps(state(con))}\n\n".encode())
                    ping = time.time()
                self.wfile.flush()
                time.sleep(1)
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            _streams.release()


def serve(port: int = 8787, host: str = "127.0.0.1"):
    ThreadingHTTPServer.daemon_threads = True
    with ThreadingHTTPServer((host, port), Handler) as httpd:
        print(f"ada live on http://{host}:{port}/live/state", flush=True)
        httpd.serve_forever()
