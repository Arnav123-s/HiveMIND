"""Checks on named outputs that can be made without an answer key or running user code."""
import csv
from decimal import Decimal, InvalidOperation
import hashlib
import io
import json
import os
import re
import shutil
import stat
import tempfile
from pathlib import Path


_EXT = r"(?:py|csv|tsv|jsonl?|ndjson|md|txt|html?|xml|ya?ml|toml|xlsx?|docx?|pptx?|pdf|png|jpe?g|svg|zip|parquet|sql|ipynb)"
_BARE = rf"[\w-]+(?:\.[\w-]+)*\.{_EXT}\b"
_QUOTED = rf"[\w-][\w .()-]*\.{_EXT}"
_NAME = rf"""(?<![\w/.-])(?P<name>`{_QUOTED}`|"{_QUOTED}"|'{_QUOTED}'|{_BARE})"""
_ACTION = re.compile(r"\b(?:sav(?:e|es|ed|ing)|writ(?:e|es|ing|ten)|creat(?:e|es|ed|ing)|mak(?:e|es|ing)|"
                     r"produc(?:e|es|ed|ing)|generat(?:e|es|ed|ing)|stor(?:e|es|ed|ing)|export(?:s|ed|ing)?|"
                     r"convert(?:s|ed|ing)?)\b", re.I)
_FILENAME = re.compile(_NAME, re.I)
_DEST = re.compile(rf"\b(?:to|into|as)\s+(?:a\s+|the\s+)?(?:file\s+)?{_NAME}", re.I)
_NEXT = re.compile(rf"^[`'\"]?\s*(?:,\s*(?:and\s+)?|and\s+){_NAME}", re.I)


def _outputs(task):
    """Yield an explicit output basename and its following instructions in the same clause."""
    task = task.split("\n\n(This continues a conversation.", 1)[0]
    for part in re.split(r"\n|[;!?]|\.(?:\s|$)", task):
        actions = list(_ACTION.finditer(part))
        for i, action in enumerate(actions):
            if re.search(r"(?:\bnot|n.t|never|without)\s+(?:need to\s+)?$", part[:action.start()], re.I):
                continue
            end = actions[i + 1].start() if i + 1 < len(actions) else len(part)
            clause = part[action.end():end]
            output = _DEST.search(clause)
            if not output:
                output = _FILENAME.search(clause, 0, 100)
                if not output:
                    continue
                lead = clause[:output.start()]
                if re.search(r"\b(?:from|read|reading|using|of)\s+(?:the\s+)?(?:file\s+)?[`'\"]?$", lead, re.I):
                    continue
                if re.search(r"\b(?:that|which)\s+(?:reads?|opens?|uses?)\s*$", lead, re.I):
                    continue
            rest = clause[output.end():]
            yield output["name"].strip("`'\""), rest
            while following := _NEXT.match(rest):
                rest = rest[following.end():]
                yield following["name"].strip("`'\""), rest


def wanted(task):
    """Files the current task explicitly asks the members to produce."""
    return list(dict.fromkeys(name for name, _ in _outputs(task)))


def regular(path):
    """Open a regular file without following a link or blocking on a special file."""
    path = Path(path)
    if path.parent.is_symlink():
        raise ValueError("the work folder is a symbolic link")
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
        raise ValueError("not a regular, independently stored file")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_BINARY", 0)
    file = os.fdopen(os.open(path, flags), "rb")
    after = os.fstat(file.fileno())
    if not os.path.samestat(before, after) or after.st_nlink != 1:
        file.close()
        raise ValueError("the file changed while opening it")
    return file


def copy_files(source, names, destination):
    """Stage complete copies before replacing any destination, including a pre-existing symlink."""
    source, destination = Path(source), Path(destination)
    if destination.is_symlink():
        raise ValueError("the destination is a symbolic link")
    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination) as tmp:
        for name in names:
            if Path(name).name != name or name in ("", ".", ".."):
                raise ValueError(f"invalid output basename {name!r}")
            target = destination / name
            if target.is_dir() and not target.is_symlink():
                raise ValueError(f"{name} is a directory")
            with regular(source / name) as src, (Path(tmp) / name).open("wb") as out:
                shutil.copyfileobj(src, out)
        backup = Path(tmp) / ".previous"
        backup.mkdir()
        moved, published = [], []
        try:
            for name in names:
                target = destination / name
                if target.exists() or target.is_symlink():
                    target.replace(backup / name)
                    moved.append(name)
                (Path(tmp) / name).replace(target)
                published.append(name)
        except OSError:
            for name in published:
                (destination / name).unlink(missing_ok=True)
            for name in moved:
                (backup / name).replace(destination / name)
            raise


