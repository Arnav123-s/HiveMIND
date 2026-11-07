"""Show the coder real samples of the data a task names, before it writes code.

Writing a scraper or API client blind is where small coders fail: wrong CSS
classes, wrong JSON keys. A preview of the actual page/API/file fixes that.
"""
import json
import re
from collections import Counter
from pathlib import Path

from bs4 import BeautifulSoup

from . import web

URL_RX = re.compile(r"https?://[^\s)\"'<>]+")
FILE_RX = re.compile(r"\b([\w\-]+\.(?:csv|json|txt|tsv|md|xml|html))\b")


def _json_preview(obj, depth=0, max_items=2):
    if isinstance(obj, dict):
        return {k: _json_preview(v, depth + 1) for k, v in list(obj.items())[:25]}
    if isinstance(obj, list):
        return [_json_preview(v, depth + 1) for v in obj[:max_items]] + ([f"... {len(obj)} items total"] if len(obj) > max_items else [])
    if isinstance(obj, str) and len(obj) > 80:
        return obj[:80] + "..."
    return obj


def _html_preview(html, limit=1800):
    soup = BeautifulSoup(html, "lxml")
    for t in soup(["script", "style", "noscript", "svg", "head"]):
        t.decompose()
    counts = Counter()
    for el in soup.find_all(True):
        cls = " ".join(el.get("class") or [])
        if cls:
            counts[(el.name, cls)] += 1
    # the repeated item block: a class that appears 5-200 times and holds the most text
    best, best_text = None, 0
    for (tag, cls), n in counts.items():
        if 5 <= n <= 200:
            els = soup.find_all(tag, class_=cls.split()[0])
            text = sum(len(e.get_text(strip=True)) for e in els[:5])
            if text > best_text and len(str(els[0])) < 3000:
                best, best_text = (tag, cls, n), text
    out = []
    if best:
        tag, cls, n = best
        els = soup.find_all(tag, class_=cls.split()[0])
        out.append(f"Repeated item: <{tag} class=\"{cls}\"> x{n}. First two:")
        for e in els[:2]:
            out.append(re.sub(r"\s+", " ", str(e))[:800])
    title = soup.title.get_text(strip=True) if soup.title else ""
    body = re.sub(r"\s+", " ", soup.get_text(" ", strip=True))[:400]
    return (f"Title: {title}\n" + "\n".join(out) + f"\nText start: {body}")[:limit]


def preview(task, workdir=None, max_urls=2):
    parts = []
    for url in list(dict.fromkeys(u.rstrip(".,;") for u in URL_RX.findall(task)))[:max_urls]:
        try:
            body = web.get(url)
        except Exception as e:  # noqa: BLE001
            parts.append(f"--- {url}\n(could not fetch: {str(e)[:120]})")
            continue
        s = body.lstrip()
        if s.startswith(("{", "[")):
            try:
                parts.append(f"--- {url} (JSON)\n" + json.dumps(_json_preview(json.loads(s)), indent=1)[:1800])
                continue
            except json.JSONDecodeError:
                pass
        if s.startswith("<?xml") or "<feed" in s[:300]:
            parts.append(f"--- {url} (XML)\n{s[:1500]}")
        else:
            parts.append(f"--- {url} (HTML)\n{_html_preview(body)}")
    if workdir:
        for name in dict.fromkeys(FILE_RX.findall(task)):
            p = Path(workdir) / name
            if p.exists() and p.is_file():
                lines = p.read_text(errors="replace").splitlines()
                parts.append(f"--- local file {name} ({len(lines)} lines)\n" + "\n".join(lines[:8])[:1000])
    return "\n".join(parts)


def expected_outputs(task, before):
    """Files the task asks the program to create (not already present)."""
    want = []
    for m in re.finditer(r"(?:save|write|create|output|store|export)[^.]*?\b([\w\-]+\.(?:csv|json|txt|png|md|tsv|html|xml))\b",
                         task, re.I):
        if m.group(1) not in before:
            want.append(m.group(1))
    return list(dict.fromkeys(want))
