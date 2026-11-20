"""A small local front door for checked calendar, arithmetic and depot quotes."""
from contextlib import contextmanager, nullcontext
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
import argparse
import json
import os

from team import config, saved
from training.experiments.atlas.pulse.one_checked import current as certificate
from training.experiments.atlas.service.wording import canonical_question

SAMPLE_BANK = config.ROOT / "training/reports/retained-skills/shipping/bank"
UNSUPPORTED = "I could not match the whole question to a supported calculation."


def withheld(message=UNSUPPORTED, *, route=None, status="unsupported"):
    return dict(status=status, route=route, value=None, unit=None, text=message)


def calculation(question):
    output = certificate.expected(question)
    if output is None:
        return None
    kind, value = output
    if kind == "weekday":
        unit, text = None, value.capitalize()
    elif kind == "days":
        unit, text = "days", f"{value} {'day' if value == 1 else 'days'}"
    elif kind == "gcd":
        unit, text = None, str(value)
    elif kind == "dollars":
        unit, text = "dollars", f"{value:.2f} dollars"
    else:
        unit, text = kind, f"{value:.1f} °{'C' if kind == 'celsius' else 'F'}"
    if not certificate.certify(question, text):
        return withheld("The computed result could not be certified in the requested format.", route=kind)
    return dict(status="answered", route=kind, value=str(value) if isinstance(value, Decimal) else value,
                unit=unit, text=text, proof="whole-question arithmetic certificate")


def shipping_request(question):
    from training.experiments.atlas.traces.trace import bind
    if bind(question):
        return True
    convention = saved._CONVENTION.search(question)
    text = question[:convention.start()] if convention and (saved.SHIPPING, convention[1].lower()) in saved._CONVENTIONS else question
    return saved._natural(text, saved.SHIPPING) is not None


@contextmanager
def one_cpu():
    """Initialize and execute WASI within one CPU. Restore the caller's Linux affinity afterward."""
    mask = os.sched_getaffinity(0) if hasattr(os, "sched_getaffinity") else None
    rayon = os.environ.get("RAYON_NUM_THREADS")
    os.environ["RAYON_NUM_THREADS"] = "1"
    try:
        if mask is not None:
            os.sched_setaffinity(0, {min(mask)})
        yield
    finally:
        if mask is not None:
            os.sched_setaffinity(0, mask)
        if rayon is None:
            os.environ.pop("RAYON_NUM_THREADS", None)
        else:
            os.environ["RAYON_NUM_THREADS"] = rayon


def answer(question, *, bank=None, sdk=None, trace_bank=None, guest=None):
    if not isinstance(question, str) or not question.strip() or len(question) > 2048:
        return withheld()
    exact = calculation(question)
    if exact is not None:
        return exact
    canonical = canonical_question(question)
    if canonical is not None:
        result = calculation(canonical)
        if result is not None:
            result["canonical_question"] = canonical
            result["proof"] = "matched calendar wording and checked the normalized question"
            return result
    if not shipping_request(question):
        return withheld()
    bank = str(bank if bank is not None else os.environ.get("HIVE_BANK", SAMPLE_BANK)).strip()
    if not bank or bank.lower() == "off":
        return withheld("Saved depot quotes are disabled.", route="shipping", status="unavailable")
    bank = Path(bank).expanduser()
    sdk = Path(sdk) if sdk is not None else config.fieldwork_sdk_path()
    if not bank.is_dir():
        return withheld("The depot bank directory is unavailable.", route="shipping", status="unavailable")
    if trace_bank and bank.resolve() == Path(trace_bank).resolve():
        return withheld("Choose a separate directory for the guarded trace.", route="shipping", status="unavailable")
    try:
        with one_cpu(), (nullcontext(trace_bank) if trace_bank else TemporaryDirectory()) as shelf:
            import wasmtime
            from training.experiments.atlas.traces.trace import GuardedTrace
            from training.experiments.fieldwork.guest import Guest
            runner = guest if guest is not None else Guest(sdk)
            trace = GuardedTrace(bank=bank, sibling_bank=shelf, guest=runner)
            try:
                receipt = trace.answer(question)
            except wasmtime.WasmtimeError:
                return withheld("The CPython WASI runtime could not load the shipping method.", route="shipping", status="unavailable")
    except (ImportError, OSError, ValueError) as exc:
        return withheld(f"Depot quotes are unavailable ({type(exc).__name__}). Check the bank and WASI SDK paths.",
                        route="shipping", status="unavailable")
    if not receipt:
        return withheld("The bank has no checked depot quote for this question.", route="shipping")
    if receipt["status"] != "answered":
        return withheld(receipt["text"], route="shipping", status=receipt["status"])
    value = receipt["value"]
    if type(value) is not int or value < 0:
        return withheld("The saved method did not return a nonnegative fee in cents.", route="shipping")
    return dict(status="answered", route="shipping", value=value, unit="cents", text=f"{value} cents",
                proof={"path": trace.last["path"], "methods": receipt["methods"], "fuel": trace.last["fuel"]})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question", help="a complete question, in quotes")
    parser.add_argument("--bank", help="read-only checked depot bank (default: bundled example, or HIVE_BANK)")
    parser.add_argument("--sdk", type=Path, help="CPython WASI SDK, needed only for depot fees")
    parser.add_argument("--trace-bank", type=Path, help="separate optional directory for previously qualified branches")
    parser.add_argument("--json", action="store_true", help="include route, typed value, unit and proof")
    args = parser.parse_args()
    result = answer(args.question, bank=args.bank, sdk=args.sdk, trace_bank=args.trace_bank)
    print(json.dumps(result, ensure_ascii=False, allow_nan=False) if args.json else result["text"])
    return 0 if result["status"] == "answered" else 1


if __name__ == "__main__":
    raise SystemExit(main())
