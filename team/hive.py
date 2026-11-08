"""The hive: one prompt in, finished work out.

coordinator plans -> each step goes to its specialist -> verifier checks it ->
failed steps are retried with the verifier's feedback -> writer delivers.
Everything goes through one shared board, so each specialist builds on what
the others found.
"""
import json
import re
import time
from pathlib import Path

from . import config, llm, memory
from .board import Board
from .guard import Guard, check_task
from .specialists import browser_agent, coder, coordinator, researcher, verifier, writer


class Hive:
    def __init__(self, goal, run_dir=None, approve="ask", allow_login=()):
        self.goal = goal.strip()
        stamp = time.strftime("%Y%m%d-%H%M%S")
        self.dir = Path(run_dir or config.RUNS / stamp)
        self.board = Board(self.dir)
        self.board.goal = self.goal
        self.guard = Guard(self.board, approve, allow_login=allow_login)
        self.work = self.dir / "work"
        self.shots = self.dir / "screens"
        self.work.mkdir(parents=True, exist_ok=True)
        self.shots.mkdir(parents=True, exist_ok=True)
        self.current = "plan"
        llm.RECORDER = self._record

    def _record(self, specialist, messages, output):
        with open(self.dir / "calls.jsonl", "a") as f:
            f.write(json.dumps({"step": self.current, "specialist": specialist, "messages": messages,
                                "output": output}, ensure_ascii=False) + "\n")

    # ------------------------------------------------------------------
    def run(self):
        b = self.board
        (self.dir / "TASK.md").write_text(self.goal + "\n")
        b.log("hive", "task", self.goal)
        reason = check_task(self.goal)
        if reason:
            b.log("guard", "refused", reason)
            return self._finish(f"Refused: {reason}.")

        notes = "\n".join(f"- {x}" for x in memory.lessons_for("coordinator", self.goal))
        past = memory.recall(self.goal, k=2)
        if past:
            notes += "\n" + "\n".join(f"- Earlier run on a similar task ({r['ts']}): {r['report'][:200]}" for r in past)
        steps, problems, raw = coordinator.plan(self.goal, b, notes.strip())
        if steps:
            review = coordinator.review(self.goal, steps)
            if review:
                b.log("plan_reviewer", "problems", " | ".join(review))
                notes2 = (notes + "\n" if notes else "") + "A reviewer found these problems in your first plan; fix them:\n" \
                    + "\n".join(f"- {r}" for r in review)
                steps2, problems2, raw2 = coordinator.plan(self.goal, b, notes2.strip())
                if steps2:
                    steps, problems, raw = steps2, problems2, raw2
            else:
                b.log("plan_reviewer", "ok", "plan covers the task")
        (self.dir / "plan_raw.txt").write_text(raw)
        if not steps:
            return self._finish("The coordinator could not produce a plan: " + "; ".join(problems))
        for p in problems:
            b.log("coordinator", "fix", p)
        for s in steps:
            r = check_task(s["task"])
            if r:
                b.log("guard", "dropped", f"{s['id']}: {r}")
                continue
            b.add_step(s)
            b.log("coordinator", "assign", f"{s['id']} -> {s['agent']}: {s['task']}"
                  + (f" (for each item of {s['for_each']})" if s["for_each"] else ""))
        (self.dir / "plan.json").write_text(json.dumps(steps, indent=2))

        for s in b.steps():
            if s["for_each"]:
                self._run_foreach(s)
            else:
                self._run_step(s)
        final = b.step(steps[-1]["id"]) if steps else None
        report = (final or {}).get("result", {})
        report = report.get("summary", "") if isinstance(report, dict) else str(report)
        return self._finish(report)

    def _run_foreach(self, s):
        src = self.board.step(s["for_each"])
        if src and src.get("verdict") == "REROUTED":
            src = self.board.step(s["for_each"] + "r")
        items = ((src or {}).get("result") or {}).get("items", []) if src and src.get("verdict") == "PASS" else []
        items = items[:config.MAX_FOREACH]
        if not items:
            self.board.update_step(s["id"], status="skipped", verdict="FAIL",
                                   feedback=f"no verified items from {s['for_each']}")
            self.board.log("hive", "skip", f"{s['id']}: nothing to repeat over")
            return
        self.board.update_step(s["id"], status="fanned-out", verdict="PASS")
        for i, item in enumerate(items, 1):
            task = s["task"].replace("{item}", str(item))
            # one sub-step handles ONE item: drop "for each of the top 3 ..." wording that makes it try all of them
            task = re.sub(r"\b(each|every) (one )?of the (top |first )?(\d+|two|three|four|five|six) (\w+?)s\b", r"this \5",
                          task, flags=re.I)
            task = re.sub(r"\bfor each (\w+)\b", r"for this \1", task, flags=re.I)
            task = f"Only for {item}: {task}"
            if (s["agent"] == "browser" and "http" not in task and re.fullmatch(r"[\w.\-]+/[\w.\-]+", str(item))
                    and re.search(r"hugging ?face", task + self.goal, re.I)):
                task += f" (page: https://huggingface.co/{item})"
            sub = dict(s, id=f"{s['id']}[{i}]", task=task, for_each=None)
            self.board.add_step(sub)
            self._run_step(sub)
        subs = [x for x in self.board.steps() if x["id"].startswith(s["id"] + "[")]
        passed = sum(x["verdict"] == "PASS" for x in subs)
        self.board.update_step(s["id"], verdict="PASS" if passed else "FAIL",
                               feedback=f"{passed}/{len(subs)} items verified",
                               result={"summary": f"{passed}/{len(subs)} items verified"})

    def _run_step(self, s, allow_reroute=True):
        b = self.board
        feedback = ""
        for attempt in range(1, config.MAX_RETRIES + 2):
            task = s["task"] if not feedback else f"{s['task']}\n(Previous attempt was rejected: {feedback})"
            b.update_step(s["id"], status="running", attempts=attempt, started=time.time())
            b.log(s["agent"], "start", f"{s['id']} attempt {attempt}")
            self.current = s["id"]
            ctx = b.context_for(s["needs"])
            lessons = memory.lessons_for(s["agent"], s["task"])
            if lessons:
                ctx += "\nLessons from earlier runs:\n" + "\n".join(f"- {x}" for x in lessons)
            try:
                result = self._dispatch(s, task, ctx)
            except Exception as e:  # noqa: BLE001 - a crash is a failed attempt, not a dead team
                result = {"summary": "", "failed": f"{type(e).__name__}: {e}"}
                b.log(s["agent"], "error", str(e)[:300])
            if result.get("failed") and s["agent"] != "browser":
                verdict, why = "FAIL", result["failed"]
            else:
                verdict, why = verifier.verify(s, result, b, self.work)
            b.log("verifier", verdict.lower(), f"{s['id']}: {why}")
            stored = {k: v for k, v in result.items() if k not in ("corpus", "page_text")}
            b.update_step(s["id"], result=stored, verdict=verdict, feedback=why,
                          status="done" if verdict == "PASS" else "failed", finished=time.time())
            if verdict == "PASS":
                if s["agent"] == "writer":
                    (self.dir / "REPORT.md").write_text(result["summary"])
                    b.add_artifact(s["id"], self.dir / "REPORT.md", "report")
                for f in result.get("files", []):
                    b.add_artifact(s["id"], self.work / f, "file")
                return
            feedback = why
        b.log("coordinator", "give-up", f"{s['id']} failed after {config.MAX_RETRIES + 1} attempts: {feedback}")
        if allow_reroute and s["agent"] in ("browser", "researcher", "coder"):
            alt = coordinator.reroute(self.goal, s, feedback)
            if alt:
                b.log("coordinator", "reroute", f"{s['id']} -> {alt['id']} ({alt['agent']}): {alt['task']}")
                b.add_step(alt)
                self._run_step(alt, allow_reroute=False)
                if b.step(alt["id"]).get("verdict") == "PASS":
                    b.update_step(s["id"], verdict="REROUTED", feedback=f"done by {alt['id']} ({alt['agent']}) after: {feedback}")

    def _dispatch(self, s, task, ctx):
        if s["agent"] == "researcher":
            return researcher.run(task, ctx, self.board, s["id"])
        if s["agent"] == "browser":
            m = re.search(r"https?://[^\s)\"']+", task)  # start where the task says; otherwise the model navigates
            return browser_agent.run(task, ctx, self.board, s["id"], self.guard,
                                     start_url=m.group(0).rstrip(".,") if m else None, shots_dir=self.shots)
        if s["agent"] == "coder":
            return coder.run(task, ctx, self.board, s["id"], self.guard, self.work)
        if s["agent"] == "writer":
            return writer.run(self.goal, task, self.board, s["needs"])
        raise ValueError(s["agent"])

    # ------------------------------------------------------------------
    def _finish(self, report):
        b = self.board
        if not (self.dir / "REPORT.md").exists():
            (self.dir / "REPORT.md").write_text(report or "(no report)")
        trace = ["# Run trace", "", f"**Task:** {self.goal}", "", "## Steps", "",
                 "| step | specialist | verdict | attempts | task | verifier |", "|---|---|---|---|---|---|"]
        for s in b.steps():
            trace.append(f"| {s['id']} | {s['agent']} | {s.get('verdict') or s['status']} | {s.get('attempts') or 0} | "
                         f"{s['task'][:120].replace('|', '/')} | {str(s.get('feedback') or '')[:140].replace('|', '/')} |")
        trace += ["", "## Facts", ""]
        for f in b.facts():
            trace.append(f"- **{f['status']}** - {f['claim'][:200]} - quote: \"{f['quote'][:160]}\" - {f['url']}")
        trace += ["", "## Approvals asked", ""] + ([f"- {a['agent']}: {a['kind']} - {a['detail']} -> {a['decision']}"
                                                     for a in b.approvals()] or ["- none"])
        trace += ["", "## Model usage", "", f"{llm.STATS['calls']} calls, {llm.STATS['tokens_out']} tokens out, "
                  f"{llm.STATS['seconds']:.0f}s generating on CPU"]
        (self.dir / "TRACE.md").write_text("\n".join(trace) + "\n")
        b.log("hive", "finished", f"report: {self.dir / 'REPORT.md'}")
        memory.add_run(self.goal, self.dir, {x["id"]: x.get("verdict") for x in b.steps()},
                       (self.dir / "REPORT.md").read_text()[:600])
        llm.RECORDER = None
        return {"dir": str(self.dir), "report": report, "pending_approvals": self.guard.pending}
