"""Freshness policy shared by the representation study and the worker's Requests cache."""
from email.utils import parsedate_to_datetime
import re


STANDARD = {"accept", "accept-encoding", "accept-language", "user-agent", "connection"}
BYPASS = {"authorization", "cookie", "cookie2", "proxy-authorization", "range", "cache-control", "pragma",
          "x-api-key", "api-key", "x-auth-token"}
HOP = {"connection", "keep-alive", "proxy-authenticate", "proxy-authorization", "te", "trailer",
       "transfer-encoding", "upgrade"}
TOKEN = re.compile(r"^[!#$%&'*+.^_`|~0-9a-z-]+$", re.I)


def freshness(response, wall, delay):
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

