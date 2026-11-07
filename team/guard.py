"""Arnav's rules, enforced in code. These are the team's only filters.

1. Family and relationships are never task material      -> task refused.
2. Spending money, deleting, sending a message as Arnav   -> stop and ask first.
3. No accounts, no logins, no sign-ups                    -> hard block,
   except: logging in to a site Arnav names for one run (--allow-login site)
   with credentials he keeps in his local vault. Sign-ups stay blocked.
"""
import re
import sys
from urllib.parse import urlparse

FAMILY = re.compile(
    r"\bmy\s+(wife|husband|girl ?friend|boy ?friend|partner|fianc[eé]e?|spouse|mom|mum|mother|dad|father|"
    r"parents?|sister|brother|siblings?|sons?|daughters?|kids?|child(ren)?|baby|family|grand(ma|pa|mother|father|"
    r"parents?)|aunt|uncle|cousins?|nieces?|nephews?|in-?laws?|ex|crush|date|relatives?)\b"
    r"|\b(dating|break ?up|divorce|marriage|anniversary|valentine'?s?|relationship (advice|problem|issue)s?|"
    r"family (member|matter|issue|drama|trip|dinner|event|tree|plan)s?|wedding|my relationship|love life)\b",
    re.I)

LOGIN_TEXT = re.compile(r"\b(log ?in|sign ?in|sign ?up|register|create (an |your )?account|join now|"
                        r"get started for free|continue with (google|github|apple|facebook))\b", re.I)
LOGIN_URL = re.compile(r"/(login|log-in|signin|sign-in|signup|sign-up|register|join|auth|oauth|sso|"
                       r"account/create|accounts/login|session/new)(\b|/|\?|$)", re.I)
SIGNUP = re.compile(r"(sign ?up|register|create (an |your )?account|join now|get started for free|signup|sign-up)", re.I)
SPEND_TEXT = re.compile(r"\b(buy|purchase|checkout|check out|pay|place (your )?order|add to (cart|basket|bag)|"
                        r"subscribe|donate|upgrade|start (free )?trial|book now|reserve|order now|"
                        r"confirm (order|payment|booking|purchase))\b", re.I)
SPEND_URL = re.compile(r"/(checkout|cart|basket|payment|billing|pay|subscribe|donate|order)(\b|/|\?|$)", re.I)
SEND_TEXT = re.compile(r"\b(send|post|publish|submit|reply|comment|tweet|share|email|message|contact|"
                       r"invite|upload)\b", re.I)
DELETE_TEXT = re.compile(r"\b(delete|remove|erase|discard|clear all|unsubscribe|close account|deactivate|"
                         r"empty (trash|bin))\b", re.I)

CODE_RULES = [
    ("delete", re.compile(r"\b(os\.(remove|unlink|rmdir|removedirs)|shutil\.rmtree|\.unlink\(|\.rmdir\(|"
                          r"send2trash|rm\s+-[rf]|subprocess[^\n]*\brm\b)")),
    ("send", re.compile(r"\b(smtplib|sendmail|send_message|twilio|slack_sdk|telegram|discord|webhook|"
                        r"(requests|httpx|session)\.(post|put|patch|delete)\(|urlopen\([^)]*data=)")),
    ("spend", re.compile(r"\b(stripe|paypal|braintree|razorpay|checkout|purchase|payment)\b", re.I)),
]


# Query endpoints that take POST but only read data.
READONLY_POST = re.compile(r"(requests|httpx|session)\.post\(\s*[\"']https://api\.osv\.dev/v1/(query|querybatch)")


class Blocked(Exception):
    """An action that breaks a hard rule (login/sign-up, family)."""


def check_task(text):
    """Rule 1. Returns a reason string if the text is off-limits, else None."""
    m = FAMILY.search(text or "")
    if m:
        return f"family/relationships are never task material (matched '{m.group(0)}')"
    return None


