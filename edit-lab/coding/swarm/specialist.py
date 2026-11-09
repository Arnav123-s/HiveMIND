"""The specialist: the smallest unit of the swarm.

One specialist, one job. A specialist is either
  - constructed: a small deterministic function (zero model RAM), or
  - model:       bound through the interface layer to a local model, or
  - api:         bound through the interface layer to a frontier API, or
  - coordinator: a specialist whose one job is coordinating ONE niche.

Every run returns the same envelope:
    {"ok": bool, "output": ..., "evidence": ..., "specialist": name}
Nothing counts as done without evidence.
"""
import copy


class Specialist:
    kind = "constructed"

    def __init__(self, name, niche, job, fn=None, binding=None):
        self.name = name
        self.niche = niche
        self.job = job                # one line: the single thing it does
        self.fn = fn                  # constructed behaviour, if any
        self.binding = binding        # model_ref chain for model/api kinds
        self.weights = {}             # trainable state (constructed specialists)
        # Development status (Arnav's method): Muse trains/optimizes/repairs
        # each specialist, verifies it, and only then marks it
        # "running-alone". Anything else is "in-development".
        self.dev_status = "in-development"
        if binding:
            # kind names the PRIMARY (first) binding; later refs are escalation
            self.kind = "api" if binding[0].startswith("api:") else "model"

    def run(self, task):
        if self.fn is not None:
            out = self.fn(task)
            if isinstance(out, dict) and "ok" in out:
                out.setdefault("specialist", self.name)
                return out
            return {"ok": True, "output": out, "evidence": None, "specialist": self.name}
        return {"ok": False, "output": None, "specialist": self.name,
                "evidence": f"model-bound specialist '{self.name}' has no loaded backend yet",
                "gap": "backend-unloaded"}

    def clone(self, suffix):
        c = Specialist(f"{self.name}#{suffix}", self.niche, self.job,
                       fn=self.fn, binding=self.binding)
        c.kind = self.kind
        c.weights = copy.deepcopy(self.weights)
        return c

    def footprint_bytes(self):
        """Rough resident size of this one specialist (state, not shared code)."""
        import sys
        return sys.getsizeof(self.__dict__) + len(repr(self.weights).encode())

    def __repr__(self):
        return f"<{self.kind}:{self.niche}/{self.name}>"


class Registry:
    """Every specialist in the swarm, by name. Clones share a base name."""

    def __init__(self):
        self.by_name = {}

    def add(self, spec):
        self.by_name[spec.name] = spec
        return spec

    def get(self, name):
        return self.by_name.get(name)

    def in_niche(self, niche):
        return [s for s in self.by_name.values() if s.niche == niche]

    def all(self):
        return list(self.by_name.values())

    def count(self):
        return len(self.by_name)

    def update_weights(self, base_name, weights):
        """Socialize: push trained weights to every instance of a specialist."""
        n = 0
        for s in self.by_name.values():
            if s.name == base_name or s.name.startswith(base_name + "#"):
                s.weights = copy.deepcopy(weights)
                n += 1
        return n


class NicheCoordinator(Specialist):
    """A coordinator specialist for exactly one niche — never a generalist.

    Its whole job: take a job for its niche, split it among the niche's own
    smallest specialists via its route table, apply the niche gate, and
    return the assembled result. It knows nothing outside its niche.
    """

    def __init__(self, niche, routes, gate=None):
        super().__init__(f"{niche}-coordinator", niche,
                         f"coordinate the {niche} niche only", fn=None)
        self.kind = "coordinator"
        self.routes = routes          # stage name -> specialist name
        self.gate = gate              # fn(results dict) -> {"ok":..., "evidence":...}

    def run(self, task):
        return {"ok": False, "specialist": self.name, "gap": "coordinator-run-via-board",
                "evidence": "niche coordinators work through the board; "
                            "see niches.run_pipeline for the unattended loop"}
