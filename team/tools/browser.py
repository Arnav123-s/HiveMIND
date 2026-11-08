"""A real Chromium the browser specialist drives: navigate, click, type, scroll, read.

Each observation numbers the visible interactive elements on the page; the
specialist answers with an action that refers to those numbers.
"""
import re

from playwright.sync_api import sync_playwright

from .. import config

SNAPSHOT_JS = r"""
(maxEls) => {
  const sel = 'a[href], button, input, select, textarea, summary, [role=button], [role=link], [role=tab], [role=menuitem], [role=searchbox], [role=combobox]';
  const els = Array.from(document.querySelectorAll(sel));
  const out = [];
  let n = 0;
  for (const el of els) {
    const r = el.getBoundingClientRect();
    const st = getComputedStyle(el);
    if (r.width < 2 || r.height < 2 || st.visibility === 'hidden' || st.display === 'none') continue;
    if (el.type === 'hidden') continue;
    n += 1;
    el.setAttribute('data-aid', String(n));
    const text = (el.innerText || el.getAttribute('aria-label') || el.getAttribute('title') ||
                  el.getAttribute('placeholder') || el.value || el.name || '').trim().replace(/\s+/g, ' ');
    const form = el.form || el.closest('form');
    const isSearch = el.type === 'search' || el.getAttribute('role') === 'searchbox' ||
      /search|query|^q$/i.test((el.name || '') + ' ' + (el.id || '') + ' ' + (el.getAttribute('placeholder') || '') + ' ' + (el.getAttribute('aria-label') || '')) ||
      (form && /search/i.test((form.getAttribute('action') || '') + ' ' + (form.getAttribute('role') || '')));
    out.push({id: n, tag: el.tagName.toLowerCase(), type: el.type || el.getAttribute('role') || '',
              text: text.slice(0, 90), href: el.getAttribute('href') || '', name: el.name || '',
              autocomplete: el.getAttribute('autocomplete') || '', search: !!isSearch,
              inview: r.top >= 0 && r.top < window.innerHeight});
  }
  return out;
}
"""


STOP = set("""the and for what with from this that find open page into about which where when who how get give
show tell list read look check site website using use their there then than them they your you are was were has
have had its it's not all any each every one two three first last next top best most more less out off per via
please item items task goal""".split())
EXPAND = {"size": ["gb", "mb", "kb", "bytes"], "price": ["£", "$", "€", "price"], "cost": ["£", "$", "€", "price"],
          "license": ["license"], "version": ["version", "release"], "released": ["release", "19", "20"],
          "when": ["19", "20"], "date": ["19", "20"], "weights": ["safetensors", ".bin", ".gguf"],
          "files": ["safetensors", "files"], "stock": ["stock", "available"], "rating": ["star", "rating"],
          "author": ["by "], "downloads": ["downloads"], "parameters": ["params", "parameters", "b params"]}


def goal_words(goal):
    words = {w for w in re.findall(r"[a-z0-9£$€.\-]{3,}", goal.lower()) if w not in STOP}
    for w in list(words):
        words.update(EXPAND.get(w, []))
    return words


def focus_text(full, goal, head=400, budget=1200):
    """Top of the page plus the lines that matter for the goal (small models drown in page chrome)."""
    lines = [ln.strip() for ln in full.split("\n") if ln.strip()]
    words = goal_words(goal)
    keep = set()
    for i, ln in enumerate(lines):
        low = ln.lower()
        if any(w in low for w in words):
            keep.update(range(max(0, i - 1), min(len(lines), i + 3)))
    picked, used = [], 0
    for i in sorted(keep):
        if used + len(lines[i]) > budget:
            break
        picked.append(lines[i])
        used += len(lines[i]) + 1
    top = full[:head]
    return top + ("\n...\n[lines matching the goal]\n" + "\n".join(picked) if picked else "")


