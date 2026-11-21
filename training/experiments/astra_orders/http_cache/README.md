# Reusing fresh public pages during one run

A caller that reads the same explicitly cacheable representations more than once can save origin fetches. The reader uses a private in-memory store with a real Requests session. It lives under experiments and has no connection to the production fetching tools.

| Two traversals of five cursor pages at one URL | First traversal | Second traversal | Origin response-body bytes |
|---|---:|---:|---:|
| Cache disabled | 5 GETs | 5 GETs | 256 |
| Original server sends only `Vary: X-Cursor` | 5 GETs | 5 GETs | 256 |
| Server also sends `Cache-Control: public, max-age=40` | 5 GETs | 0 GETs | 128 |

Each traversal independently produced Ada 2, Lin 4, Ros 2 and Mei 1. An example that needs each page just once saves zero fetches. Two independent one-read runs fetched twice and saw different origin values. The [receipts](result.json) also cover eighteen restricted request or response cases, expiry, byte and entry limits, cookie state, and gzip and redirect behavior.

## Interface and scope

Create one `PublicPages` context for a single sequential run, declaring any custom public request selectors. For example, `PublicPages(public_headers=["X-Cursor"])` accepts the public pagination header in this study. A stored representation is keyed by the prepared URL and all eligible request headers. Missing and empty selector values are distinct.

The reader accepts a narrow freshness offer with `public` and a single positive `max-age`, returning a cached representation only while its origin age and the local TTL permit. Unknown or conditional directives, `Vary: *`, credentials, queries, ranges and non-200 responses bypass reuse. A request asking for a reread clears stored variants of its URL. Redirects remain visible to the caller. Encoded bodies retain their content encoding and length. The reader returns a small immutable representation object.

One run stores at most 32 entries and 1 MiB of representation and key data by default. Its maximum read size is 2 MiB and its local TTL cap is 60 seconds. The reader supports direct GET only, with no ambient proxy or netrc credentials. It raises on oversized reads. The benchmark measured origin requests and response-body bytes on loopback. Hosted task accuracy and end-to-end latency remain unmeasured.

Run from the repository root with `python -m training.experiments.astra_orders.http_cache.study`. The fixture extends the adjacent five-page HTTP study and requires no live site or model.
