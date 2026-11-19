"""Use the two learned sender messages once per request, including nested worker calls."""
from contextlib import contextmanager
from contextvars import ContextVar
import os


# The six task domains share the body's four existing specialist families.
_SPECIALIST = {"coding": "code", "math": "code", "physical_science": "data",
               "conversation": "words", "machine_learning": "data", "computer_engineering": "code"}
_GUIDANCE = {
    "coding": "Preserve the requested language, identifiers, and return format.",
    "math": "Keep the units and precision the user requested.",
    "physical_science": "Distinguish observations from assumptions and keep physical units explicit.",
    "conversation": "Use the user's most recent correction or preference when it applies.",
    "machine_learning": "Keep training and evaluation data distinct when discussing model results.",
    "computer_engineering": "Keep bit, byte, clock, and time units explicit where they affect the answer.",
}
_UNSET = object()
_active = ContextVar("hive_domain_signals", default=_UNSET)
_advice = ContextVar("hive_domain_advice", default=_UNSET)


@contextmanager
def for_request(message, history=(), *, inherit=False):
    """A work seat can inherit a chat decision, including an explicit abstention."""
    existing = _active.get()
    if inherit and existing is not _UNSET:
        yield existing
        return
    decision = None
    if os.environ.get("HIVE_SIGNALS", "1").lower() not in {"0", "off", "false"}:
        from .domain_consensus import read_consensus
        from .signals import read_request
        decision = read_consensus(message, history, read_request(message, history))
    token = _active.set(decision)
    memory_token = _advice.set(_UNSET)
    try:
        yield decision
    finally:
        _advice.reset(memory_token)
        _active.reset(token)


def current_domain():
    decision = _active.get()
    return decision["domain"] if isinstance(decision, dict) else None


def specialist(original):
    """Use advice only for the body's otherwise unspecified default seat."""
    return original or _SPECIALIST.get(current_domain(), "code")


def guidance():
    return _GUIDANCE.get(current_domain(), "")


def prepare_advice(message, base, system, *, direct_labels=False):
    from . import domain_advice
    if _advice.get() is _UNSET:
        _advice.set(domain_advice.consult(message, base, current_domain(), system, direct_labels=direct_labels))
    return advice()


def advice():
    decision = _advice.get()
    return decision if isinstance(decision, dict) else None
