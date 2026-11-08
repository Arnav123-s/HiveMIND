"""Local web front end: a chat-style page to give the team tasks and watch it work.

    python -m team web            then open http://127.0.0.1:8765
Only listens on 127.0.0.1. One task runs at a time; the rest queue. Served by team/api.py (same queue as the API).
"""

PAGE = """<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>agent-team</title><style>
:root{--bg:#fafaf9;--fg:#1c1917;--mut:#78716c;--card:#fff;--line:#e7e5e4;--acc:#2563eb}
@media (prefers-color-scheme:dark){:root{--bg:#0c0a09;--fg:#e7e5e4;--mut:#a8a29e;--card:#1c1917;--line:#292524;--acc:#60a5fa}}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,sans-serif}
main{max-width:860px;margin:0 auto;padding:16px}
textarea{width:100%;box-sizing:border-box;min-height:90px;padding:10px;border:1px solid var(--line);border-radius:8px;background:var(--card);color:var(--fg);font:inherit}
button{margin-top:8px;padding:8px 16px;border:0;border-radius:8px;background:var(--acc);color:#fff;font:inherit;cursor:pointer}
.run{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px;margin:14px 0}
.ev{font:12px/1.4 ui-monospace,monospace;color:var(--mut);max-height:220px;overflow:auto;white-space:pre-wrap}
.rep{white-space:pre-wrap;margin-top:8px}.mut{color:var(--mut);font-size:13px}
</style></head><body><main><h2>agent-team</h2>
<p class="mut">One prompt. The team plans it, splits it up, checks every piece, and brings back the finished work.</p>
<textarea id="t" placeholder="What should the team do?"></textarea><br><button onclick="send()">Give to the team</button>
<button onclick="stopAll()" style="background:#dc2626;margin-left:8px">Stop</button>
<div id="runs"></div></main><script>
async function send(){const t=document.getElementById('t');if(!t.value.trim())return;
await fetch('/api/task',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({task:t.value})});t.value='';load()}
async function stopAll(){await fetch('/api/stop',{method:'POST'});load()}
function esc(s){return (s||'').replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]))}
async function load(){const r=await (await fetch('/api/runs')).json();
document.getElementById('runs').innerHTML=r.map(x=>`<div class="run"><b>${esc(x.goal)}</b><div class="mut">${x.status} · ${x.dir}</div>
<div class="ev">${esc(x.events.join('\\n'))}</div>${x.report?`<div class="rep">${esc(x.report)}</div>`:''}</div>`).join('')}
load();setInterval(load,4000);</script></body></html>"""


def main(port=8765):
    """The page is served by the API server, so the page and every API client share one queue (one task at a time)."""
    from .api import main as api
    print(f"agent-team web: http://127.0.0.1:{port}  (also the API: http://127.0.0.1:{port}/v1)", flush=True)
    api(port)
