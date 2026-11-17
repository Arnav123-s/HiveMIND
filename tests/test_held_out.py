"""Lessons kept back: 2 of every kind's lessons are never trained on, and their loss is measured where a cell starts
and where it ends, in every slice's record (training/grow.kept_back, kept_loss and train)."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

from training import grow

ROOT = Path(__file__).resolve().parents[1]


def _lesson(kind, i, who="lesson"):
    task = f"Do the {kind} task number {i}."
    head = [{"role": "system", "content": "Today is 2026-11-16 (Monday)."}, {"role": "user", "content": f"TASK: {task}"}]
    base = {"task": task, "kind": kind, "seed": f"lesson:1:{kind}:{i}", "who": who, "member": 0, "lesson": f"m_{kind}"}
    return [base | {"type": "first", "messages": head, "output": f"```python\nprint({i} * {len(kind)})\n```"},
            base | {"type": "done", "messages": head + [{"role": "assistant", "content": "x"}, {"role": "user", "content": "OUTPUT: 1"}], "output": "DONE"}]


def _rows():
    rows = [r for k, n in (("alpha", 6), ("beta", 4), ("gamma", 2)) for i in range(n) for r in _lesson(k, i)]
    return rows + [r for i in range(8) for r in _lesson("own", i, who="member")]  # the hive's own work: never kept back


def test_two_lessons_of_every_kind_are_kept_back_the_same_whatever_the_order():
    rows = _rows()
    back = grow.kept_back(rows)
    assert sorted(back) == ["alpha", "beta", "gamma"]  # lessons only, every kind of them
    assert all(len(ts) == 2 for ts in back.values())
    assert grow.kept_back(list(reversed(rows))) == back
    assert grow.kept_back(rows, 0) == {}
    # rows only grow from one generation to the next: a lesson kept back now was kept back before
    more = rows + [r for i in range(6, 20) for r in _lesson("alpha", i)]
    assert set(grow.kept_back(more)["alpha"]) <= set(back["alpha"]) | {f"Do the alpha task number {i}." for i in range(6, 20)}


def _tiny(tmp_path):
    """A model of two small layers and a tokenizer of bytes, saved the way a published DNA is."""
    import torch
    from tokenizers import Tokenizer, decoders, models, pre_tokenizers
    from transformers import PreTrainedTokenizerFast, Qwen3Config, Qwen3ForCausalLM
    alphabet = pre_tokenizers.ByteLevel.alphabet()
    vocab = {c: i for i, c in enumerate(sorted(alphabet))}
    t = Tokenizer(models.BPE(vocab=vocab, merges=[]))
    t.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False)
    t.decoder = decoders.ByteLevel()
    tok = PreTrainedTokenizerFast(tokenizer_object=t, eos_token="<|im_end|>", pad_token="<|im_end|>")
    tok.add_special_tokens({"additional_special_tokens": ["<|im_start|>"]})
    tok.chat_template = ("{% for m in messages %}<|im_start|>{{ m['role'] }}\n{{ m['content'] }}<|im_end|>\n{% endfor %}"
                         "{% if add_generation_prompt %}<|im_start|>assistant\n{% endif %}")
    tok.save_pretrained(tmp_path)
    torch.manual_seed(0)
    cfg = Qwen3Config(vocab_size=len(tok), hidden_size=32, intermediate_size=64, num_hidden_layers=2, num_attention_heads=2,
                      num_key_value_heads=1, head_dim=16, max_position_embeddings=2048, tie_word_embeddings=False)
    Qwen3ForCausalLM(cfg).save_pretrained(tmp_path)
    return tok


def _train(tmp_path, monkeypatch, rows, shard):
    """train() on the tiny model; every forward pass seen, as text and whether it was trained on (a gradient)."""
    import huggingface_hub
    import torch
    from transformers import Qwen3ForCausalLM

    from team import ternary
    dna = tmp_path / "dna"
    if not dna.exists():
        dna.mkdir()
        _tiny(dna)
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(dna)
    seen = []
    forward = Qwen3ForCausalLM.forward

    def spy(self, input_ids=None, **k):
        seen.append((tok.decode(input_ids[0]), torch.is_grad_enabled()))
        return forward(self, input_ids=input_ids, **k)
    monkeypatch.setattr(Qwen3ForCausalLM, "forward", spy)
    monkeypatch.setattr(huggingface_hub, "snapshot_download", lambda name: str(dna))
    monkeypatch.setenv("AGENT_TEAM_THREADS", "1")  # a model this small is slower on more threads
    monkeypatch.setattr(grow, "GROW", tmp_path / "grow")
    monkeypatch.setattr(ternary, "source", lambda: tmp_path)
    run = subprocess.run

    def convert(args, **k):  # the edit as the runtime reads it: not needed here
        if "--outfile" not in args:
            return run(args, **k)
        Path(args[args.index("--outfile") + 1]).write_bytes(b"gguf")
        return subprocess.CompletedProcess(args, 0, "", "")
    monkeypatch.setattr(grow.subprocess, "run", convert)
    f = tmp_path / "rows.jsonl"
    f.write_text("".join(json.dumps(r) + "\n" for r in rows))
    meta = grow.train(str(f), "kb", base="t17", epochs=2.0, rank=4, accum=2, log=lambda *a, **k: None, out_dir=tmp_path / "out", shard=shard, dtype="f32")
    monkeypatch.setattr(Qwen3ForCausalLM, "forward", forward)
    return meta, seen


def test_every_slice_measures_the_same_kept_back_lessons_before_and_after_and_never_trains_on_them(tmp_path, monkeypatch):
    pytest.importorskip("peft")
    rows = _rows()
    back = grow.kept_back(rows)
    tasks = {t for ts in back.values() for t in ts}
    measured = []
    for shard in ("0/2", "1/2"):
        meta, seen = _train(tmp_path, monkeypatch, rows, shard)
        trained = [s for s, g in seen if g]
        assert trained and not any(t in s for s in trained for t in tasks)  # no row of a kept-back task is trained on
        looked = [s for s, g in seen if not g]
        # one measure where the cell starts and one where it ends: the "first" rows of the kept-back lessons, each once
        assert len(looked) == 2 * len(tasks) and all(sum(t in s for s in looked) == 2 for t in tasks)
        assert looked[:len(tasks)] == looked[len(tasks):]
        measured.append(sorted(looked))
        kb = meta["kept_back"]
        assert sorted(kb) == ["alpha", "beta", "gamma"]
        for k, v in kb.items():
            assert v["lessons"] == 2 and v["rows"] == 2 and v["before"] > 0 and v["after"] > 0
        assert json.loads((tmp_path / "out" / "t17+kb.json").read_text())["kept_back"] == kb  # in the record the slice writes
    assert measured[0] == measured[1]  # the same lessons in every slice


def test_the_reader_prints_the_kept_back_lessons_by_kind_before_and_after():
    sys.path.insert(0, str(ROOT / "scripts"))
    import read_generation as rg
    recs = [{"job": "train (code, 0)", "record": {"member": "t80+g40code", "shard": "0/3", "kept_back": {
                "h_join": {"lessons": 2, "rows": 2, "before": 0.9, "after": 0.3}, "h_log": {"lessons": 2, "rows": 2, "before": 1.2, "after": 1.1}}}},
            {"job": "train (code, 1)", "record": {"member": "t80+g40code", "shard": "1/3", "kept_back": {
                "h_join": {"lessons": 2, "rows": 2, "before": 0.9, "after": 0.5}}}},
            {"job": "train (code, 2)", "record": None}]
    out = "\n".join(rg.kept_back(recs))
    assert "| h_join | 2 | 2 | 0.900 -> 0.400 | -0.500 |" in out
    assert "t80+g40code 0/3: 0.900 -> 0.300; t80+g40code 1/3: 0.900 -> 0.500" in out
    assert "| h_log | 1 | 2 | 1.200 -> 1.100 | -0.100 |" in out
    assert rg.kept_back([{"job": "x", "record": {"member": "m"}}]) == ["no slice's record has lessons kept back"]
