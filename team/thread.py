"""A GitHub issue as a conversation with the hive (the workflow "Talk to the hive").

    python3 team/thread.py OWNER issue.json comments-1.json [comments-2.json ...] > thread.json

The issue's title and text are the first message. Every later comment by the repository's owner is a message of
theirs, and every comment the workflow itself posted is the hive's reply. Comments by anyone else are left out: the
repository is public, and the hive talks with its owner. Needs nothing but Python.
"""
import json
import re
import sys

BOT = "github-actions[bot]"
FOOT = re.compile(r"\n*<sub>.*?</sub>\s*$", re.S)  # the line the hive's replies end with (how it was answered, how long)
MOST = 20000  # characters of one message


def thread(owner, issue, comments):
    first = "\n\n".join(x.strip() for x in (issue.get("title") or "", issue.get("body") or "") if x and x.strip())
    out = [{"role": "user", "content": first[:MOST]}] if first else []
    for c in sorted((c for c in comments if isinstance(c, dict)), key=lambda c: c.get("id", 0)):
        who, text = (c.get("user") or {}).get("login", ""), (c.get("body") or "").strip()
        if not text:
            continue
        if who == BOT:
            out.append({"role": "assistant", "content": FOOT.sub("", text)[:MOST]})
        elif who.lower() == owner.lower():
            if out and out[-1]["role"] == "user":  # two messages in a row are one turn
                out[-1]["content"] = (out[-1]["content"] + "\n\n" + text)[:MOST]
            else:
                out.append({"role": "user", "content": text[:MOST]})
    return {"name": owner, "messages": out}


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) < 2:
        sys.exit(__doc__)
    comments = []
    for f in a[2:]:
        try:
            page = json.load(open(f))
        except (OSError, ValueError):
            continue
        comments += page if isinstance(page, list) else []
    print(json.dumps(thread(a[0], json.load(open(a[1])), comments)))
