import sys
import re as _re
try:
    import requests as _rq
    from urllib.parse import urljoin as _urljoin
    _orig = _rq.Session.request
    _base = [None]
    # An address without its site is joined to the page fetched last, and a bare site gets https:// (seen in the
    # pulse of g27: a member found the link '/author/bob-marley' and fetched it as it stood; requests refused it)
    _SITE = _re.compile(r"^[\w-]+(\.[\w-]+)*\.(?!html?\b|php\b|json\b|xml\b|aspx?\b|txt\b|csv\b|py\b)[a-z]{2,24}(:\d+)?(/|$)", _re.I)
    def _request(self, method, url, *a, **k):
        if isinstance(url, str) and not _re.match(r"^[a-z][a-z0-9+.-]*://", url.strip(), _re.I):
            u = url.strip()
            if u.startswith("//"):
                url = "https:" + u
            elif _SITE.match(u):
                url = "https://" + u
            elif _base[0] and u:
                url = _urljoin(_base[0], u)
        r = _orig(self, method, url, *a, **k)
        _base[0] = r.url
        if str(method).upper() == "GET":
            _times[r.url] = _times.get(r.url, 0) + 1
        if r.status_code >= 400:
            sys.stderr.write("HIVE-HTTP: %s %s returned %d\n" % (method, r.url, r.status_code))
        return r
    _rq.Session.request = _request
    # A loop meant to walk pages that fetched one page again and again (seen in the pulse of g27: "the first 5 pages",
    # range(1, 6), the same address each time; 8 authors counted where 28 were wanted, and nothing failed)
    _times = {}
    import atexit as _atexit
    def _same():
        u, n = max(_times.items(), key=lambda x: x[1], default=("", 0))
        if n >= 3:
            sys.stderr.write("HIVE-SAME: %s was fetched %d times\n" % (u, n))
    _atexit.register(_same)
except Exception:
    pass

# Data the TASK gave ("Here is a CSV file:" and its lines) is served under whatever name a program opens it by. Seen
# in the pulse of g27: given a CSV and a log in the message, every member of all three opened people.csv, input.csv,
# data.csv or log.txt, got FileNotFoundError on every turn, and no task of the kind was ever passed.
try:
    import os as _os, io as _io, builtins as _bi, json as _gjson
    _gpath = _os.environ.get("HIVE_GIVEN")
    _blocks = _gjson.load(_io.open(_gpath)) if _gpath and _os.path.isfile(_gpath) else []
    if _blocks:
        _bopen = _bi.open
        def _fits(text, ext):
            if ext == ".json":
                try:
                    _gjson.loads(text)
                    return True
                except Exception:
                    return False
            if ext in (".csv",):
                return text.count(",") >= text.count("\n")
            if ext == ".tsv":
                return "\t" in text
            return True
        def _hive_open(file, mode="r", *a, **k):
            try:
                return _bopen(file, mode, *a, **k)
            except FileNotFoundError:
                if isinstance(file, int) or any(c in str(mode) for c in "wax+"):
                    raise
                name = _os.fspath(file)
                if not isinstance(name, str) or _os.path.dirname(name) or name.startswith("."):
                    raise
                ext = _os.path.splitext(name)[1].lower()
                pick = next((b for b in _blocks if _fits(b["text"], ext)), _blocks[0])
                with _bopen(name, "w") as f:
                    f.write(pick["text"].rstrip("\n") + "\n")
                sys.stderr.write("HIVE-GIVEN: %s was not here; the data the TASK gave is saved under that name\n" % name)
                return _bopen(file, mode, *a, **k)
        _bi.open = _hive_open
        _io.open = _hive_open
except Exception:
    pass

# JSON data says what it holds when a key is not there: a member that guessed 'pypi_version' was told only
# KeyError: 'pypi_version', twice, and gave up; the keys that are there are what it needed to see
try:
    import json as _json

    # ... and where the key IS, when it is deeper (seen in the pulse of g27: asked when boto3 was released, a member
    # read ['info']['upload_time'], was told the keys of 'info', looked, read it again, six turns, no answer; it is
    # under ['urls'][0] and ['releases'][VERSION][0])
    def _where(x, k, path="", found=None, seen=None, many=False):
        found = [] if found is None else found
        seen = seen if seen is not None else [0]
        seen[0] += 1
        if len(found) >= 3 or seen[0] > 20000 or path.count("[") > 6:
            return found
        if isinstance(x, dict):
            if k in x and path:
                found.append((path + "[%r]" % (k,), x[k]))
            items = list(x.items())
            if len(items) > 30:  # many keys of one kind (versions, ids): searched only when nothing else has it
                items = items[-3:] if many else []
            for kk, v in items:
                if isinstance(v, (dict, list)):
                    _where(v, k, path + "[%r]" % (kk,), found, seen, many)
        elif isinstance(x, list):
            for i, v in enumerate(x[:3]):
                if isinstance(v, (dict, list)):
                    _where(v, k, path + "[%d]" % i, found, seen, many)
        if not path and not found and not many:
            return _where(x, k, path, found, seen, True)
        return found

    class _Keys(dict):
        def __missing__(self, k):
            ks = list(self)
            root = getattr(self, "_root", None)
            deeper = _where(self, k) or (_where(root, k) if root is not None and root is not self else [])
            raise KeyError("%r is not a key here%s; the keys here are: %s%s" % (
                k, "; it is in the data at: " + "; ".join("data%s = %s" % (p, repr(v)[:60]) for p, v in deeper) if deeper else "",
                ", ".join(repr(x) for x in ks[:25]), " ... (%d in all)" % len(ks) if len(ks) > 25 else ""))

    def _rooted(top):
        todo, n = [top], 0
        while todo and n < 200000:
            x = todo.pop()
            n += 1
            if isinstance(x, _Keys):
                x._root = top
                todo.extend(v for v in x.values() if isinstance(v, (dict, list)))
            elif isinstance(x, list):
                todo.extend(v for v in x if isinstance(v, (dict, list)))
        return top

    _loads = _json.loads
    def _hive_loads(s, *a, **k):
        if not a and "object_hook" not in k and "object_pairs_hook" not in k and k.get("cls") is None:
            k["object_hook"] = _Keys
            return _rooted(_loads(s, *a, **k))
        return _loads(s, *a, **k)
    _json.loads = _hive_loads
    try:
        import requests as _rq2
        _rjson = _rq2.Response.json
        def _response_json(self, *a, **k):
            try:
                return _rjson(self, *a, **k)
            except ValueError as e:
                head = (self.text or "")[:160].replace("\n", " ")
                e.args = ("the reply from %s is not JSON (%s); it begins: %r. look(r) shows what it is"
                          % (self.url, e, head),)
                raise
        _rq2.Response.json = _response_json
        if getattr(_rq2.compat, "json", _json) is not _json:
            _rq2.compat.json.loads = _hive_loads
    except Exception:
        pass
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
