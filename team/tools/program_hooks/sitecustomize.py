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