def _list(text):
    # A whole, simple list only. Prose, expressions and examples are too ambiguous to enforce.
    words = [s.strip().strip("`'\"") for s in re.split(r",\s*(?:and\s+)?|\s+and\s+", text.strip())]
    return words if len(words) >= 2 and all(re.fullmatch(r"[\w-]+", w) for w in words) else None


def _tabular_rules(task, name):
    for output, clause in _outputs(task):
        if output != name or re.search(r"\b[\w-]+\.(?:csv|tsv)\b", clause, re.I):
            continue
        header = re.match(r"^[`'\"]?\s*[:,]?\s*(?:(?:with|using)\s+(?:the\s+)?)?(?:columns|headers?)\s*[:=]?\s+(.+)", clause, re.I)
        labels = None
        if header:
            labels = _list(re.split(r"\s+and\s+(?:rows|data|(?:one|\d+) data rows?|sort|print|tell|save|keep|include)\b|:\s*|,?\s+(?:(?:sorted|ordered|grouped) by|(?:with (?:the )?)?(?:highest|lowest) \w+ first|keeping|one row)\b", header[1], maxsplit=1, flags=re.I)[0])
        row_order = re.search(r"\brows in (?:the|this) order\s*:?\s+(.+)$", clause, re.I)
        count = re.search(r"\bexactly (\d+) data rows\b", clause, re.I)
        if labels or row_order or count:
            return labels, _list(row_order[1]) if row_order else None, int(count[1]) if count else None
    return None, None, None


def _ordering(task, name):
    """Recognize an unambiguous, single-key, directed sort on a single output table."""
    task = task.split("\n\n(This continues a conversation.", 1)[0]
    tables = [f for f in wanted(task) if f.lower().endswith((".csv", ".tsv"))]
    if tables != [name] or re.search(
        r"\b(?:bytes?|byte[- ](?:exact|for[- ]byte)|verbatim|identical|tie[- ]?break|"
        r"(?:break|resolve) ties|then by|no headers?|without (?:a |the )?header|headerless|"
        r"(?:preserve|keep) (?:the )?(?:original|input|source) (?:order|format|bytes))\b", task, re.I
    ):
        return None
    mentions = list(re.finditer(r"\b(?:sort(?:ed)?|order(?:ed)?)\s+(?:the rows\s+)?by\b", task, re.I))
    extremes = list(re.finditer(r"""\b(highest|lowest)\s+[`"']?([\w-]+)[`"']?\s+first\b""", task, re.I))
    if len(mentions) + len(extremes) != 1:
        return None
    phrase = (mentions or extremes)[0]
    before = task[:phrase.start()]
    position = before.rfind(name)
    if position < 0:
        return None
    following = before[position + len(name):]
    if _FILENAME.search(following) or re.search(r"\b(?:source|input|reference)\b", following, re.I):
        return None
    # A separate sentence must be a direct instruction about the output.
    sections = re.split(r"[;\n]|\.(?:\s|$)", following)
    # Conditional or negated requests cannot authorize a deterministic rewrite.
    sentence = re.split(r"[;\n]|\.(?:\s|$)", before)[-1]
    if re.search(r"\b(?:if|unless|whether|optionally|never|not|without|only when|compare|compared|instead of)\b|n.t\b",
                 sentence, re.I):
        return None
    if len(sections) == 1:
        # Positively recognize a sort attached to the output name or its declared
        # columns. A sort mentioned in arbitrary intervening prose can describe another table.
        field = r"""[`'"]?[\w-]+[`'"]?"""
        fields = rf"{field}(?:\s*,\s*{field})*(?:\s*,?\s+and\s+{field})?"
        schema = rf"(?:(?:with|using)\s+(?:the\s+)?)?(?:columns|headers?)\s*:?\s+{fields}"
        population = r"(?:and\s+)?(?:one|a|\d+)\s+(?:data\s+)?rows?\s+(?:per|for each)\s+[\w-]+"
        attachment = rf"(?:{schema})?\s*[,;]?\s*(?:{population})?\s*,?\s*(?:(?:with|and)\s+)?(?:(?:the|its)\s+)?(?:(?:rows|records)\s*)?"
        if not re.fullmatch(attachment, following.strip("`'\" "), re.I):
            return None
    if len(sections) > 1:
        lead = sections[-1].strip()
        direct = re.fullmatch(r"(?:(?:then|please)\s*)?(?:(?:put|place|list|show|display)\s+"
                              r"(?:the\s+)?(?:rows\s+)?(?:with\s+)?(?:the\s*)?)?", sections[-1].lstrip(), re.I)
        # A separate instruction can first restrict which rows to put in the output,
        # then specify their order. It must name the output as the destination.
        destination = re.fullmatch(r"(?:put|place|include|list|copy|save|write)\b.+?\b(?:in|into|to)\s+"
                                   r"(?:the |this )?(?:output(?: file| table)?|file|table|CSV|TSV)\s*,?", lead, re.I)
        if not direct and not destination:
            return None
    if extremes:
        if re.match(r"\s*(?=[.;\n]|$)", task[phrase.end():]):
            return {"column": phrase[2], "direction": "descending" if phrase[1].lower() == "highest" else "ascending"}
        return None
    # Consume the complete instruction. Qualifiers and second keys require a more precise contract.
    rule = re.match(r"""\s+[`"']?([\w-]+)[`"']?\s+(?:in\s+)?(ascending|descending)(?:\s+order)?"""
                    r"\s*(?=[.;\n]|$)", task[phrase.end():], re.I)
    if rule:
        return {"column": rule[1], "direction": rule[2].lower()}
    return None


