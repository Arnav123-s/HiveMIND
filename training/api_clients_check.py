"""The official OpenAI and Anthropic Python SDKs against the swarm API, with a stand-in hive (no models, seconds).

    pip install openai anthropic        (only for this check; the swarm itself does not need them)
    python training/api_clients_check.py
"""
import sys, tempfile, threading
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
from http.server import ThreadingHTTPServer
from team import api, hive, sdk
from test_interface import FakeHive
hive.Hive = FakeHive
api.SWARM = sdk.Swarm(root=Path(tempfile.mkdtemp()) / "runs")
srv = ThreadingHTTPServer(("127.0.0.1", 0), api.H); srv.daemon_threads = True
threading.Thread(target=srv.serve_forever, daemon=True).start()
port = srv.server_address[1]
import openai, anthropic
oc = openai.OpenAI(base_url=f"http://127.0.0.1:{port}/v1", api_key="local", timeout=60)
print("openai models:", [m.id for m in oc.models.list()])
r = oc.chat.completions.create(model="hivemind", messages=[{"role": "user", "content": "Find it."}])
print("openai:", repr(r.choices[0].message.content[:20]), r.choices[0].finish_reason)
parts, thinking = [], []
for ch in oc.chat.completions.create(model="hivemind", stream=True, messages=[{"role": "user", "content": "Find it."}]):
    d = ch.choices[0].delta
    parts.append(d.content or ""); thinking.append(getattr(d, "reasoning_content", None) or (d.model_extra or {}).get("reasoning_content") or "")
print("openai stream:", repr("".join(parts)[:20]), "progress lines:", sum(1 for t in thinking if t))
ac = anthropic.Anthropic(base_url=f"http://127.0.0.1:{port}", api_key="local", timeout=60)
m = ac.messages.create(model="hivemind", max_tokens=100, messages=[{"role": "user", "content": "Find it."}])
print("anthropic:", repr(m.content[0].text[:20]), m.stop_reason)
with ac.messages.stream(model="hivemind", max_tokens=100, messages=[{"role": "user", "content": "Find it."}]) as st:
    text = "".join(st.text_stream)
    final = st.get_final_message()
print("anthropic stream:", repr(text[:20]), final.stop_reason)
r = oc.responses.create(model="hivemind", input="Find it.")
print("openai responses:", repr(r.output_text[:20]), r.status)
with oc.responses.stream(model="hivemind", input=[{"role": "user", "content": [{"type": "input_text", "text": "Find it."}]}]) as st:
    for _ in st:
        pass
    fin = st.get_final_response()
print("openai responses stream:", repr(fin.output_text[:20]), fin.status)
srv.shutdown()
