"""The swarm as an API: OpenAI- and Anthropic-compatible, plus jobs you can submit and follow.

    python -m team api [--port 8766] [--host 127.0.0.1] [--until-done 2]

Any client that speaks the OpenAI or Anthropic API can give the swarm a task: set its base URL to this server and the
model to "hivemind". Examples (the official SDKs; nothing leaves your machine):

    from openai import OpenAI
    c = OpenAI(base_url="http://127.0.0.1:8766/v1", api_key="local", timeout=3600)
    r = c.chat.completions.create(model="hivemind", messages=[{"role": "user", "content": "What is 17.5% of 2,340?"}])
    print(r.choices[0].message.content)

    import anthropic
    c = anthropic.Anthropic(base_url="http://127.0.0.1:8766", api_key="local", timeout=3600)
    m = c.messages.create(model="hivemind", max_tokens=4096, messages=[{"role": "user", "content": "..."}])

A task takes minutes on a CPU: use stream=True (progress arrives while the swarm works and keeps the connection
alive) or the jobs API:
    POST /v1/jobs {"task": "...", "until_done": 2}      -> the job (id, status)
    GET  /v1/jobs | /v1/jobs/<id>                       -> status; report, files and what is still undone when finished
    GET  /v1/jobs/<id>/events                           -> live progress (server-sent events)
    POST /v1/stop                                       -> kill switch: the running job halts now

Unattended: risky actions happen only where the task orders them; the rest are listed in the report.
Only listens on 127.0.0.1 unless --host is given. Set AGENT_TEAM_API_KEY to require a key (Authorization: Bearer <key>
or x-api-key: <key>); keys are compared, never logged.
"""
import hmac
import json
import os
import re
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .sdk import FINISHED, Swarm

MODEL = "hivemind"
SWARM = None
DEFAULTS = {"until_done": 0}