def _csv(source, name):
    return csv.reader(source, delimiter="\t" if name.lower().endswith(".tsv") else ",", strict=True)


def _sorted_rows(source, name, rule):
    rows = list(_csv(source, name))
    if not rows or any(not row for row in rows) or rows[0].count(rule["column"]) != 1:
        return None
    index = rows[0].index(rule["column"])
    values = []
    for row in rows[1:]:
        if len(row) != len(rows[0]) or not re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][+-]?\d+)?", row[index].strip()):
            return None
        values.append((Decimal(row[index].strip()), row))
    ordered = sorted(values, key=lambda pair: pair[0], reverse=rule["direction"] == "descending")
    return [rows[0], *(row for _, row in ordered)]


def _digest_row(digest, row):
    digest.update(json.dumps(row, ensure_ascii=False).encode())
    digest.update(b"\n")


def apply_order(work, name, rule):
    """Sort the staging copy, preserving all cell strings and relative order among ties."""
    path = Path(work) / name
    with regular(path) as raw:
        bom = raw.read(3) == b"\xef\xbb\xbf"
        raw.seek(0)
        with io.TextIOWrapper(raw, encoding="utf-8-sig", newline="") as source:
            rows = _sorted_rows(source, name, rule)
            newline = source.newlines if isinstance(source.newlines, str) else "\n"
    if rows is None:
        raise ValueError(f"{name} does not support the requested numeric sort")
    with path.open("w", encoding="utf-8-sig" if bom else "utf-8", newline="") as out:
        csv.writer(out, delimiter="\t" if name.lower().endswith(".tsv") else ",", lineterminator=newline).writerows(rows)


def comparison(delivery):
    """Compare checked row sets in the explicitly requested order, when one exists."""
    return {name: delivery["sorts"][name]["digest"] if name in delivery["sorts"] else digest
            for name, digest in delivery["content"].items()}


def repairs(delivery):
    return [{"name": name, "column": rule["column"], "direction": rule["direction"]}
            for name, rule in delivery["sorts"].items() if rule["digest"] != delivery["content"][name]]


