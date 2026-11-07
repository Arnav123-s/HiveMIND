"""Arnav's credentials, kept on his machine only, outside the repo.

File: ~/.agent-team/credentials.json (chmod 600), e.g.
  {"quotes.toscrape.com": {"username": "me", "password": "..."}}
The browser tool reads it and types the values itself. They never go into a
model prompt, the board, the logs or a screenshot taken after typing.
"""
import json
import os
from pathlib import Path
from urllib.parse import urlparse

PATH = Path(os.environ.get("AGENT_TEAM_VAULT", Path.home() / ".agent-team" / "credentials.json"))


def lookup(url):
    if not PATH.exists():
        return None
    host = (urlparse(url).hostname or "").lower().removeprefix("www.")
    data = json.loads(PATH.read_text())
    for domain, cred in data.items():
        d = domain.lower().removeprefix("www.")
        if host == d or host.endswith("." + d):
            return cred
    return None
