"""Live web access: search sources that allow automated queries, and page reading.

General web search engines (DuckDuckGo, Mojeek) answer this cloud network with
bot walls; the team does not try to get around them. It reports the wall and
uses sources that publish APIs for scripts instead.
"""
import json
import re
import threading
import time
import xml.etree.ElementTree as ET
from urllib.parse import quote_plus, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from .. import config

_S = requests.Session()
_S.headers["User-Agent"] = config.USER_AGENT
_cache = {}

# Resilience (added 2026-11-11 after battery failures b4/b6): the first version
# retried only HTTP 429, three times with 3s/6s sleeps, and let connection
# errors, timeouts and 5xx through on the first attempt. One dead host or one
# rate-limited API therefore sank whole end-to-end tasks. Now: retry transient
# failures (connection error, timeout, 429, 5xx) with exponential backoff,
# honor Retry-After, and pace calls to hosts that publish a politeness rule
# (arXiv asks for at most one request every 3 seconds).
_RETRY_STATUSES = {429, 500, 502, 503, 504}
_HOST_MIN_INTERVAL = {"export.arxiv.org": 3.1, "arxiv.org": 3.1}
_host_lock = threading.Lock()
_host_last = {}


class FetchError(Exception):
    pass


def _pace(url):
    host = urlparse(url).netloc
    interval = _HOST_MIN_INTERVAL.get(host)
    if not interval:
        return
    with _host_lock:
        wait = interval - (time.monotonic() - _host_last.get(host, 0.0))
        if wait > 0:
            time.sleep(wait)
        _host_last[host] = time.monotonic()


def _retry_after(r, attempt):
    try:
        return min(float(r.headers.get("Retry-After", "")), 30.0)
    except (TypeError, ValueError):
        return 2.0 * (2 ** attempt)


def get(url, params=None, as_json=False, attempts=4):
    key = (url, json.dumps(params, sort_keys=True))
    if key in _cache:
        return _cache[key]
    r = None
    for attempt in range(attempts):
        _pace(url)
        try:
            r = _S.get(url, params=params, timeout=config.HTTP_TIMEOUT)
        except requests.RequestException as e:
            if attempt == attempts - 1:
                raise FetchError(f"could not reach {url}: {e}") from e
            time.sleep(2.0 * (2 ** attempt))
            continue
        if r.status_code in _RETRY_STATUSES and attempt < attempts - 1:
            time.sleep(_retry_after(r, attempt))
            continue
        break
    if "charset" not in r.headers.get("content-type", "").lower():
        r.encoding = r.apparent_encoding or "utf-8"
    if r.status_code >= 400:
        raise FetchError(f"HTTP {r.status_code} from {r.url}: {r.text[:200]}")
    out = r.json() if as_json else r.text
    _cache[key] = out
    return out


def readable(html, base_url="", max_chars=12000):
    soup = BeautifulSoup(html, "lxml")
    for t in soup(["script", "style", "noscript", "svg", "nav", "footer", "header", "form", "aside"]):
        t.decompose()
    title = soup.title.get_text(strip=True) if soup.title else ""
    main = soup.find("main") or soup.find("article") or soup.body or soup
    text = re.sub(r"\n\s*\n+", "\n\n", main.get_text("\n", strip=True))
    links = []
    for a in main.find_all("a", href=True)[:200]:
        label = a.get_text(" ", strip=True)
        if label and not a["href"].startswith("#"):
            links.append((label[:80], urljoin(base_url, a["href"])))
    return {"title": title, "text": text[:max_chars], "links": links}


def read_url(url, max_chars=12000):
    """Fetch a page or API URL and return {'url','title','text','links'}."""
    body = get(url)
    if body.lstrip().startswith(("{", "[")):
        try:
            return {"url": url, "title": url, "text": json.dumps(json.loads(body), indent=1)[:max_chars], "links": []}
        except json.JSONDecodeError:
            pass
    page = readable(body, url, max_chars)
    page["url"] = url
    return page


# ---------------- search sources ----------------

HF_NOISE = set("""small tiny best top open permissive license licensed licence text generation text-generation
under below less than over models model chat llm llms language languages free cpu laptop parameters params
param popular good recent new latest instruction-tuned tuned ungated gated not with and for the a of on that run
runs local locally""".split())