def _table(source, task, name):
    header, order, count = _tabular_rules(task, name)
    reader = _csv(source, name)
    digest = hashlib.sha256()
    # A filter can return zero matches, and a template can deliberately contain just its header.
    current = task.split("\n\n(This continues a conversation.", 1)[0]
    no_header = bool(re.search(r"\b(?:headerless|(?:no|without(?: a| the)?) (?:headers?|headings?))\b", current, re.I))
    header_only_ok = count == 0 or re.search(
        r"\b(?:template|header[- ]only|only (?:a |the )?(?:header|heading)|(?:zero|no|0) data rows|"
        r"(?:one|single|1) (?:row|record|line)|filter\w*|keep only|matching rows|rows (?:that|where)|if (?:any|none))\b",
        current, re.I)
    width, rows, order_columns = None, 0, set()
    for row in reader:
        if not row:
            continue
        if width is None:
            width = len(row)
            if header and row != header:
                raise ValueError(f"expected header {header!r}, found {row!r}")
            order_columns = set(range(width))
        elif len(row) != width:
            raise ValueError(f"record {rows + 1} has {len(row)} columns, expected {width}")
        index = rows if no_header else rows - 1
        if order and 0 <= index < len(order):
            order_columns = {i for i in order_columns if row[i] == order[index]}
        _digest_row(digest, row)
        rows += 1
    if not rows:
        raise ValueError("the table contains no records")
    data_rows = rows if no_header else rows - 1
    if count is not None and data_rows != count:
        raise ValueError(f"expected {count} data rows, found {data_rows}")
    if not data_rows and not header_only_ok:
        raise ValueError("the table holds no rows (at most a heading)")
    if order and (data_rows != len(order) or not order_columns):
        raise ValueError(f"expected rows in the order {order!r}")
    return digest.hexdigest()


def _json_object(pairs):
    data = dict(sorted(pairs, key=lambda pair: pair[0]))
    if len(data) != len(pairs):
        raise ValueError("the JSON object repeats a key")
    return data


def _json_number(text):
    # Read exact decimal values. Binary floats can collapse two distinct quantities.
    value = Decimal(text)
    if not value.is_finite():
        raise ValueError(f"{text} is not a JSON number")
    sign, digits, exponent = value.as_tuple()
    if not any(digits):
        return Decimal(0)
    end = len(digits)
    while digits[end - 1] == 0:
        end -= 1
    return Decimal((sign, digits[:end], exponent + len(digits) - end))


def inspect(task, work, names):
    """Record observable failures and comparable content. A passed shape check does not verify the values."""
    issues, content, byte_hashes, sorts = {}, {}, {}, {}
    for name in names:
        try:
            with regular(Path(work) / name) as file:
                if not os.fstat(file.fileno()).st_size:
                    empty = re.search(rf"\b(?:empty|blank)\s+(?:[\w-]+\s+file\s+|file\s+)?(?:named\s+|called\s+)?[`'\"]?{re.escape(name)}\b", task, re.I)
                    if not empty or Path(name).suffix.lower() in (".csv", ".tsv", ".json"):
                        raise ValueError("the file is empty")
                byte_hashes[name] = hashlib.file_digest(file, "sha256").hexdigest()
                file.seek(0)
                suffix = Path(name).suffix.lower()
                if suffix in (".csv", ".tsv", ".json"):
                    with io.TextIOWrapper(file, encoding="utf-8-sig", newline="") as source:
                        if suffix == ".json":
                            value = json.load(source, object_pairs_hook=_json_object, parse_int=_json_number,
                                              parse_float=_json_number, parse_constant=_json_number)
                            content[name] = hashlib.sha256(ascii(value).encode()).hexdigest()
                        else:
                            content[name] = _table(source, task, name)
                            rule = _ordering(task, name)
                            if rule:
                                source.seek(0)
                                rows = _sorted_rows(source, name, rule)
                                if rows is not None:
                                    digest = hashlib.sha256()
                                    for row in rows:
                                        _digest_row(digest, row)
                                    sorts[name] = dict(rule, digest=digest.hexdigest())
        except FileNotFoundError:
            issues[name] = "the requested file is missing"
        except (OSError, ValueError, csv.Error, InvalidOperation, RecursionError) as e:
            issues[name] = str(e)
    return {"issues": issues, "content": content, "byte_hashes": byte_hashes, "sorts": sorts}
