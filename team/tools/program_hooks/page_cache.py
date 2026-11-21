"""Small, explicitly fresh public responses shared by one member's consecutive Python processes."""
from contextlib import contextmanager
import hashlib
import io
import json
import sqlite3
import time
from urllib.parse import urlsplit

import requests
from requests.adapters import HTTPAdapter
from urllib3.response import HTTPResponse
from urllib3._collections import HTTPHeaderDict

from page_freshness import BYPASS, HOP, STANDARD, freshness


MAX_BYTES = 1024 * 1024
MAX_ENTRIES = 32


def install(path):
    original = requests.Session.send

    def send(session, request, **kwargs):
        method, url = request.method, request.url
        if method not in ("GET", "HEAD", "OPTIONS"):
            _forget(path)
            try:
                return original(session, request, **kwargs)
            finally:
                _forget(path)
        if method != "GET":
            return original(session, request, **kwargs)
        headers = {k.lower(): v for k, v in request.headers.items()}
        if "cache-control" in headers or "pragma" in headers:
            _forget(path, url)
        parts = urlsplit(url)
        # Preserve custom transports, streaming, authentication, proxies, redirects and hooks.
        if (type(session) is not requests.Session or type(session.get_adapter(url)) is not HTTPAdapter
                or request.body is not None or kwargs.get("stream") or kwargs.get("cert")
                or (parts.scheme == "https" and kwargs.get("verify", True) is not True)
                or kwargs.get("proxies") or session.cert
                or session.auth or session.cookies or any(request.hooks.values())
                or parts.scheme not in ("http", "https") or parts.query or parts.fragment or parts.username is not None
                or headers.keys() - (STANDARD | {"x-cursor"}) or headers.keys() & BYPASS):
            return original(session, request, **kwargs)
        key = hashlib.sha256(json.dumps([url, sorted(headers.items())]).encode()).hexdigest()
        started = time.monotonic()
        epoch = None
        try:
            with _store(path) as db:
                epoch = db.execute("SELECT generation FROM version").fetchone()[0]
                found = db.execute("SELECT status, reason, headers, body, aged, received FROM pages "
                                   "WHERE key=? AND expires>?", (key, started)).fetchone()
        except (sqlite3.Error, OSError):
            found = None
        if found:
            status, reason, fields, body, age, received = found
            fields = HTTPHeaderDict(json.loads(fields))
            fields["Age"] = str(int(age + started - received))
            raw = HTTPResponse(body=io.BytesIO(body), headers=fields, status=status, reason=reason,
                               preload_content=False)
            response = session.get_adapter(url).build_response(request, raw)
            response.content  # Match non-streaming Requests, including repeated reads.
            response._hive_public_cache_hit = True
            return response
        response = original(session, request, **kwargs)
        received = time.monotonic()
        lifetime = freshness(response, time.time(), received - started)
        if epoch is None:
            return response
        vary = {h.strip().lower() for h in response.headers.get("Vary", "").split(",")}
        if not lifetime or response.history or response.url != url or ("x-cursor" in headers and "x-cursor" not in vary):
            _forget(path, url)
            return response
        # Read the body only after Requests has consumed it normally. Unsupported encodings pass through.
        if response.headers.get("Content-Encoding", "identity").lower() != "identity":
            return response
        limit, initial_age = lifetime
        ttl = min(60., limit - initial_age)
        if ttl <= 0:
            _forget(path, url)
            return response
        if len(response.content) > MAX_BYTES:
            return response
        fields = [(k, v) for k, v in response.raw.headers.iteritems() if k.lower() not in HOP]
        encoded_fields = json.dumps(fields)
        size = len(response.content) + len(encoded_fields.encode()) + len(url.encode()) + len(key) + len(response.reason or "")
        if size > MAX_BYTES:
            return response
        try:
            with _store(path) as db:
                db.execute("BEGIN IMMEDIATE")
                if db.execute("SELECT generation FROM version").fetchone()[0] != epoch:
                    return response  # A request invalidated the cache during this origin fetch.
                db.execute("DELETE FROM pages WHERE expires<=? OR key=?", (received, key))
                db.execute("INSERT INTO pages VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                           (key, url, response.status_code, response.reason, encoded_fields, response.content,
                            initial_age, received, received + ttl, size, received))
                count, total = db.execute("SELECT COUNT(*), SUM(size) FROM pages").fetchone()
                while count > MAX_ENTRIES or total > MAX_BYTES:
                    oldest, dropped = db.execute("SELECT key,size FROM pages ORDER BY born,key LIMIT 1").fetchone()
                    db.execute("DELETE FROM pages WHERE key=?", (oldest,))
                    count -= 1
                    total -= dropped
        except (sqlite3.Error, OSError):
            pass
        return response

    requests.Session.send = send


@contextmanager
def _store(path):
    db = sqlite3.connect(path, timeout=0.2)
    try:
        with db:
            db.execute("CREATE TABLE IF NOT EXISTS pages (key TEXT PRIMARY KEY, url, status, reason, headers, body,"
                       " aged, received, expires, size, born)")
            db.execute("CREATE TABLE IF NOT EXISTS version (id INTEGER PRIMARY KEY, generation INTEGER NOT NULL)")
            db.execute("INSERT OR IGNORE INTO version VALUES(1,0)")
            db.commit()
            yield db
    finally:
        db.close()


def _forget(path, url=None):
    try:
        with _store(path) as db:
            db.execute("UPDATE version SET generation=generation+1")
            if url is None:
                db.execute("DELETE FROM pages")
            else:
                db.execute("DELETE FROM pages WHERE url=?", (url,))
    except (sqlite3.Error, OSError):
        pass