class Browser:
    def __init__(self, headless=True):
        self._pw = sync_playwright().start()
        self._b = self._pw.chromium.launch(headless=headless)
        self._ctx = self._b.new_context(user_agent=None, viewport={"width": 1280, "height": 900})
        self.page = self._ctx.new_page()
        self.page.set_default_timeout(20000)
        self._new_pages = []
        self._ctx.on("page", lambda pg: self._new_pages.append(pg))  # links that open a new tab
        self.elements = {}
        self.typed = []  # fields typed into on the current page
        self.http_status = None  # HTTP status of the last page load (a 404 page still renders, so the model can't tell)
        self._ctx.on("response", self._on_response)

    def _on_response(self, r):
        try:
            if r.request.is_navigation_request() and r.frame.parent_frame is None:
                self.http_status = r.status
        except Exception:  # noqa: BLE001 - a closed page must not break the browser
            pass

    def close(self):
        try:
            self._b.close()
        finally:
            self._pw.stop()

    def _settle(self):
        try:
            self.page.wait_for_load_state("domcontentloaded", timeout=15000)
            self.page.wait_for_load_state("networkidle", timeout=5000)
        except Exception:
            pass

    def goto(self, url):
        try:
            self.page.goto(url, wait_until="domcontentloaded")
        except Exception as e:  # noqa: BLE001 - report a clean reason the model can act on
            msg = str(e).split("\n")[0]
            raise RuntimeError(f"could not open {url}: {msg[:140]}") from None
        self.typed = []
        self._settle()
        if self.page.url.startswith("chrome-error://"):
            raise RuntimeError(f"could not open {url}: the browser got an error page (blocked or certificate problem)")

    def text(self, max_chars=6000):
        try:
            t = self.page.inner_text("body", timeout=5000)
        except Exception:
            t = ""
        return re.sub(r"\n\s*\n+", "\n", t)[:max_chars]

    def observe(self, goal="", max_elements=40, text_chars=1800):
        for attempt in range(3):  # the page may still be navigating
            try:
                els = self.page.evaluate(SNAPSHOT_JS, 400)
                break
            except Exception:  # noqa: BLE001
                if attempt == 2:
                    raise
                self.page.wait_for_timeout(1500)
                self._settle()
        self.elements = {e["id"]: e for e in els}
        words = goal_words(goal)
        hay = {e["id"]: (e["text"] + " " + e["href"]).lower() for e in els}
        # rare words matter more: a word matching 1 element beats one matching 50
        weight = {w: 1.0 / max(1, sum(1 for h in hay.values() if w in h)) for w in words}

        def score(e):
            t = hay[e["id"]]
            hit = sum(weight[w] for w in words if w in t)
            if re.match(r"^(next|previous|more|load more|older|newer)\b|→|»", e["text"].strip(), re.I):
                hit += 0.5  # pagination is always worth showing
            return (-round(hit, 3), not e["search"], not e["inview"], e["id"])

        shown = sorted(els, key=score)[:max_elements]
        shown.sort(key=lambda e: e["id"])
        lines = []
        for e in shown:
            kind = e["tag"] if e["tag"] != "input" else f"input[{e['type'] or 'text'}]"
            href = re.sub(r"^https?://[^/]+", "", e["href"] or "") if e["tag"] == "a" else ""
            extra = f" -> {href[:45]}" if href and (len(e["text"]) < 25 or "/author/" in href) else ""
            lines.append(f"[{e['id']}] {kind} \"{e['text'][:60]}\"{extra}")
        return {"url": self.page.url, "title": self.page.title(), "text": focus_text(self.text(20000), goal),
                "elements": "\n".join(lines), "n_elements": len(els)}

    def act(self, action):
        a = action.get("action")
        if a == "goto":
            self.goto(action["url"])
        elif a in ("click", "type"):
            eid = int(action["id"])
            loc = self.page.locator(f'[data-aid="{eid}"]').first
            if a == "click":
                loc.click(timeout=10000)
                self.typed = []
                self.page.wait_for_timeout(300)
                if self._new_pages:  # the click opened a new tab: follow it, like a person would
                    self.page = self._new_pages.pop()
                    self._new_pages.clear()
                    self.page.set_default_timeout(20000)
            else:
                loc.fill(str(action.get("text", "")), timeout=10000)
                self.typed.append(self.elements.get(eid, {}))
                if action.get("enter"):
                    loc.press("Enter")
                    self.page.wait_for_timeout(1500)
            self._settle()
        elif a == "press":
            self.page.keyboard.press(action.get("key", "Enter"))
            self._settle()
        elif a == "scroll":
            self.page.mouse.wheel(0, 800 if action.get("direction", "down") == "down" else -800)
            self.page.wait_for_timeout(400)
        elif a == "back":
            self.page.go_back()
            self._settle()
        else:
            raise ValueError(f"unknown action {a}")
        return self.page.url

    def login(self, cred):
        """Fill the page's login form from the vault entry and submit it. Values are never returned."""
        pw = self.page.locator("input[type=password]").first
        user = self.page.locator("input[type=email], input[autocomplete=username], input[name*=user i], "
                                 "input[name*=login i], input[name*=email i], input[type=text]").first
        user.fill(cred["username"], timeout=10000)
        pw.fill(cred["password"], timeout=10000)
        pw.press("Enter")
        self.typed = []
        self._settle()
        return self.page.url

    def screenshot(self, path):
        self.page.screenshot(path=str(path), full_page=False)