class Guard:
    """Rules 2 and 3. `approve` is 'ask' (prompt on the terminal), 'never' or 'always'."""

    def __init__(self, board, approve="ask", allow_login=()):
        self.board = board
        self.mode = approve
        self.allow_login = {d.lower().removeprefix("www.") for d in allow_login}
        self.pending = []  # actions that need Arnav

    def login_allowed(self, url):
        host = (urlparse(url or "").hostname or "").lower().removeprefix("www.")
        return any(host == d or host.endswith("." + d) for d in self.allow_login)

    def ask(self, agent, kind, detail):
        from . import memory
        category = {"spend money": "spend", "delete": "delete", "send a message as Arnav": "send"}.get(kind, kind)
        standing = memory.policy().get(category, "ask")
        if standing == "allow":
            decision = "approved (standing approval in memory/policy.json)"
        elif standing == "deny":
            decision = "denied (memory/policy.json)"
        elif self.mode == "always":
            decision = "approved (pre-authorized)"
        elif self.mode == "ask" and sys.stdin.isatty():
            print(f"\n*** {agent} wants to {kind.upper()}: {detail}\n*** Allow? [y/N] ", end="", flush=True)
            decision = "approved" if input().strip().lower() in ("y", "yes") else "denied"
        else:
            decision = "not asked - waiting for Arnav"
            self.pending.append({"agent": agent, "kind": kind, "detail": detail})
        self.board.record_approval(agent, kind, detail, decision)
        self.board.log(agent, "approval", f"{kind}: {detail} -> {decision}")
        return decision.startswith("approved")

    # ---- browser ------------------------------------------------------
    def check_url(self, url):
        if LOGIN_URL.search(url or "") and not (self.login_allowed(url) and not SIGNUP.search(url)):
            raise Blocked(f"login/sign-up page refused: {url}")

    def check_browser(self, agent, action, element=None, page_url="", typed_fields=()):
        """Raise Blocked, return False if denied, True if allowed."""
        kind = action.get("action")
        if kind == "goto":
            self.check_url(action.get("url", ""))
            if SPEND_URL.search(action.get("url", "")):
                return self.ask(agent, "spend money", f"open {action['url']}")
            return True
        if element is None:
            return True
        text = " ".join(str(element.get(k) or "") for k in ("text", "label", "name", "href", "type"))
        if SIGNUP.search(text):
            raise Blocked(f"sign-up refused: {text.strip()[:80]}")
        if element.get("type") == "password":
            raise Blocked("the model never types passwords; use the login action on an allowed site")
        if (LOGIN_TEXT.search(text) or LOGIN_URL.search(element.get("href") or "")) and not self.login_allowed(page_url):
            raise Blocked(f"login/sign-up element refused: {text.strip()[:80]}")
        if kind == "type" and (element.get("autocomplete") or "").startswith("cc-"):
            raise Blocked("payment card field refused")
        if kind in ("click", "press", "type"):
            if SPEND_TEXT.search(text) or SPEND_URL.search(element.get("href") or ""):
                return self.ask(agent, "spend money", f"click '{text.strip()[:80]}' on {page_url}")
            if DELETE_TEXT.search(text):
                return self.ask(agent, "delete", f"click '{text.strip()[:80]}' on {page_url}")
            is_search = element.get("search") or any(f.get("search") for f in typed_fields)
            if kind == "click" and SEND_TEXT.search(text) and not is_search and element.get("tag") != "a":
                return self.ask(agent, "send a message as Arnav", f"click '{text.strip()[:80]}' on {page_url}")
            if kind == "press" and typed_fields and not all(f.get("search") for f in typed_fields):
                return self.ask(agent, "send a message as Arnav", f"submit form on {page_url}")
        return True

    # ---- code ---------------------------------------------------------
    def check_code(self, agent, code):
        for kind, rx in CODE_RULES:
            m = rx.search(code)
            if m and kind == "send" and READONLY_POST.search(code) and len(rx.findall(code)) == len(READONLY_POST.findall(code)):
                continue  # read-only query APIs that happen to use POST (e.g. OSV)
            if m:
                label = {"delete": "delete", "send": "send a message as Arnav", "spend": "spend money"}[kind]
                if not self.ask(agent, label, f"run code containing `{m.group(0)}`"):
                    return False
        return True
