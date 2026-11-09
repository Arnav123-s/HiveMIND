"""Meta layer: the growth specialists.

An unknown problem triggers growth, never refusal:
    gap -> LEARNER records it -> HARVESTER finds/makes examples ->
    TRAINER fits a new smallest specialist (or new weights) ->
    verify on held-out examples -> SPAWNER clones for coverage ->
    weights socialize to every instance. Surgery on existing weights is
    a different niche with its own protocol (surgeon.py).
"""
import copy
import random
import re

from .specialist import Specialist


# ------------------------------------------------------------- a trainable
class KeywordClassifier(Specialist):
    """The smallest trainable specialist: keyword votes -> one class.

    weights = {"keywords": {keyword: {class: score}}}. Deliberately tiny:
    it is the standing example of a specialist the TRAINER can fit, the
    SURGEON can map and edit, and the SPAWNER can clone.
    """

    def __init__(self, name, niche, job="classify text into one class by keyword votes"):
        super().__init__(name, niche, job)
        self.weights = {"keywords": {}}

    def run(self, task):
        text = task["text"] if isinstance(task, dict) else str(task)
        scores = {}
        for kw, votes in self.weights["keywords"].items():
            if kw in text.lower():
                for cls, s in votes.items():
                    scores[cls] = scores.get(cls, 0) + s
        if not scores:
            return {"ok": False, "output": "unknown", "specialist": self.name,
                    "evidence": "no keyword matched", "gap": "no-keyword-votes"}
        best = max(scores, key=scores.get)
        return {"ok": True, "output": best, "specialist": self.name,
                "evidence": f"vote scores {scores}"}

    def clone(self, suffix):
        c = KeywordClassifier(f"{self.name}#{suffix}", self.niche, self.job)
        c.weights = copy.deepcopy(self.weights)
        c.dev_status = self.dev_status
        return c


# ------------------------------------------------------------- HARVESTER
ERROR_TEMPLATES = {
    "SyntaxError": ["SyntaxError: invalid syntax", "SyntaxError: '(' was never closed",
                    "SyntaxError: unexpected indent"],
    "NameError": ["NameError: name 'usr' is not defined", "NameError: name 'resutl' is not defined",
                  "NameError: name 'df' is not defined"],
    "TypeError": ["TypeError: can only concatenate str (not \"int\") to str",
                  "TypeError: 'NoneType' object is not subscriptable",
                  "TypeError: unsupported operand type(s) for +: 'int' and 'str'"],
    "ValueError": ["ValueError: invalid literal for int() with base 10: 'abc'",
                   "ValueError: too many values to unpack (expected 2)",
                   "ValueError: invalid literal for int() with base 10: 'x9'"],
    "IndexError": ["IndexError: list index out of range", "IndexError: string index out of range",
                   "IndexError: tuple index out of range"],
    "KeyError": ["KeyError: 'user_id'", "KeyError: 'config'", "KeyError: 'total'"],
    "ZeroDivisionError": ["ZeroDivisionError: division by zero",
                          "ZeroDivisionError: float division by zero",
                          "ZeroDivisionError: integer division or modulo by zero"],
    "FileNotFoundError": ["FileNotFoundError: [Errno 2] No such file or directory: 'data.csv'",
                          "FileNotFoundError: [Errno 2] No such file or directory: 'in.txt'",
                          "FileNotFoundError: [Errno 2] No such file or directory: 'x.json'"],
}


def harvest_error_examples(task):
    """HARVESTER: synthesize labelled examples for an error-class gap."""
    classes = task.get("classes") or list(ERROR_TEMPLATES)
    out = []
    for cls in classes:
        for text in ERROR_TEMPLATES.get(cls, []):
            out.append({"text": text, "label": cls})
    return {"ok": True, "output": out,
            "evidence": f"{len(out)} harvested examples over {len(classes)} classes"}


# ------------------------------------------------------------- TRAINER
def _tokens(text):
    return [t for t in re.findall(r"[a-z_']+", text.lower()) if len(t) >= 3]


