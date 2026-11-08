"""Arnav's rules, enforced in code: anything risky happens only under his explicit order.

Risky kinds of action: spend money, delete, send a message as Arnav, log in, sign up, use his credentials,
and touch family/relationship matters.

- His order is the approval. If the task he gave explicitly orders that kind of action, the guard allows it and
  logs the exact sentence it relied on. A negated sentence ("no paying", "don't delete") is never an order.
- Anything he did not order stops: in the terminal it asks him; in serve/web mode it is not done and is listed
  in the report as waiting for him. memory/policy.json can hold standing orders ("allow") or bans ("deny").
- Logins and sign-ups are allowed only on sites his order names (or --allow-login). Credentials stay in the local
  vault: the browser types them itself; they never enter a prompt, the board, a log or a trace.
- Models never type passwords or card numbers themselves.
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

# what counts as Arnav ORDERING each kind of action (verbs in his own task text)
ORDER_VERBS = {
    "spend": r"\b(buy|purchase|pay for|pay|order|subscribe|book|donate|check ?out|rent|reserve|add \S+ to (my )?(cart|basket))\b",
    "delete": r"\b(delete|remove|erase|wipe|clear out|empty|unsubscribe|deactivate|cancel)\b",
    "send": r"\b(send|email|e-mail|message|text|dm|post|publish|reply|comment|tweet|share|submit|invite|upload)\b",
    "login": r"\b(log ?in|sign ?in|login)\b",
    "signup": r"\b(sign ?up|register|create (an |my |a )?account|join)\b",
    "credentials": r"\b(my (credentials|password|login|account)|use my (account|credentials|login))\b",
    "family": FAMILY.pattern,
}
NEGATION = re.compile(r"\b(no|not|don'?t|do not|never|without|avoid|nothing|nor|stop)\b", re.I)
DOMAIN = re.compile(r"\b((?:[a-z0-9-]+\.)+(?:com|org|net|io|ai|co|dev|app|in|uk|me|edu|gov|toscrape\.com))\b", re.I)

LOGIN_TEXT = re.compile(r"\b(log ?in|sign ?in|continue with (google|github|apple|facebook))\b", re.I)
LOGIN_URL = re.compile(r"/(login|log-in|signin|sign-in|auth|oauth|sso|accounts/login|session/new)(\b|/|\?|$)", re.I)
SIGNUP = re.compile(r"(sign ?up|register|create (an |your )?account|join now|get started for free|signup|sign-up|/join\b)", re.I)
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
LABEL = {"spend": "spend money", "delete": "delete", "send": "send a message as Arnav", "login": "log in",
         "signup": "sign up", "credentials": "use Arnav's credentials", "family": "touch family/relationship matters"}


class Blocked(Exception):
    """An action that needs Arnav's order and does not have it, and cannot wait for approval."""


def sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?;\n])\s+|\n", text or "") if s.strip()]


# an order is a verb in command position: start of a sentence/clause, or after and/then/please/to/...
COMMAND_POS = r"(?:^|[,;:]\s*|\b(?:and|then|please|also|to|must|should|can|could|will|go ahead and|you may|now)\s+)"


def parse_orders(goal):
    """{kind: the sentence of Arnav's task that orders it}. Nouns ("a book", "text-generation") and negated
    sentences ("no paying", "don't delete") are not orders."""
    orders = {}
    for sent in sentences(goal):
        for kind, pat in ORDER_VERBS.items():
            if kind == "family":
                m = re.search(pat, sent, re.I)  # a family matter mentioned in his own order is ordered
            else:
                m = re.search(COMMAND_POS + pat + r"(?![-'\w])", sent, re.I)
            if not m:
                continue
            before = sent[:m.start()]
            if NEGATION.search(before[-40:]):  # "no paying", "don't delete anything", "without signing up"
                continue
            orders.setdefault(kind, sent)
    return orders


def ordered_sites(goal, orders, kind):
    sent = orders.get(kind, "")
    sites = {d.lower().removeprefix("www.") for d in DOMAIN.findall(sent)}
    return sites or {d.lower().removeprefix("www.") for d in DOMAIN.findall(goal or "")}


def _family_cell(text):
    try:
        from .cells import use
        return use.on("family_topic") and bool(text) and use.ask("family_topic", text) == "yes"
    except Exception:  # noqa: BLE001
        return False


def check_task(text, goal=""):
    """Family/relationship matters only when Arnav's own order is about them. Reason string, or None.
    Two readers: the rule and the family_topic cell (it also catches 'Mom', 'our son', 'the kids').
    The cell only ever adds blocks: what the rule blocks, the cell can never unlock."""
    m = FAMILY.search(text or "")
    if m:
        if FAMILY.search(goal or ""):
            return None
        return f"touches family/relationships ('{m.group(0)}'), which your order did not ask for"
    if _family_cell(text) and not (FAMILY.search(goal or "") or _family_cell(goal)):
        return "touches family/relationships (family_topic cell), which your order did not ask for"
    return None


