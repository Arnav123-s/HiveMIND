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


_NAME = r"(?<![\w/.-])([\w-]+\.(?:py|csv|tsv|json|md|txt|html|xml|ya?ml|xlsx|pdf|png))\b"
_ACTION = re.compile(r"\b(?:sav(?:e|es|ed|ing)|writ(?:e|es|ing|ten)|creat(?:e|es|ed|ing)|mak(?:e|es|ing)|"
                     r"produc(?:e|es|ed|ing)|generat(?:e|es|ed|ing)|stor(?:e|es|ed|ing)|export(?:s|ed|ing)?|"
                     r"convert(?:s|ed|ing)?)\b", re.I)
_FILENAME = re.compile(_NAME, re.I)
_DEST = re.compile(rf"\b(?:to|into|as)\s+(?:a\s+|the\s+)?(?:file\s+)?[`'\"]?{_NAME}", re.I)
_NEXT = re.compile(rf"^[`'\"]?\s*(?:,\s*(?:and\s+)?|and\s+)[`'\"]?{_NAME}", re.I)


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
            yield output[1], rest
            while following := _NEXT.match(rest):
                rest = rest[following.end():]
                yield following[1], rest


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
            labels = _list(re.split(r"\s+and\s+(?:rows|data|sort|print|tell|save|keep|include)\b|:\s*|,?\s+(?:(?:sorted|ordered|grouped) by|keeping|one row)\b", header[1], maxsplit=1, flags=re.I)[0])
        row_order = re.search(r"\brows in (?:the|this) order\s*:?\s+(.+)$", clause, re.I)
        count = re.search(r"\bexactly (\d+) data rows\b", clause, re.I)
        if labels or row_order or count:
            return labels, _list(row_order[1]) if row_order else None, int(count[1]) if count else None
    return None, None, None


def _table(source, task, name):
    header, order, count = _tabular_rules(task, name)
    reader = csv.reader(source, delimiter="\t" if name.lower().endswith(".tsv") else ",", strict=True)
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
        digest.update(json.dumps(row, ensure_ascii=False).encode())
        digest.update(b"\n")
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
    issues, content, byte_hashes = {}, {}, {}
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
        except FileNotFoundError:
            issues[name] = "the requested file is missing"
        except (OSError, ValueError, csv.Error, InvalidOperation, RecursionError) as e:
            issues[name] = str(e)
    return {"issues": issues, "content": content, "byte_hashes": byte_hashes}
