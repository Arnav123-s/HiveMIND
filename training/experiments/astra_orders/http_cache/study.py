"""Run on loopback with requests.Session. No credentials, model, or downloads required."""
import argparse
from collections import Counter
from gzip import compress, decompress
from http.server import HTTPServer
import json
from pathlib import Path
from threading import Thread

from ..web_pages import EXPECTED, Pages
from .cache import PublicPages


class Controls(Pages):
    def do_GET(self):
        self.server.visits[self.path] += 1
        if self.path == "/feed":
            return super().do_GET()
        path = self.path.split("?", 1)[0]
        data = str(self.server.visits[self.path]).encode()
        status = {"/redirect": 302, "/partial": 206, "/missing": 404}.get(path, 200)
        policies = {"/no-store": "public, max-age=40, no-store", "/private": "private, max-age=40",
                    "/no-cache": "no-cache", "/ambiguous": "public, max-age=30, max-age=80",
                    "/ttl": "public, max-age=7", "/no-offer": None}
        self.send_response(status)
        policy = policies.get(path, "public, max-age=40")
        if policy:
            self.send_header("Cache-Control", policy)
        if path == "/vary-star":
            self.send_header("Vary", "*")
        if path in ("/set-cookie", "/cookie/seed"):
            self.send_header("Set-Cookie", "mode=fixture; Path=/cookie")
        if path == "/vary-missing":
            self.send_header("Vary", "Accept-Language")
            data = repr(self.headers.get("Accept-Language")).encode()
        if path in ("/ttl", "/too-old"):
            self.send_header("Age", "4" if path == "/ttl" else "80")
        if path in ("/redirect", "/gzip"):
            self.send_header("Content-Encoding", "gzip")
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            data = compress("Crème brûlée".encode(), mtime=0)
        if path == "/redirect":
            self.send_header("Location", "/redirect-target")
        if path == "/content-range":
            self.send_header("Content-Range", "bytes 0-0/3")
        if path == "/fat":
            data = b"x" * 3072
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def end_headers(self):
        # Unmodified cursor fixture first, then explicitly fresh and public per server policy.
        if self.path == "/feed" and self.server.public_feed:
            self.send_header("Cache-Control", "public, max-age=40")
        super().end_headers()


def traversal(base, server, enabled, public):
    server.public_feed = public
    start = server.visits["/feed"]
    counts, origins, transferred = [], [], 0
    with PublicPages(enabled=enabled, public_headers=["X-Cursor"]) as reader:
        for _ in range(2):
            authors = Counter()
            for cursor in range(1, 6):
                before = reader.fetches
                page = reader.get(base + "/feed", headers={"X-Cursor": str(cursor)})
                if before != reader.fetches:
                    transferred += len(page.body)
                authors.update(json.loads(page.body)["authors"])
            assert authors == EXPECTED
            counts.append(dict(authors))
            origins.append(server.visits["/feed"] - start)
        assert reader.fetches == origins[-1]
        return {"network_by_traversal": [origins[0], origins[1] - origins[0]], "hits": reader.hits,
                "response_body_bytes_from_origin": transferred, "author_counts": counts}


