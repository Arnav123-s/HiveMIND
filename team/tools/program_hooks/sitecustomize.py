import sys
try:
    import requests as _rq
    _orig = _rq.Session.request
    def _request(self, method, url, *a, **k):
        r = _orig(self, method, url, *a, **k)
        if r.status_code >= 400:
            sys.stderr.write("HIVE-HTTP: %s %s returned %d\n" % (method, r.url, r.status_code))
        return r
    _rq.Session.request = _request
except Exception:
    pass


def look(x, _depth=0, _most=14):
    '''The hive's eyes, built into every program a member writes: prints what is really there. JSON data: its
    keys, types and short values, nested. The text of a web page: its title, its links (text -> address) and its
    first lines of text. A requests response: whichever of the two it holds.'''
    pad = "  " * _depth
    if hasattr(x, "status_code") and hasattr(x, "text"):
        try:
            return look(x.json(), _depth, _most)
        except Exception:
            return look(x.text, _depth, _most)
    if isinstance(x, bytes):
        x = x.decode("utf-8", "replace")
    if isinstance(x, str) and "<" in x[:3000] and "</" in x:
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(x, "html.parser")
            print("PAGE title:", (soup.title.get_text(strip=True) if soup.title else "")[:100])
            seen, n = set(), 0
            for a in soup.find_all("a", href=True):
                key = (a.get_text(" ", strip=True)[:60], a["href"])
                if key in seen or not key[0]:
                    continue
                seen.add(key)
                n += 1
                if n <= 70:
                    print("  link %r -> %s" % key)
            if n > 70:
                print("  ... %d links in all" % n)
            for t in soup(["script", "style"]):
                t.decompose()
            lines = [ln.strip() for ln in soup.get_text("\n").splitlines() if ln.strip()]
            print("TEXT (%d lines; the first 30):" % len(lines))
            for ln in lines[:30]:
                print("  " + ln[:110])
            return
        except Exception as e:
            print("(not read as a page: %s)" % e)
    if isinstance(x, dict):
        if len(x) > 20:  # many keys of one kind (versions, dates, ids): two of them, and the last ones by name
            _most = 2
        for i, (k, v) in enumerate(x.items()):
            if i >= _most:
                print(pad + "... %d keys in all; the last ones: %s" % (len(x), ", ".join(repr(k) for k in list(x)[-3:])))
                break
            if isinstance(v, (dict, list)):
                print(pad + "%r: %s of %d" % (k, type(v).__name__, len(v)))
                if _depth < 3:
                    look(v, _depth + 1, 6)
            else:
                print(pad + "%r: %s" % (k, repr(v)[:90]))
    elif isinstance(x, (list, tuple)):
        print(pad + "[%d items; the first:]" % len(x))
        if x and _depth < 4:
            look(x[0], _depth + 1, 8)
    else:
        print(pad + repr(x)[:300])


try:
    import builtins as _b
    _b.look = look
except Exception:
    pass
