"""Pass a single, clearly identified, inline CSV/TSV to the frozen one-file composer."""
import argparse
import csv
import io
import json
import re
import sys

from training.experiments.verified_growth.composer import solver


FILE = re.compile(r"(?<![\w./\\-])([\w./\\-]+\.[a-z][a-z0-9]{0,9})\b", re.I)
SAFE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\.(?:csv|tsv|json)", re.I)
HEADER = re.compile(r"[a-zA-Z_][a-zA-Z0-9 _-]{0,63}")
FENCE = re.compile(r"^[ \t]*```(.*)$")
DECLARED = re.compile(
    r"(?:(?:here (?:is|are)|contents of|input(?: file| data| table)?|source(?: file)?|file|table|data)\s*[:=]?\s*)?"
    r"(?:`?([\w.-]+\.(?:csv|tsv))`?)?\s*:?\s*$", re.I
)


class Unclear(ValueError):
    pass


def table_lines(lines):
    fences = [(i, match[1].strip()) for i, line in enumerate(lines) if (match := FENCE.match(line))]
    if fences:
        if len(fences) != 2 or fences[1][1] or fences[1][0] <= fences[0][0] + 1:
            raise Unclear("expected exactly one closed table block")
        start, info = fences[0]
        end = fences[1][0]
        if info and not re.fullmatch(r"(?:(?:csv|tsv)(?:\s+|$))?(?:[\w-]+\.(?:csv|tsv))?", info, re.I):
            raise Unclear("unrecognized fenced table declaration")
        return start, end + 1, lines[start + 1:end], info
    candidates = []
    for start, line in enumerate(lines):
        for delimiter in (",", "\t"):
            if delimiter not in line:
                continue
            if start and any(d in lines[start - 1] for d in (",", "\t")):
                continue
            fields = line.split(delimiter)
            if not all(HEADER.fullmatch(f.strip()) for f in fields):
                continue
            end = start + 1
            while end < len(lines) and lines[end].strip():
                end += 1
            if end > start + 1:
                candidates.append((start, end, lines[start:end], ""))
    if len(candidates) != 1:
        raise Unclear("expected one rectangular table block")
    return candidates[0]


def json_destination(text, name):
    # A filename mentioned in an example is insufficient; there must be an explicit output instruction.
    filename = r"`?" + re.escape(name) + r"\b`?"
    action = r"(?:save|write|export|return|store|put|place|create|produce|generate|output)"
    link = r"(?:as|to|in|into|named|called)"
    if re.search(rf"\b(?:do not|don['’]t|never|without)\s+{action}\b", text, re.I):
        return False
    direct = rf"\b{action}\s+(?:(?:the\s+)?(?:file|output file)\s+)?{filename}"
    named = rf"\b{action}\s+(?:[^.!?;\n]{{0,96}}?\s+)?{link}\s+(?:(?:the )?(?:file|output file)\s+)?{filename}"
    declaration = rf"(?im)^\s*(?:output(?: file)?|destination)\s*[:=]\s*{filename}"
    return re.search(direct, text, re.I) or re.search(named, text, re.I) or re.search(declaration, text)


def read_table(lines, separator):
    if not 2 <= len(lines) <= 10000 or any(not line.strip() for line in lines):
        raise Unclear("expecting a header followed by contiguous records")
    rows = list(csv.reader(io.StringIO("\n".join(lines), newline=""), delimiter=separator, strict=True))
    header = rows[0]
    if (not 2 <= len(header) <= 100 or any(not HEADER.fullmatch(h) for h in header)
            or len({solver.words(h) for h in header}) != len(header)):
        raise Unclear("ambiguous table headers")
    if any(len(r) != len(header) for r in rows[1:]):
        raise Unclear("table is not rectangular")
    buf = io.StringIO(newline="")
    csv.writer(buf, lineterminator="\n").writerows(rows)
    return buf.getvalue()


def extract(message, files=None):
    """Return (prose, named input file) on an unambiguous message with no attachments; otherwise None."""
    if not isinstance(message, str) or not 1 <= len(message) <= 200000 or files or "\x00" in message:
        return None
    lines = message.splitlines()
    try:
        start, end, block, info = table_lines(lines)
        before = lines[:start]
        declaration = DECLARED.fullmatch(before[-1].strip()) if before else None
        declaration_name = declaration[1] if declaration else None
        if declaration:
            before = before[:-1]
        prose = "\n".join([*before, *lines[end:]]).strip()
        if not prose or len(prose) > 4000:
            raise Unclear("expected a short question outside the table")
        names = set(FILE.findall("\n".join((prose, info, declaration_name or ""))))
        if any(not SAFE.fullmatch(n) for n in names):
            raise Unclear("unexpected filenames")
        inputs = [n for n in names if n.lower().endswith((".csv", ".tsv"))]
        outputs = [n for n in names if n.lower().endswith(".json")]
        if len(inputs) != 1 or len(outputs) != 1 or not json_destination(prose, outputs[0]):
            raise Unclear("expecting one explicit source and requested JSON destination")
        source = inputs[0]
        ext = source.rsplit(".", 1)[1].lower()
        if info.lower().split()[:1] in (["csv"], ["tsv"]) and info.lower().split()[0] != ext:
            raise Unclear("delimiter declaration disagrees with filename")
        # A second unfenced data block cannot be ignored beside the selected one.
        for line in prose.splitlines():
            if "\t" in line:
                raise Unclear("tab-separated values remain in the request")
            if "," in line and not re.search(r"\b(?:save|write|file|using|return|count|sum|total|which|what|how)\b", line, re.I):
                raise Unclear("a second possible record remains in the question")
        normalized = read_table(block, "," if ext == "csv" else "\t")
        transport_name = source if ext == "csv" else source.rsplit(".", 1)[0] + ".csv"
        if ext == "tsv":
            prose = prose.replace(source, transport_name)
        return prose, {transport_name: normalized}
    except (Unclear, ValueError, csv.Error):
        return None


def solve_message(message, files=None, mode="rules"):
    if files:
        conflict = isinstance(message, str) and (
            "```" in message or any("," in line or "\t" in line for line in message.splitlines()[1:])
        )
        if conflict:
            return {"status": "abstained", "value": None, "files": {}, "reason": "both attached and possible inline data"}
        return solver.run_files(message, files, mode=mode)
    normalized = extract(message, files)
    if normalized is None:
        return {"status": "abstained", "value": None, "files": {}, "reason": "no unambiguous named inline table"}
    return solver.run_files(*normalized, mode=mode)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("rules", "learned", "flat", "single", "agree"), default="rules")
    result = solve_message(sys.stdin.read(), mode=parser.parse_args().mode)
    print(json.dumps(result, ensure_ascii=False))
    sys.exit(0 if result["status"] == "answered" else 1)