def benchmark(base, server):
    result = {"cursor": {}}
    for name, flag, public in [("no_cache", False, True), ("no_freshness_offer", True, False),
                               ("explicit_public_freshness", True, True)]:
        result["cursor"][name] = traversal(base, server, flag, public)
    assert [v["network_by_traversal"] for v in result["cursor"].values()] == [[5, 5], [5, 5], [5, 0]]

    controls = {}
    for path in ("/no-store", "/no-cache", "/private", "/ambiguous", "/no-offer", "/vary-star",
                 "/set-cookie", "/too-old", "/content-range", "/partial", "/missing", "/lookup?key=fixture"):
        with PublicPages() as reader:
            before = server.visits[path]
            first, second = reader.get(base + path), reader.get(base + path)
            assert first.body != second.body and reader.hits == 0
            controls[path] = server.visits[path] - before
    for name in ("Authorization", "Proxy-Authorization", "Cookie", "Range", "If-None-Match", "X-Private"):
        with PublicPages() as reader:
            before = server.visits["/hello"]
            opts = {name: "fixture"}
            assert reader.get(base + "/hello", headers=opts).body != reader.get(base + "/hello", headers=opts).body
            controls["request " + name] = server.visits["/hello"] - before
    assert all(n == 2 for n in controls.values())
    result["two_read_bypasses_origin_calls"] = controls

    with PublicPages() as reader:
        reader.get(base + "/cookie/seed")
        assert reader.session.cookies.get("mode") == "fixture"
        assert reader.get(base + "/cookie/read").body != reader.get(base + "/cookie/read").body
        assert reader.hits == 0
    result["session_cookie_fetches_after_set"] = 2

    for directive in ({"Cache-Control": "no-cache"}, {"Cache-Control": "no-store"}, {"Pragma": "no-cache"}):
        with PublicPages() as reader:
            a = reader.get(base + "/renew").body
            assert reader.get(base + "/renew").body == a
            b = reader.get(base + "/renew", headers=directive).body
            c = reader.get(base + "/renew").body
            assert len({a, b, c}) == 3 and reader.get(base + "/renew").body == c
            assert reader.hits == 2 and reader.fetches == 3
    result["force_reread"] = {"directives_checked": 3, "network_per_five_requests": 3}

    with PublicPages() as reader:
        groups = [None, "", "fr", None, "", "fr"]
        pages = [reader.get(base + "/vary-missing", headers={"Accept-Language": value} if value is not None else {}).body
                 for value in groups]
        assert pages == [repr(s).encode() for s in groups] and reader.hits == 3
    result["absent_empty_and_french_selector_network_for_six"] = 3

    clock = [100.0]
    with PublicPages(clock=lambda: clock[0]) as reader:
        first = reader.get(base + "/ttl")
        clock[0] += 2
        replay = reader.get(base + "/ttl")
        assert replay.body == first.body and replay.headers["Age"] == "6"
        clock[0] += 1
        assert reader.get(base + "/ttl").body != first.body and reader.fetches == 2
    result["age_adjusted_expiry"] = {"initial_age": 4, "origin_max_age": 7, "hit_after_seconds": 2, "miss_after_seconds": 3}

    with PublicPages() as reader:
        before = server.visits["/redirect-target"]
        for name, code in (("/gzip", 200), ("/redirect", 302)):
            pages = [reader.get(base + name) for _ in range(2)]
            for p in pages:
                assert p.status == code and decompress(p.body).decode() == "Crème brûlée"
                assert int(p.headers["Content-Length"]) == len(p.body) and p.headers["Content-Encoding"] == "gzip"
                assert p.headers["Content-Type"] == "text/plain; charset=utf-8"
            assert pages[0].body == pages[1].body
        assert server.visits["/redirect-target"] == before and reader.fetches == 3
    result["encoded_representations"] = {"gzip_fetches": 1, "redirect_fetches": 2, "redirect_target_fetches": 0}

    with PublicPages(max_entries=2, max_bytes=1024) as reader:
        for path in ("/a", "/b", "/a", "/c", "/b", "/fat", "/fat"):
            reader.get(base + path)
            assert reader.size <= 1024 and len(reader.entries) <= 2
        assert reader.hits == 1 and reader.fetches == 6
    with PublicPages(max_body=256) as reader:
        try:
            reader.get(base + "/fat")
        except ValueError as exc:
            assert "body limit" in str(exc) and reader.size == 0
        else:
            raise AssertionError("oversize page escaped its read limit")
    result["bounded_store"] = {"entry_limit": 2, "byte_limit": 1024, "network_for_seven": 6, "read_limit_enforced": True}

    unique = []
    for _ in range(2):
        with PublicPages() as reader:
            unique.append(reader.get(base + "/isolate").body)
            assert reader.hits == 0 and reader.fetches == 1
        assert len(reader.entries) == 0 and reader.size == 0
    assert len(set(unique)) == 2
    result["separate_single_read_runs"] = {"network": 2, "hits": 0, "different_origin_values": True}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    with HTTPServer(("127.0.0.1", 0), Controls) as server:
        server.visits, server.public_feed = Counter(), False
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            result = benchmark(f"http://127.0.0.1:{server.server_port}", server)
        finally:
            server.shutdown()
            thread.join()
    encoded = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.out:
        args.out.write_text(encoded)
    else:
        print(encoded, end="")


if __name__ == "__main__":
    main()