class Guard:
    """`approve`: 'ask' (terminal prompt for anything unordered), 'never' (unordered = not done, listed for Arnav)."""

    def __init__(self, board, approve="ask", allow_login=(), goal="", use_model=False):
        self.board = board
        self.mode = approve
        self.goal = goal
        self.orders = parse_orders(goal)
        if use_model and goal:
            self._second_opinion(board)
        self.allow_login = {d.lower().removeprefix("www.") for d in allow_login}
        if "login" in self.orders or "credentials" in self.orders:
            self.allow_login |= ordered_sites(goal, self.orders, "login" if "login" in self.orders else "credentials")
        self.signup_sites = ordered_sites(goal, self.orders, "signup") if "signup" in self.orders else set()
        self.pending = []  # actions waiting for Arnav
        if self.orders:
            board.log("guard", "orders", "; ".join(f"{k}: \"{v[:80]}\"" for k, v in self.orders.items()))

    def _second_opinion(self, board):
        """Two independent readers must agree before a risky kind counts as ordered: the rule-based parser and the
        order-reader member (its own weight edit). If they disagree, the kind is NOT treated as ordered."""
        from . import llm, prompts
        from .cells import use
        if use.orders_on():  # five one-kind cells (spend, delete, send, login, signup) read the order
            model = use.orders(self.goal, board)
        else:
            data, _ = llm.chat_json("order_reader", [{"role": "system", "content": prompts.ORDER_READER},
                                                     {"role": "user", "content": self.goal}], max_new_tokens=40)
            model = {k for k in (data or {}).get("orders", [])} if isinstance(data, dict) else set()
        risky = {"spend", "delete", "send", "login", "signup"}
        rx = set(self.orders) & risky
        for k in rx - model:
            board.log("guard", "disagree", f"'{k}': the parser read an order, the order reader did not - not treated as ordered")
            self.orders.pop(k)
        for k in model - rx:
            board.log("guard", "disagree", f"'{k}': the order reader read an order, the parser did not - not treated as ordered")

    @staticmethod
    def _host(url):
        return (urlparse(url or "").hostname or "").lower().removeprefix("www.")

    def _site_in(self, url, sites):
        h = self._host(url)
        return any(h == d or h.endswith("." + d) for d in sites)

    def login_allowed(self, url):
        return self._site_in(url, self.allow_login)

    def ask(self, agent, kind, detail):
        """kind is one of LABEL's keys. Returns True if the action may go ahead."""
        from . import memory
        if kind in self.orders:
            decision = f"approved by your order: \"{self.orders[kind][:120]}\""
        else:
            standing = memory.policy().get(kind, "ask")
            if standing == "allow":
                decision = "approved (standing order in memory/policy.json)"
            elif standing == "deny":
                decision = "denied (memory/policy.json)"
            elif self.mode == "ask" and sys.stdin.isatty():
                print(f"\n*** {agent} wants to {LABEL[kind].upper()}: {detail}\n*** You did not order this. Allow? [y/N] ",
                      end="", flush=True)
                decision = "approved by you at the prompt" if input().strip().lower() in ("y", "yes") else "denied"
            else:
                decision = "not done - you did not order it (waiting for you)"
                self.pending.append({"agent": agent, "kind": LABEL[kind], "detail": detail})
        self.board.record_approval(agent, LABEL[kind], detail, decision)
        self.board.log(agent, "approval", f"{LABEL[kind]}: {detail} -> {decision}")
        return decision.startswith("approved")

    # ---- browser ------------------------------------------------------
    def check_url(self, url):
        if SIGNUP.search(url or "") and not self._site_in(url, self.signup_sites):
            raise Blocked(f"sign-up page: you did not order a sign-up on this site ({url})")
        if LOGIN_URL.search(url or "") and not self.login_allowed(url):
            raise Blocked(f"login page: you did not order a login on this site ({url})")

    def check_browser(self, agent, action, element=None, page_url="", typed_fields=()):
        """Raise Blocked, return False if not approved, True if allowed."""
        kind = action.get("action")
        if kind == "goto":
            self.check_url(action.get("url", ""))
            if SPEND_URL.search(action.get("url", "")):
                return self.ask(agent, "spend", f"open {action['url']}")
            return True
        if element is None:
            return True
        text = " ".join(str(element.get(k) or "") for k in ("text", "label", "name", "href", "type"))
        if element.get("type") == "password":
            raise Blocked("models never type passwords; the login action types them from your vault")
        if kind == "type" and (element.get("autocomplete") or "").startswith("cc-"):
            raise Blocked("models never type card numbers")
        if SIGNUP.search(text) and not self._site_in(page_url, self.signup_sites):
            raise Blocked(f"sign-up: you did not order a sign-up on this site ('{text.strip()[:60]}')")
        if (LOGIN_TEXT.search(text) or LOGIN_URL.search(element.get("href") or "")) and not self.login_allowed(page_url):
            raise Blocked(f"login: you did not order a login on this site ('{text.strip()[:60]}')")
        if kind in ("click", "press", "type"):
            if SPEND_TEXT.search(text) or SPEND_URL.search(element.get("href") or ""):
                return self.ask(agent, "spend", f"click '{text.strip()[:80]}' on {page_url}")
            if DELETE_TEXT.search(text):
                return self.ask(agent, "delete", f"click '{text.strip()[:80]}' on {page_url}")
            is_search = element.get("search") or any(f.get("search") for f in typed_fields)
            if kind == "click" and SEND_TEXT.search(text) and not is_search and element.get("tag") != "a":
                return self.ask(agent, "send", f"click '{text.strip()[:80]}' on {page_url}")
            if kind == "press" and typed_fields and not all(f.get("search") for f in typed_fields):
                return self.ask(agent, "send", f"submit form on {page_url}")
        return True

    # ---- code ---------------------------------------------------------
    def check_code(self, agent, code):
        for kind, rx in CODE_RULES:
            m = rx.search(code)
            if m and kind == "send" and READONLY_POST.search(code) and len(rx.findall(code)) == len(READONLY_POST.findall(code)):
                continue  # read-only query APIs that happen to use POST (e.g. OSV)
            if m and not self.ask(agent, kind, f"run code containing `{m.group(0)}`"):
                return False
        return True