def clean_hf_query(q):
    """Hugging Face search matches model *names*; descriptive words make it return junk."""
    words = [w for w in re.split(r"\s+", q.strip()) if w and w.lower() not in HF_NOISE
             and not re.fullmatch(r"(<|>|<=|>=)?\d+(\.\d+)?b?", w.lower())]
    return " ".join(words) or "Instruct"


def search_huggingface(q, limit=12, **filters):
    q = clean_hf_query(q)
    params = {"search": q, "sort": "downloads", "limit": limit,
              "expand[]": ["safetensors", "cardData", "gated", "pipeline_tag", "downloads", "likes", "tags"]}
    params.update(filters)
    rows = get("https://huggingface.co/api/models", params, as_json=True)
    out = []
    for m in rows:
        st = m.get("safetensors") or {}
        lic = (m.get("cardData") or {}).get("license") or next(
            (t.split(":", 1)[1] for t in m.get("tags", []) if t.startswith("license:")), "unknown")
        params_b = round(st["total"] / 1e9, 3) if st.get("total") else None
        out.append({
            "title": m["id"], "url": f"https://huggingface.co/{m['id']}",
            "snippet": f"{m['id']} | params {params_b}B | license {lic} | pipeline {m.get('pipeline_tag')} | "
                       f"gated {m.get('gated')} | downloads {m.get('downloads')} | likes {m.get('likes')}",
            "data": {"id": m["id"], "params_b": params_b, "license": lic, "pipeline": m.get("pipeline_tag"),
                     "gated": m.get("gated"), "downloads": m.get("downloads"), "likes": m.get("likes")},
            "source_url": "https://huggingface.co/api/models?search=" + quote_plus(q),
        })
    return out


def _human(n):
    for unit, size in (("GB", 1e9), ("MB", 1e6), ("kB", 1e3)):
        if n >= size:
            return f"{n / size:.2f} {unit}"
    return f"{n} B"


def search_hf_model(q, limit=40):
    """One model's facts from the Hugging Face API: license, gating, parameters, and every file with its size."""
    m = re.search(r"[\w.\-]+/[\w.\-]+", q)
    if not m:
        raise FetchError(f"hf_model needs an exact model id like Qwen/Qwen3-1.7B, got {q!r}")
    mid = m.group(0)
    url = f"https://huggingface.co/api/models/{mid}"
    d = get(url, {"blobs": "true", "expand[]": ["safetensors", "cardData", "gated", "pipeline_tag", "downloads",
                                                   "siblings", "likes", "tags"]}, as_json=True)
    lic = (d.get("cardData") or {}).get("license") or next(
        (t.split(":", 1)[1] for t in d.get("tags", []) if t.startswith("license:")), "unknown")
    st = d.get("safetensors") or {}
    params = f"{st['total'] / 1e9:.3f}B" if st.get("total") else "unknown"
    files = sorted(d.get("siblings") or [], key=lambda f: -(f.get("size") or 0))
    weights = sum(f.get("size") or 0 for f in files if f["rfilename"].endswith(".safetensors"))
    out = [{"title": mid, "url": f"https://huggingface.co/{mid}",
            "snippet": f"{mid} | params {params} | license {lic} | gated {d.get('gated')} | pipeline {d.get('pipeline_tag')} | "
                       f"downloads {d.get('downloads')}", "source_url": url}]
    if weights:
        out.append({"title": "weights total", "url": f"https://huggingface.co/{mid}/tree/main",
                    "snippet": f"{mid} safetensors weights total {_human(weights)} ({weights} bytes)", "source_url": url})
    for f in files[:limit]:
        if f.get("size") is not None:
            out.append({"title": f["rfilename"], "url": f"https://huggingface.co/{mid}/blob/main/{f['rfilename']}",
                        "snippet": f"file {f['rfilename']} size {_human(f['size'])} ({f['size']} bytes)", "source_url": url})
    return out


def search_hn(q, limit=8):
    d = get("https://hn.algolia.com/api/v1/search", {"query": q, "hitsPerPage": limit, "tags": "story"}, as_json=True)
    return [{"title": h.get("title") or "", "url": h.get("url") or f"https://news.ycombinator.com/item?id={h['objectID']}",
             "snippet": f"{h.get('points')} points, {h.get('num_comments')} comments, {h.get('created_at', '')[:10]}"}
            for h in d.get("hits", [])]