def text_of(content):
    """Message content as text: a string, or a list of parts ({"type": "text", "text": ...})."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(p.get("text", "") for p in content if isinstance(p, dict) and p.get("type") in ("text", "input_text"))
    return ""


def task_from(messages):
    """The task is the latest user message. Earlier turns are context for the planner and writer, never orders.
    System prompts are the client's own instructions for a chat model, not Arnav's task: not used."""
    turns = [(m.get("role"), text_of(m.get("content"))) for m in messages or [] if m.get("role") in ("user", "assistant")]
    users = [i for i, (r, _) in enumerate(turns) if r == "user" and _.strip()]
    if not users:
        return "", ""
    last = users[-1]
    ctx = "\n".join(f"{'Arnav' if r == 'user' else 'The swarm'}: {t[:1500]}" for r, t in turns[:last][-8:] if t.strip())
    return turns[last][1].strip(), ctx


def history_from(messages):
    """The turns before the latest user message, as (role, text)."""
    turns = [(m.get("role"), text_of(m.get("content"))) for m in messages or [] if m.get("role") in ("user", "assistant")]
    users = [i for i, (r, t) in enumerate(turns) if r == "user" and t.strip()]
    return [(r, t) for r, t in turns[:users[-1]] if t.strip()] if users else []


def progress_line(ev):
    return f"[{time.strftime('%H:%M:%S', time.localtime(ev['ts']))}] {ev['agent']} {ev['kind']}: {ev['msg'][:200]}\n"


class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):  # requests are not logged: they can carry keys and private tasks
        pass

    # ---- plumbing --------------------------------------------------------------------------------------------
    def _json(self, code, obj):
        data = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _error(self, code, msg, kind="invalid_request_error"):
        self._json(code, {"error": {"message": msg, "type": kind}, "type": "error"})

    def _sse_start(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()
        self.close_connection = True

    def _sse(self, data, event=None):
        msg = (f"event: {event}\n" if event else "") + f"data: {data if isinstance(data, str) else json.dumps(data)}\n\n"
        self.wfile.write(msg.encode())
        self.wfile.flush()

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        try:
            return json.loads(self.rfile.read(n) or b"{}")
        except json.JSONDecodeError:
            return None

    def _authorised(self):
        key = os.environ.get("AGENT_TEAM_API_KEY")
        if not key:
            return True
        got = self.headers.get("x-api-key") or re.sub(r"^Bearer\s+", "", self.headers.get("Authorization") or "")
        return hmac.compare_digest(got.encode(), key.encode())

    def _follow(self, job, on_event, beat=10.0):
        """on_event(ev) for each new board event until the job finishes; on_event(None) after `beat` quiet seconds."""
        for ev in job.events(follow=True, poll=0.5, heartbeat=beat):
            on_event(ev)

    # ---- routes ----------------------------------------------------------------------------------------------
    def do_GET(self):
        if not self._authorised():
            return self._error(401, "missing or wrong API key", "authentication_error")
        path = self.path.split("?")[0].rstrip("/")
        if path in ("/v1/models", "/models"):
            return self._json(200, {"object": "list", "data": [{"id": MODEL, "object": "model", "created": 0,
                                                                "owned_by": "local", "display_name": "HiveMIND swarm"}]})
        if path == "/v1/jobs":
            return self._json(200, {"data": [j.to_dict(report=False) for j in SWARM.list()]})
        m = re.fullmatch(r"/v1/jobs/([\w-]+)(/events)?", path)
        if m:
            job = SWARM.get(m.group(1))
            if not job:
                return self._error(404, "no such job", "not_found_error")
            if not m.group(2):
                return self._json(200, job.to_dict())
            self._sse_start()
            for ev in job.events(follow=True, heartbeat=15):
                if ev is None:
                    self.wfile.write(b": keep-alive\n\n")
                    self.wfile.flush()
                else:
                    self._sse(ev)
            job.wait()
            return self._sse(job.to_dict(), event="done")
        if path == "/v1/projects":
            from . import project
            return self._json(200, {"data": [{"id": p.id, "goal": p.goal, "status": p.status, "progress": p.progress(),
                                              "milestones": p.milestones} for p in project.Project.all()]})
        if path == "/health":
            return self._json(200, {"ok": True, "model": MODEL})
        if path == "":  # the chat page (team/web.py), on the same queue as every API client
            from .web import PAGE
            data = PAGE.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            return self.wfile.write(data)
        if path == "/api/runs":
            return self._json(200, [page_view(j) for j in SWARM.list(8)])
        self._error(404, "not found", "not_found_error")

    def do_POST(self):
        if not self._authorised():
            return self._error(401, "missing or wrong API key", "authentication_error")
        path = self.path.split("?")[0].rstrip("/")
        body = self._body()
        if body is None:
            return self._error(400, "the body is not JSON")
        try:
            if path == "/api/task":  # the chat page
                job = SWARM.submit(str(body.get("task", "")), until_done=DEFAULTS["until_done"])
                return self._json(200, {"queued": job.id})
            if path in ("/v1/stop", "/api/stop"):
                SWARM.stop("api: POST /v1/stop")
                return self._json(200, {"stopping": True})
            if path == "/v1/projects":
                from . import project
                p = project.launch(str(body.get("goal", "")).strip() or "", SWARM)
                return self._json(202, {"id": p.id, "status": p.status, "milestones": p.milestones})
            if path == "/v1/jobs":
                job = SWARM.submit(str(body.get("task", "")), until_done=body.get("until_done", DEFAULTS["until_done"]),
                                   context=str(body.get("context", "")))
                return self._json(202, job.to_dict(report=False))
            if path in ("/v1/chat/completions", "/chat/completions"):
                return self._openai(body)
            if path == "/v1/messages":
                return self._anthropic(body)
            if path in ("/v1/responses", "/responses"):
                return self._responses(body)
        except ValueError as e:
            return self._error(400, str(e))
        self._error(404, "not found", "not_found_error")

    def _submit_chat(self, body):
        task, ctx = task_from(body.get("messages"))
        if not task:
            raise ValueError("no user message with text")
        rounds = body.get("until_done", DEFAULTS["until_done"])
        from . import converse
        if converse.on() and not body.get("job"):  # a conversation: talk is answered at once, work becomes a job
            hist = history_from(body.get("messages"))
            from . import project
            return converse.handle(task, hist, lambda t, c: SWARM.submit(t, until_done=rounds, context=c),
                                   start_project=lambda g: project.launch(g, SWARM))
        return SWARM.submit(task, until_done=rounds, context=ctx)

    def _openai(self, body):
        job = self._submit_chat(body)
        cid, created = f"chatcmpl-{job.id}", int(time.time())

        def chunk(delta, finish=None):
            return {"id": cid, "object": "chat.completion.chunk", "created": created, "model": MODEL,
                    "choices": [{"index": 0, "delta": delta, "finish_reason": finish}]}
        if not body.get("stream"):
            job.wait()
            return self._json(200, {"id": cid, "object": "chat.completion", "created": created, "model": MODEL,
                                    "choices": [{"index": 0, "message": {"role": "assistant", "content": job.report or job.error},
                                                 "finish_reason": "stop"}],
                                    "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                                    "hivemind": {"job": job.id, "unmet": job.unmet, "files": job.files}})
        self._sse_start()
        self._sse(chunk({"role": "assistant", "content": ""}))
        # progress goes in reasoning_content: clients that show "thinking" show it, others ignore it
        self._follow(job, lambda ev: self.wfile.write(b": keep-alive\n\n") or self.wfile.flush() if ev is None
                     else self._sse(chunk({"reasoning_content": progress_line(ev)})))
        job.wait()
        self._sse(chunk({"content": job.report or job.error}))
        self._sse(chunk({}, "stop"))
        self._sse("[DONE]")

    def _responses(self, body):
        """OpenAI Responses API (used by newer OpenAI clients and Codex): one message with the report as output_text."""
        job = self._submit_chat({"messages": responses_messages(body), "until_done": body.get("until_done", DEFAULTS["until_done"])})
        rid, mid, created = f"resp_{job.id}", f"msg_{job.id}", int(time.time())

        def response(status, text=None):
            out = [] if text is None else [{"type": "message", "id": mid, "status": "completed", "role": "assistant",
                                            "content": [{"type": "output_text", "text": text, "annotations": []}]}]
            return {"id": rid, "object": "response", "created_at": created, "status": status, "model": MODEL,
                    "output": out, "parallel_tool_calls": False, "tool_choice": "auto", "tools": [],
                    "usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0,
                              "input_tokens_details": {"cached_tokens": 0}, "output_tokens_details": {"reasoning_tokens": 0}}}
        if not body.get("stream"):
            job.wait()
            return self._json(200, response("completed", job.report or job.error))
        self._sse_start()
        seq = iter(range(10 ** 6))

        def ev(kind, **kw):
            self._sse({"type": kind, "sequence_number": next(seq), **kw}, kind)
        ev("response.created", response=response("in_progress"))
        self._follow(job, lambda e: self.wfile.write(b": keep-alive\n\n") or self.wfile.flush() if e is None else None)
        job.wait()
        text = job.report or job.error
        item = {"type": "message", "id": mid, "status": "in_progress", "role": "assistant", "content": []}
        part = {"type": "output_text", "text": "", "annotations": []}
        ev("response.output_item.added", output_index=0, item=item)
        ev("response.content_part.added", item_id=mid, output_index=0, content_index=0, part=part)
        ev("response.output_text.delta", item_id=mid, output_index=0, content_index=0, delta=text)
        ev("response.output_text.done", item_id=mid, output_index=0, content_index=0, text=text)
        ev("response.content_part.done", item_id=mid, output_index=0, content_index=0, part=part | {"text": text})
        ev("response.output_item.done", output_index=0, item=item | {"status": "completed", "content": [part | {"text": text}]})
        ev("response.completed", response=response("completed", text))

    def _anthropic(self, body):
        job = self._submit_chat(body)
        mid = f"msg_{job.id}"

        def message(content, stop_reason):
            return {"id": mid, "type": "message", "role": "assistant", "model": body.get("model", MODEL),
                    "content": content, "stop_reason": stop_reason, "stop_sequence": None,
                    "usage": {"input_tokens": 0, "output_tokens": 0}}
        if not body.get("stream"):
            job.wait()
            return self._json(200, message([{"type": "text", "text": job.report or job.error}], "end_turn"))
        self._sse_start()
        self._sse({"type": "message_start", "message": message([], None)}, "message_start")
        self._follow(job, lambda ev: self._sse({"type": "ping"}, "ping") if ev is None else None, beat=5.0)
        job.wait()
        self._sse({"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}},
                  "content_block_start")
        self._sse({"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": job.report or job.error}},
                  "content_block_delta")
        self._sse({"type": "content_block_stop", "index": 0}, "content_block_stop")
        self._sse({"type": "message_delta", "delta": {"stop_reason": "end_turn", "stop_sequence": None},
                   "usage": {"output_tokens": 0}}, "message_delta")
        self._sse({"type": "message_stop"}, "message_stop")


def page_view(job):
    ev = [progress_line(e).rstrip() for e in job.events()][-40:]
    status = job.status if job.status != "done" else ("done" if not job.unmet else f"done, {len(job.unmet)} left undone")
    return {"goal": job.task[:300], "dir": str(job.dir), "status": status, "events": ev,
            "report": job.report if job.status in FINISHED else ""}


def responses_messages(body):
    """OpenAI Responses input (a string, or a list of messages whose content is text or input_text parts) as chat messages."""
    inp = body.get("input")
    if isinstance(inp, str):
        return [{"role": "user", "content": inp}]
    return [{"role": m.get("role", "user"), "content": m.get("content", "")} for m in inp or []
            if isinstance(m, dict) and m.get("type", "message") == "message"]


def start(port=8766, host="127.0.0.1", until_done=0, swarm=None, block=True):
    """Serve the API on a swarm (the always-on service passes its own, so inbox, schedule and API share one queue)."""
    global SWARM
    SWARM = swarm or Swarm()
    DEFAULTS["until_done"] = until_done
    if host not in ("127.0.0.1", "localhost", "::1") and not os.environ.get("AGENT_TEAM_API_KEY"):
        print("warning: listening beyond this machine with no AGENT_TEAM_API_KEY set", flush=True)
    print(f"HiveMIND API: http://{host}:{port}/v1  (model '{MODEL}'; jobs at /v1/jobs)", flush=True)
    srv = ThreadingHTTPServer((host, port), H)
    srv.daemon_threads = True
    if not block:
        import threading
        threading.Thread(target=srv.serve_forever, daemon=True, name="hive-api").start()
        return srv
    srv.serve_forever()


def main(port=8766, host="127.0.0.1", until_done=0, root=None, workers=1):
    start(port, host, until_done, Swarm(root=root, workers=workers))

