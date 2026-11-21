"""A per-run reader of small public GET representations. No global hooks or disk state."""
from collections import OrderedDict
from dataclasses import dataclass, replace
from email.utils import parsedate_to_datetime
import re
import time
from urllib.parse import urlsplit

import requests
from requests.structures import CaseInsensitiveDict


# Custom public selectors must be named by the caller. All accepted headers join the key,
# even if the origin forgets to list a representation selector in Vary.
STANDARD = {"accept", "accept-encoding", "accept-language", "user-agent", "connection"}
BYPASS = {"authorization", "cookie", "cookie2", "proxy-authorization", "range", "cache-control", "pragma",
          "x-api-key", "api-key", "x-auth-token"}
HOP = {"connection", "keep-alive", "proxy-authenticate", "proxy-authorization", "te", "trailer",
       "transfer-encoding", "upgrade"}
TOKEN = re.compile(r"^[!#$%&'*+.^_`|~0-9a-z-]+$", re.I)


@dataclass(frozen=True)
class Page:
    """Raw content-coded representation (HTTP transfer framing removed) and end-to-end headers."""
    url: str
    status: int
    fields: tuple
    body: bytes

    @property
    def headers(self):
        return CaseInsensitiveDict(self.fields)


@dataclass(frozen=True)
class Entry:
    page: Page
    received: float
    initial_age: float
    expires: float
    size: int


def _freshness(response, wall, delay):
    h = response.headers
    if (response.status_code != 200 or any(k in h for k in
            ("Set-Cookie", "Set-Cookie2", "Content-Range", "WWW-Authenticate", "Proxy-Authenticate",
             "Authentication-Info", "Proxy-Authentication-Info", "Pragma"))):
        return None
    if any(token.strip().lower() not in {"", "close", "keep-alive"} for token in h.get("Connection", "").split(",")):
        return None
    vary = h.get("Vary")
    if vary is not None and any(s.strip() == "*" or not TOKEN.fullmatch(s.strip()) for s in vary.split(",")):
        return None
    # Narrow grammar: reject ambiguous, conflicting or unfamiliar directives rather than guessing their semantics.
    directives = [x.strip().lower() for x in h.get("Cache-Control", "").split(",")]
    maximum = [x[8:] for x in directives if re.fullmatch(r"max-age=[0-9]{1,10}", x)]
    if len(directives) != 2 or directives.count("public") != 1 or len(maximum) != 1:
        return None
    age = h.get("Age", "0")
    if not re.fullmatch(r"[0-9]{1,10}", age):
        return None
    try:
        date = parsedate_to_datetime(h["Date"])
        if date.tzinfo is None or len(response.raw.headers.getlist("Date")) != 1:
            return None
        apparent_age = max(0, wall - date.timestamp())
    except (KeyError, ValueError, TypeError, OverflowError, OSError):
        return None
    initial_age = max(apparent_age, int(age) + delay)
    return int(maximum[0]), initial_age


class _NoRedirects(requests.Session):
    # Session.send(allow_redirects=False) normally prepares Response.next, consuming even a compressed redirect
    # body. This reader hands the original redirect and body to the caller; it has no implicit follow-up.
    def resolve_redirects(self, *args, **kwargs):
        return iter(())


class PublicPages:
    """One context per run, one caller at a time. GET never follows redirects implicitly."""
    def __init__(self, *, public_headers=(), max_entries=32, max_bytes=2**20, max_body=2**21,
                 max_ttl=60, enabled=True, clock=time.monotonic):
        if min(max_entries, max_bytes, max_body, max_ttl) <= 0:
            raise ValueError("cache bounds must be positive")
        self.session = _NoRedirects()
        self.session.trust_env = False
        self.allowed = STANDARD | {s.lower() for s in public_headers}
        self.max_entries, self.max_bytes = max_entries, max_bytes
        self.max_body, self.max_ttl, self.clock = max_body, max_ttl, clock
        self.enabled = enabled
        self.entries = OrderedDict()
        self.size = self.hits = self.fetches = 0
        self.closed = False

    def __enter__(self):
        if self.closed:
            raise RuntimeError("page reader is closed")
        return self

    def __exit__(self, *_):
        self.entries.clear()
        self.size = 0
        self.session.close()
        self.closed = True

    def _remove(self, key):
        self.size -= self.entries.pop(key).size

    def _forget_url(self, url):
        for key in list(self.entries):
            if key[0] == url:
                self._remove(key)

    def get(self, url, *, headers=None, timeout=5):
        if self.closed:
            raise RuntimeError("page reader is closed")
        req = self.session.prepare_request(requests.Request("GET", url, headers=headers))
        parts = urlsplit(req.url)
        fields = tuple(sorted((k.lower(), v) for k, v in req.headers.items()))
        names = {k for k, _ in fields}
        eligible = (self.enabled and parts.scheme in ("http", "https") and not parts.query and parts.username is None
                    and not self.session.cert and not self.session.auth and not self.session.proxies
                    and names <= self.allowed and not names & BYPASS and not any(k.startswith("if-") for k in names))
        key = (req.url, fields)
        now = self.clock()
        for old in list(self.entries):
            if self.entries[old].expires <= now:
                self._remove(old)
        if eligible and key in self.entries:
            entry = self.entries[key]
            self.entries.move_to_end(key)
            self.hits += 1
            fields = tuple((k, v) for k, v in entry.page.fields if k.lower() != "age")
            age = int(entry.initial_age + now - entry.received)
            return replace(entry.page, fields=fields + (("Age", str(age)),))
        if names & {"cache-control", "pragma"}:
            self._forget_url(req.url)
        self.fetches += 1
        with self.session.send(req, stream=True, timeout=timeout, allow_redirects=False) as response:
            received, wall = self.clock(), time.time()
            lifetime = _freshness(response, wall, received - now) if eligible else None
            # Keep encoded bytes and their Content-Encoding/Length together, including on gzip hits.
            body = response.raw.read(self.max_body + 1, decode_content=False)
            if len(body) > self.max_body:
                raise ValueError("page exceeds configured body limit")
            skip = HOP | {s.strip().lower() for s in response.headers.get("Connection", "").split(",")}
            page = Page(req.url, response.status_code,
                        tuple((k, v) for k, v in response.raw.headers.iteritems() if k.lower() not in skip), body)
        if eligible and lifetime is None:
            self._forget_url(req.url)
        if lifetime is not None:
            age_limit, age = lifetime
            ttl = min(self.max_ttl, age_limit - age)
            # Include URL and request/response metadata as well as encoded body in the byte budget.
            size = len(body) + len(req.url) + sum(len(k) + len(v) for k, v in fields + page.fields)
            if ttl <= 0:
                self._forget_url(req.url)
            elif size <= self.max_bytes:
                while len(self.entries) >= self.max_entries or self.size + size > self.max_bytes:
                    self._remove(next(iter(self.entries)))
                self.entries[key] = Entry(page, received, age, received + ttl, size)
                self.size += size
        return page
