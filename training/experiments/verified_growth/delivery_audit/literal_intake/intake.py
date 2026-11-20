"""Read explicit literal assertions and requested calls, then use the existing checked relay."""
import ast
import json
import re

from training.experiments.verified_growth.file_relay import relay


NEGATION = re.compile(r"\b(?:not|never|incorrect|wrong|ignore|unless|maybe|might|possibly|counterexamples?)\b|n['’]t\b", re.I)
REL = re.compile(r"^\s*`?\s*(?:(?:should|must|will|would)\s+)?(?:==|=>|->|→|returns?\b|gives?\b|"
                 r"produces?\b|equals?\b|evaluates? to\b|yields?\b|is\b)\s*`?\s*", re.I)
REPORT = re.compile(r"\b(?:tell me|give me|report|print|show me)\b", re.I)
LAYOUT = re.compile(r"\b(?:each on (?:its own|a separate) line|one (?:per|on each) line|"
                    r"on separate lines|in (?:that|this) order)\b", re.I)
FILENAME = re.compile(r"(?<![\w.-])(?:[\w.-]+[/\\])*[\w.-]+\.(?:py|json|csv|txt|md|tsv)\b", re.I)
NUMBERS = {word:i for i,word in enumerate("zero one two three four five six seven eight nine ten".split())}


def token(call):
    name, args = call
    return name + "(" + ", ".join(map(repr, args)) + ")"


def normalized(spec):
    filename, _, examples, queries = spec
    text = "Save " + filename + ". " + "; ".join(token(call) + " == " + repr(value) for call,value in examples) + "."
    if queries:
        text += " Then tell me the values of " + " and ".join(map(token,queries)) + "."
    return text


def query_part(masked, calls):
    """Accept only a report whose remaining words specify calls, their order, or line layout."""
    queries, pieces = [], []
    keep_from = 0
    for report in REPORT.finditer(masked):
        if report.start() < keep_from:
            continue
        stop = re.search(r"[.!?](?=\s|$)|\n\s*\n", masked[report.end():])
        end = report.end() + stop.start() if stop else len(masked)
        fragment = masked[report.end():end]
        ids = [int(i) for i in re.findall(r"§(\d+)§",fragment)]
        if not ids:
            return None
        remainder = LAYOUT.sub("", re.sub(r"§\d+§", "", fragment))
        remainder = re.sub(r"\b(?:the|both|values?|results?|outputs?|answers?|and|of|for|then|followed by|please)\b",
                           "", remainder, flags=re.I)
        if re.sub(r"[,;:\s`*]", "", remainder):
            return None
        for i in ids:
            call = relay.call_args(calls[i])
            if call is None:
                return None
            queries.append(call)
        pieces.append(masked[keep_from:report.start()])
        keep_from = end
    pieces.append(masked[keep_from:])
    return queries, " ".join(pieces)


def contract(text):
    if not isinstance(text,str) or len(text)>12000 or "§" in text:
        return None
    files = set(FILENAME.findall(text))
    if (len(files)!=1 or not relay.FILE.fullmatch(next(iter(files)))
            or not re.search(r"\b(?:write|save|implement|create|build|provide|deliver)\b", text, re.I)
            or re.search(r"\b(?:class|classes|test file|test suite|write tests?|input files?)\b",text,re.I)):
        return None
    filename = files.pop()
    calls = list(relay.CALL.finditer(text))
    # Mask calls before parsing clauses so words or punctuation inside arguments are never instructions.
    masked = text
    for i in reversed(range(len(calls))):
        call = calls[i]
        masked = masked[:call.start()] + f"§{i}§" + masked[call.end():]
    if NEGATION.search(masked):
        return None
    queries = query_part(masked, calls)
    if queries is None:
        return None
    queries, assertions = queries
    names, examples, identities = set(), [], {}
    for entry in re.finditer(r"§(\d+)§",assertions):
        match = calls[int(entry[1])]
        names.add(match[1])
        relation = REL.match(assertions[entry.end():])
        args = relay.call_args(match)
        if not args or not relation:
            continue
        tail = assertions[entry.end()+relation.end():]
        val = relay.VALUE.match(tail)
        if not val:
            return None
        rest = tail[val.end():].lstrip("`* ")
        if rest and rest[0] not in "),.;\n":
            return None
        if re.match(r"^[),.;\s]*(?:or|except|instead|only when)\b",rest,re.I):
            return None
        try:
            value=ast.literal_eval(val.group())
            key=json.dumps(args,ensure_ascii=False,sort_keys=True,allow_nan=False)
            encoded=json.dumps(value,ensure_ascii=False,sort_keys=True,allow_nan=False)
        except (ValueError, SyntaxError, TypeError, RecursionError):
            return None
        if key in identities:
            if identities[key] != encoded:
                return None
        else:
            identities[key]=encoded
            examples.append((args,value))
    checked_names={call[0] for call,_ in examples}
    declared=set(re.findall(r"\b(?:def|function (?:named|called))\s+([A-Za-z_]\w*)",text))
    bare_list = rf"(`?{relay.IDENT}`?(?:\s*(?:,\s*(?:and\s+)?|\s+and\s+)\s*`?{relay.IDENT}`?)+)"
    for match in re.finditer(r"\bfunctions?\s+(?:(?:named|called)\s+)?" + bare_list,text,re.I):
        declared.update(name for name in re.findall(relay.IDENT, match[1]) if name.lower()!="and")
    counts=re.findall(r"\b(\d+|one|two|three|four|five|six|seven|eight|nine|ten) functions?\b",masked,re.I)
    if (len(examples)<2 or names!=checked_names or not declared<=checked_names or
            any(call[0] not in checked_names for call in queries) or
            any((int(c) if c.isdigit() else NUMBERS[c.lower()])!=len(checked_names) for c in counts)):
        return None
    spec = filename,names,examples,queries
    # The normalized request must produce exactly the original typed literals, names, and query order.
    checked = relay.contract(normalized(spec))
    return spec if checked==spec else None


def propose(request, files, programs, visible_report, *, guest=None):
    spec = contract(request)
    if spec is None:
        return {"status":"abstained","files":{},"text":""}
    return relay.propose(normalized(spec),files,programs,visible_report,guest=guest)