def _arxiv_fetch(search_query, limit):
    try:
        xml = get("https://export.arxiv.org/api/query", {"search_query": search_query, "max_results": limit,
                                                         "sortBy": "relevance"})
    except FetchError as e:
        # The API answers 400 for queries carrying characters its parser
        # rejects; retry once with punctuation stripped before giving up.
        if "HTTP 400" not in str(e):
            raise
        clean = " ".join(re.sub(r"[^\w\s\-]", " ", search_query).split())
        xml = get("https://export.arxiv.org/api/query", {"search_query": clean, "max_results": limit,
                                                         "sortBy": "relevance"})
    ns = {"a": "http://www.w3.org/2005/Atom"}
    root = ET.fromstring(xml)
    out = []
    for e in root.findall("a:entry", ns):
        out.append({"title": " ".join(e.findtext("a:title", "", ns).split()),
                    "url": e.findtext("a:id", "", ns),
                    "snippet": " ".join(e.findtext("a:summary", "", ns).split())[:300]})
    return out


def search_arxiv(q, limit=6):
    # Researchers usually pass a paper's title or near-title. The all: field's
    # relevance ranking buries the canonical paper under newer papers that
    # merely mention it (measured 2026-11-11: neither the DDPM nor the Codex
    # paper appears in the all: top 6 for its own title), so ask the title
    # field first and top up from all: only if the title search runs short.
    phrase = " ".join(q.split()).replace('"', "")
    out = _arxiv_fetch(f'ti:"{phrase}"', limit)
    if len(out) < limit:
        seen = {r["url"] for r in out}
        for r in _arxiv_fetch(f"all:{q}", limit):
            if r["url"] not in seen:
                out.append(r)
            if len(out) >= limit:
                break
    return out[:limit]


def search_pypi(q, limit=1):
    """PyPI's API needs an exact package name: try the query, then each word in it."""
    words = [w for w in re.split(r"[\s,]+", q.strip()) if w and w.lower() not in
             {"latest", "version", "versions", "package", "python", "release", "pypi", "the", "of", "newest", "current"}]
    d, last = None, None
    for cand in dict.fromkeys([q.strip().replace(" ", "-")] + words):
        try:
            d = get(f"https://pypi.org/pypi/{cand}/json", as_json=True)
            break
        except FetchError as e:
            last = e
    if d is None:
        raise last or FetchError(f"no PyPI package found for {q!r}")
    info = d["info"]
    return [{"title": info["name"], "url": f"https://pypi.org/project/{info['name']}/",
             "snippet": f"latest {info['version']} | {info.get('summary')} | requires-python {info.get('requires_python')}"}]


def search_wikipedia(q, limit=5):
    html = get("https://en.wikipedia.org/w/index.php", {"search": q, "fulltext": "1", "ns0": "1"})
    soup = BeautifulSoup(html, "lxml")
    out = []
    for li in soup.select("li.mw-search-result")[:limit]:
        a = li.select_one(".mw-search-result-heading a")
        if a:
            out.append({"title": a.get_text(strip=True), "url": urljoin("https://en.wikipedia.org", a["href"]),
                        "snippet": li.get_text(" ", strip=True)[:250]})
    return out


def search_web(q, limit=8):
    html = get("https://html.duckduckgo.com/html/", {"q": q})
    soup = BeautifulSoup(html, "lxml")
    res = soup.select("a.result__a")
    if not res:
        raise FetchError("DuckDuckGo returned a bot-check page instead of results (not bypassed)")
    return [{"title": a.get_text(strip=True), "url": a["href"], "snippet": ""} for a in res[:limit]]


SOURCES = {"huggingface": search_huggingface, "hf_model": search_hf_model, "hn": search_hn, "arxiv": search_arxiv,
           "pypi": search_pypi, "wikipedia": search_wikipedia, "web": search_web}


def search(source, q, **kw):
    fn = SOURCES.get(source)
    if fn is None:
        raise FetchError(f"unknown source {source}; use one of {list(SOURCES)}")
    return fn(q, **kw)
