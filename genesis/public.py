"""Bounded public synthetic demo; no ServiceNow or external-AI connection."""
import asyncio
from collections import deque
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import time

from starlette.requests import Request
from starlette.responses import JSONResponse

from .api import app
from .runtime import visitor_database


SESSION_SECONDS = 3600
MAX_SESSIONS = 100
MAX_BODY_BYTES = 65536
MAX_DATABASE_BYTES = 2 * 1024 * 1024
ALLOWED_POSTS = {"/verify", "/compare", "/explain", "/demo/requests"}
ALLOWED_GETS = {"/", "/health", "/demo/config", "/demo/requests",
                "/demo/examples/fixed", "/demo/examples/vulnerable"}
DATABASE_NAME = re.compile(r"^[0-9a-f]{48}\.sqlite3(?:-(?:journal|wal|shm))?$")


class PublicDemo:
    def __init__(self, application):
        self.application = application
        self.sessions = {}
        self.slots = asyncio.Semaphore(2)
        self.new_sessions = deque()
        self.all_calls = deque()
        self.cleaned = False

    @staticmethod
    def _directory():
        directory = Path(os.environ.get("GENESIS_PUBLIC_DATA", "/tmp/genesis-public"))
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    @staticmethod
    def _json(detail, status):
        return JSONResponse({"detail": detail}, status)

    @staticmethod
    def _prune(counter, now, seconds=60):
        while counter and now - counter[0] >= seconds:
            counter.popleft()

    @staticmethod
    def _allowed(method, path):
        if method in ("GET", "HEAD"):
            return (path in ALLOWED_GETS or path.startswith("/assets/") or
                    (path.startswith("/demo/requests/") and path.count("/") == 3))
        if method == "POST":
            return path in ALLOWED_POSTS or (path.startswith("/demo/requests/") and path.endswith("/actions"))
        return False

    @staticmethod
    def _delete_database(directory, identifier):
        for suffix in ("", "-journal", "-wal", "-shm"):
            (directory / (identifier + ".sqlite3" + suffix)).unlink(missing_ok=True)

    def _cleanup(self, directory, now):
        for identifier, session in list(self.sessions.items()):
            if now - session["created"] > SESSION_SECONDS and not session.get("active"):
                self._delete_database(directory, identifier)
                del self.sessions[identifier]
        if not self.cleaned:
            cutoff = time.time() - (SESSION_SECONDS * 2)
            for path in directory.iterdir():
                if path.is_file() and DATABASE_NAME.fullmatch(path.name) and path.stat().st_mtime < cutoff:
                    path.unlink(missing_ok=True)
            self.cleaned = True

    @staticmethod
    def _database_size(directory, identifier):
        return sum((directory / (identifier + ".sqlite3" + suffix)).stat().st_size
                   for suffix in ("", "-journal", "-wal", "-shm")
                   if (directory / (identifier + ".sqlite3" + suffix)).exists())

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.application(scope, receive, send)
        key = os.environ.get("GENESIS_SESSION_SECRET", "")
        if len(key) < 32:
            return await self._json("Public demo requires a private session secret", 503)(scope, receive, send)
        if os.environ.get("GENESIS_PUBLIC_REQUIRE_HTTPS", "true").lower() == "true" and scope.get("scheme") != "https":
            return await self._json("HTTPS is required", 400)(scope, receive, send)

        request = Request(scope, receive)
        path, method = scope["path"], request.method
        if not self._allowed(method, path):
            return await self._json("Endpoint unavailable in public demo", 404)(scope, receive, send)
        if path == "/health":
            return await JSONResponse({"status": "ok", "mode": "public_synthetic_demo"})(scope, receive, send)

        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > MAX_BODY_BYTES:
                return await self._json("Request too large", 413)(scope, receive, send)

        if method == "POST":
            if request.headers.get("content-type", "").split(";")[0] != "application/json":
                return await self._json("Use application/json", 415)(scope, receive, send)
            try:
                data = json.loads(body)
                if not isinstance(data, dict) or data.get("external_ai"):
                    raise ValueError()
                for field in ("snapshot", "proposed"):
                    if field in data:
                        supplied_snapshot = data[field]
                        reference = json.loads((Path(__file__).with_name("static") / "fixed.json").read_text())
                        reference["policy"] = supplied_snapshot["policy"]
                        reference["revision"] = supplied_snapshot["revision"]
                        if supplied_snapshot != reference:
                            raise ValueError()
                if "bound" in data and (type(data["bound"]) is not int or not 0 <= data["bound"] <= 3):
                    raise ValueError()
                if "snapshot" in data and path != "/demo/requests":
                    data["timeout_ms"] = min(data.get("timeout_ms", 1000), 1000)
                body = json.dumps(data).encode()
            except (ValueError, KeyError, TypeError):
                return await self._json("Public demo accepts synthetic examples only; external AI is disabled", 422)(scope, receive, send)

        now = time.monotonic()
        directory = self._directory()
        self._cleanup(directory, now)
        self._prune(self.all_calls, now)
        if len(self.all_calls) >= 600:
            return await self._json("Demo is busy; try later", 429)(scope, receive, send)
        self.all_calls.append(now)

        def sign(identifier):
            return hmac.new(key.encode(), identifier.encode(), hashlib.sha256).hexdigest()

        supplied = request.cookies.get("genesis_demo", "")
        identifier, _, signature = supplied.partition(".")
        valid = identifier in self.sessions and hmac.compare_digest(signature, sign(identifier))
        if not valid:
            self._prune(self.new_sessions, now)
            if len(self.sessions) >= MAX_SESSIONS or len(self.new_sessions) >= 30:
                return await self._json("Demo is busy; try later", 503)(scope, receive, send)
            identifier = secrets.token_hex(24)
            self.sessions[identifier] = {"created": now, "window": now, "calls": 0, "writes": 0}
            self.new_sessions.append(now)

        session = self.sessions[identifier]
        if now - session["window"] >= 60:
            session.update(window=now, calls=0)
        session["calls"] += 1

        async def cookie_response(response):
            async def with_cookie(message):
                if message["type"] == "http.response.start":
                    headers = list(message.get("headers", []))
                    secure = "; Secure" if scope.get("scheme") == "https" else ""
                    value = f"genesis_demo={identifier}.{sign(identifier)}; HttpOnly; SameSite=Strict; Path=/; Max-Age={SESSION_SECONDS}{secure}"
                    headers.append((b"set-cookie", value.encode()))
                    message = {**message, "headers": headers}
                await send(message)
            await response(scope, receive, with_cookie)

        if session["calls"] > 60:
            return await cookie_response(self._json("Please wait before trying again", 429))
        if method == "POST":
            if self._database_size(directory, identifier) > MAX_DATABASE_BYTES:
                return await cookie_response(self._json("Demo session storage limit reached", 507))
            session["writes"] += 1
            if session["writes"] > 100:
                return await cookie_response(self._json("Demo session limit reached", 429))

        sent = False

        async def replay_body():
            nonlocal sent
            if not sent:
                sent = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        async def cookie_send(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                secure = "; Secure" if scope.get("scheme") == "https" else ""
                value = f"genesis_demo={identifier}.{sign(identifier)}; HttpOnly; SameSite=Strict; Path=/; Max-Age={SESSION_SECONDS}{secure}"
                headers.append((b"set-cookie", value.encode()))
                message = {**message, "headers": headers}
            await send(message)

        token = visitor_database.set(str(directory / (identifier + ".sqlite3")))
        session["active"] = session.get("active", 0) + 1
        acquired = False
        try:
            try:
                await asyncio.wait_for(self.slots.acquire(), timeout=1.0)
                acquired = True
            except TimeoutError:
                return await cookie_response(self._json("Demo is busy; try again shortly", 503))
            await self.application(scope, replay_body, cookie_send)
        finally:
            if acquired:
                self.slots.release()
            session["active"] -= 1
            visitor_database.reset(token)


public_app = PublicDemo(app)