def train_keyword_classifier(task):
    """TRAINER: fit keyword votes from examples; verify on a held-out split.

    Returns new weights plus the held-out accuracy — a candidate is only
    adopted if the held-out score beats the incumbent (the swarm's win
    rule, applied at the smallest scale).
    """
    examples = task["examples"]
    rng = random.Random(7)
    idx = list(range(len(examples)))
    rng.shuffle(idx)
    cut = max(1, int(len(idx) * 0.8))
    train = [examples[i] for i in idx[:cut]]
    held = [examples[i] for i in idx[cut:]] or train[:1]
    counts = {}
    for ex in train:
        for tok in set(_tokens(ex["text"])):
            counts.setdefault(tok, {}).setdefault(ex["label"], 0)
            counts[tok][ex["label"]] += 1
    # keep only keywords that vote mostly for one class (signal, not noise)
    keywords = {k: v for k, v in counts.items() if max(v.values()) >= 2 or len(train) < 12}
    probe = KeywordClassifier("_trainer_probe", "meta")
    probe.weights = {"keywords": keywords}
    right = sum(1 for ex in held if probe.run(ex)["output"] == ex["label"])
    acc = right / len(held)
    return {"ok": True,
            "output": {"weights": {"keywords": keywords}, "heldout_acc": acc,
                       "train_n": len(train), "heldout_n": len(held)},
            "evidence": f"held-out accuracy {acc:.2f} on {len(held)} examples"}


# ------------------------------------------------------------- SPAWNER
def spawn_from_spec(registry, board=None):
    def _spawn(task):
        spec = task["spec"]
        s = Specialist(spec["name"], spec["niche"], spec["job"],
                       fn=task.get("fn"), binding=spec.get("binding"))
        if spec.get("kind"):
            s.kind = spec["kind"]
        registry.add(s)
        if board:
            board.event("spawner", "spawn", s.name)
        return {"ok": True, "output": s.name, "evidence": f"spawned {s}"}
    return _spawn


def clone_for_coverage(registry, board=None):
    def _clone(task):
        base = registry.get(task["name"])
        if base is None:
            return {"ok": False, "output": None, "evidence": f"no specialist {task['name']}"}
        made = []
        for i in range(task.get("n", 1)):
            c = base.clone(f"c{i}")
            registry.add(c)
            made.append(c.name)
        if board:
            board.event("spawner", "clone", f"{task['name']} x{len(made)}")
        return {"ok": True, "output": made, "evidence": f"{len(made)} clone(s) of {task['name']}"}
    return _clone


# ------------------------------------------------------------- LEARNER
def learn_from_failure(board):
    def _learn(task):
        board.log_lesson(task.get("niche", "meta"),
                         f"failure: {task.get('what')} (gap: {task.get('gap', 'unknown')})",
                         source="learner")
        board.event("learner", "lesson", task.get("what", ""))
        return {"ok": True, "output": task.get("gap"),
                "evidence": "failure recorded as a lesson on the board"}
    return _learn


def recommend_growth(board):
    """LEARNER's other half: read the failure lessons, name the growth move."""
    gaps = {}
    for les in board.lessons():
        if "gap:" in les["text"]:
            g = les["text"].split("gap:")[1].strip().rstrip(")")
            gaps[g] = gaps.get(g, 0) + 1
    moves = []
    for gap, n in gaps.items():
        if gap in ("unknown-error-class", "no-keyword-votes"):
            moves.append({"gap": gap, "move": "harvest+train", "times": n})
        elif gap in ("unknown-bug", "semantic-check"):
            moves.append({"gap": gap, "move": "spawn+harvest", "times": n})
        elif gap == "backend-unloaded":
            moves.append({"gap": gap, "move": "wait-for-backend (queued, no human stop)", "times": n})
        elif gap == "surgery-prerequisite":
            moves.append({"gap": gap, "move": "map-first-then-edit (protocol steps 1-4, then re-apply)", "times": n})
        elif gap in ("no-features", "no-class-models"):
            moves.append({"gap": gap, "move": "harvest+train", "times": n})
        else:
            moves.append({"gap": gap, "move": "harvest", "times": n})
    return {"ok": True, "output": moves, "evidence": f"{len(gaps)} distinct gap(s) seen"}
