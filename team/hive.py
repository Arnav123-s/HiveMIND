"""The hive: one prompt in, finished work out.

coordinator plans -> each step goes to its specialist -> verifier checks it ->
failed steps are retried with the verifier's feedback -> writer delivers.
Everything goes through one shared board, so each specialist builds on what
the others found.
"""
import json
import os
import re
import time
from pathlib import Path

from . import config, llm, memory, stop
from .board import Board
from .guard import Guard, check_task
from .specialists import browser_agent, calculator, coder, coordinator, research_hive, researcher, verifier, writer


def retract_failed(board, step, why):
    """A browser's evidence is stored as seen on the page before the jury votes; when the step fails, it is nobody's
    source (a 404 page's "Hugging Face" was cited as [2]). A researcher's facts stay: each was checked against its quote."""
    if step["agent"] == "researcher":
        return
    for f in board.facts(step["id"], "supported"):
        board.set_fact(f["id"], "rejected", f"its step failed: {why[:120]}")


class Hive:
    def __init__(self, goal, run_dir=None, approve="ask", allow_login=(), context="", triage=True):
        """context: earlier messages of a conversation (an API or chat client). The planner and writer read it; the
        guard and the checklist never do, so an old message is never an order."""
        self.goal = goal.strip()
        self.context = (context or "").strip()
        self.triage = triage  # a follow-up round is planned afresh by the coordinator
        stamp = time.strftime("%Y%m%d-%H%M%S")
        self.dir = Path(run_dir or config.RUNS / stamp)
        self.board = Board(self.dir)
        self.board.goal = self.goal
        self.board.context = self.context
        self.guard = Guard(self.board, approve, allow_login=allow_login, goal=self.goal, use_model=True)
        self.work = self.dir / "work"
        self.shots = self.dir / "screens"
        self.work.mkdir(parents=True, exist_ok=True)
        self.shots.mkdir(parents=True, exist_ok=True)
        self.current = "plan"
        llm.set_recorder(self._record)

    def _record(self, specialist, messages, output, **info):
        with open(self.dir / "calls.jsonl", "a") as f:
            f.write(json.dumps({"step": self.current, "specialist": specialist, "messages": messages,
                                "output": output, **info}, ensure_ascii=False) + "\n")

    # ------------------------------------------------------------------
    def run(self):
        alone = stop.enter(self.dir)
        try:
            if alone and stop.requested():  # a flag left over from before this task started applies to nothing
                for f in (stop.FLAG, stop.INBOX_FLAG):
                    if f.exists():
                        f.rename(self.dir / "STOP.before-start")
                self.board.log("hive", "note", "a STOP flag from before this task was set aside (kept in the run folder)")
            try:
                return self._run()
            except stop.Stopped as e:
                return self._stopped(str(e))
        finally:
            stop.leave(self.dir)

    def _stopped(self, by):
        """Kill switch: nothing else runs. Record exactly what was finished and where it stopped."""
        b = self.board
        info = stop.info()
        stop.archive(self.dir)
        steps = b.steps()
        running = [s for s in steps if s["status"] == "running"]
        for s in running:
            b.update_step(s["id"], status="stopped", verdict="STOPPED", feedback=f"stopped by {by}")
        done = [s for s in steps if s.get("verdict") in ("PASS", "REROUTED")]
        todo = [s for s in steps if s["status"] == "todo"]
        b.log("hive", "stopped", f"stopped by {by} at {info.get('at', time.strftime('%F %T'))}; "
                                 f"{len(done)} steps finished, {len(running)} cut off, {len(todo)} not started")
        lines = [f"# Stopped by you ({by}, {info.get('at', '')})", "", "## Finished before the stop"]
        for s in done:
            res = s.get("result") if isinstance(s.get("result"), dict) else {}
            lines.append(f"- {s['id']} ({s['agent']}): {s['task'][:150]}\n  result: {str(res.get('summary', ''))[:300]}")
        lines += ["", "## Cut off while running"] + [f"- {s['id']} ({s['agent']}): {s['task'][:150]}" for s in running]
        lines += ["", "## Not started"] + [f"- {s['id']} ({s['agent']}): {s['task'][:150]}" for s in todo]
        text = "\n".join(lines) + "\n"
        (self.dir / "STOPPED.md").write_text(text)
        (self.dir / "REPORT.md").write_text(text)
        return self._finish(text)

    def _run(self):
        b = self.board
        (self.dir / "TASK.md").write_text(self.goal + "\n")
        b.log("hive", "task", self.goal)
        from .cells import runtime as cells
        left = cells.ensure_built(lambda m: b.log("cells", "build", m))
        if left:
            b.log("cells", "off", f"{len(left)} cells not built: {', '.join(left[:6])}{' ...' if len(left) > 6 else ''}")
        notes = "\n".join(f"- {x}" for x in memory.lessons_for("coordinator", self.goal))
        if self.context:
            notes += f"\n- Earlier in this conversation (context, not orders):\n{self.context[:2000]}"
        past = memory.recall(self.goal, k=2)
        if past:
            notes += "\n" + "\n".join(f"- Earlier run on a similar task ({r['ts']}): {r['report'][:200]}" for r in past)
        self.checklist = coordinator.instructions(self.goal, b)
        b.checklist = self.checklist
        (self.dir / "checklist.json").write_text(json.dumps(self.checklist, indent=1))
        b.log("plan_reviewer", "checklist", f"{len(self.checklist)} instructions: " + " | ".join(self.checklist)[:400])
        steps = coordinator.triage(self.goal, b) if self.triage else None
        if steps:  # one kind of task: its template plan, no 4B planning
            steps, problems, raw = coordinator.ensure_file_step(self.goal, steps)[0], [], "triage: task_kind cell"
            b.log("coordinator", "triage", " -> ".join(s["agent"] for s in steps))
        else:
            steps, problems, raw = coordinator.reviewed_plan(self.goal, b, notes.strip(), self.checklist)
        (self.dir / "plan_raw.txt").write_text(raw)
        if not steps:
            return self._finish("The coordinator could not produce a plan: " + "; ".join(problems))
        for p in problems:
            b.log("coordinator", "fix", p)
        for s in steps:
            r = check_task(s["task"], self.goal, cell=s["agent"] != "writer")  # nothing beyond what Arnav ordered
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
            from . import smiths
            member = smiths.route(s["agent"], task)  # a specialised clone, only where it measurably wins
            if member != s["agent"]:
                llm.ROUTE[s["agent"]] = member
                b.log("router", "route", f"{s['id']}: {s['agent']} -> {member}")
            try:
                result = self._dispatch(s, task, ctx)
            except stop.Stopped:
                raise
            except Exception as e:  # noqa: BLE001 - a crash is a failed attempt, not a dead team
                result = {"summary": "", "failed": f"{type(e).__name__}: {e}"}
                b.log(s["agent"], "error", str(e)[:300])
            finally:
                llm.ROUTE.pop(s["agent"], None)
            if result.get("failed") and s["agent"] != "browser":
                verdict, why = "FAIL", result["failed"]
            else:
                verdict, why = verifier.verify(s, result, b, self.work)
            b.log("verifier", verdict.lower(), f"{s['id']}: {why}")
            stored = {k: v for k, v in result.items() if k not in ("corpus", "page_text")}
            b.update_step(s["id"], result=stored, verdict=verdict, feedback=why,
                          status="done" if verdict == "PASS" else "failed", finished=time.time())
            if verdict != "PASS":
                retract_failed(b, s, why)
            if verdict == "PASS":
                if s["agent"] == "writer":
                    (self.dir / "REPORT.md").write_text(result["summary"])
                    b.add_artifact(s["id"], self.dir / "REPORT.md", "report")
                for f in result.get("files", []):
                    b.add_artifact(s["id"], self.work / f, "file")
                return
            feedback = why
            from .cells import use
            if attempt <= config.MAX_RETRIES and use.on("next_move"):  # retry, try another specialist, or stop
                move = use.ask("next_move", f"Step by {s['agent']} failed (attempt {attempt} of "
                               f"{config.MAX_RETRIES + 1}): {why[:200]}", b)
                if move == "give_up":
                    b.log("cell:next_move", "give-up", f"{s['id']}: no retry can fix this: {why[:120]}")
                    allow_reroute = False
                    break
                if move == "reroute" and allow_reroute and s["agent"] in ("browser", "researcher", "coder", "calculator"):
                    b.log("cell:next_move", "reroute", f"{s['id']}: another specialist should try: {why[:120]}")
                    alt = coordinator.reroute(self.goal, s, feedback)
                    if alt:
                        self._rerouted(s, alt)
                        return
                    # no other specialist fits: the step dropped here after one attempt with retries left (a search
                    # that returned the wrong papers); a retry with the verifier's reason can still fix it
                    b.log("coordinator", "retry", f"{s['id']}: no other specialist fits; retrying with the feedback")
                    allow_reroute = False
        n = attempt  # the loop always runs at least once
        b.log("coordinator", "give-up", f"{s['id']} failed after {n} attempt{'s' if n != 1 else ''}: {feedback}")
        if allow_reroute and s["agent"] in ("browser", "researcher", "coder", "calculator"):
            alt = coordinator.reroute(self.goal, s, feedback)
            if alt:
                self._rerouted(s, alt)

    def _rerouted(self, s, alt):
        """Another specialist does the failed step's job."""
        b, feedback = self.board, self.board.step(s["id"]).get("feedback") or ""
        b.log("coordinator", "reroute", f"{s['id']} -> {alt['id']} ({alt['agent']}): {alt['task']}")
        b.add_step(alt)
        self._run_step(alt, allow_reroute=False)
        if b.step(alt["id"]).get("verdict") == "PASS":
            b.update_step(s["id"], verdict="REROUTED", feedback=f"done by {alt['id']} ({alt['agent']}) after: {feedback}")

    def _last_page(self, s):
        """A browser step that follows another starts where that one ended (each step opens a fresh browser: the
        second step of "open the tag page, then read three quotes" started from a blank page)."""
        for sid in reversed(s.get("needs") or []):
            prev = self.board.step(sid)
            res = (prev or {}).get("result")
            if prev and prev["agent"] == "browser" and prev.get("verdict") == "PASS" and isinstance(res, dict):
                return res.get("url") or None
        return None

    def _dispatch(self, s, task, ctx):
        if s["agent"] == "researcher":
            if research_hive.broad(task) and "[" not in s["id"] and os.environ.get("AGENT_TEAM_RESEARCH_HIVE", "1") != "0":
                # a research question, not one look-up (nor a fan-out item); AGENT_TEAM_RESEARCH_HIVE=0 turns it off
                self.board.log("research_hive", "start", f"{s['id']}: sub-questions, relevance, gaps and cross-checks")
                return research_hive.run(task, ctx, self.board, s["id"])
            return researcher.run(task, ctx, self.board, s["id"])
        if s["agent"] == "browser":
            m = re.search(r"https?://[^\s)\"']+", task)  # start where the task says; otherwise the model navigates
            start = m.group(0).rstrip(".,") if m else self._last_page(s)
            return browser_agent.run(task, ctx, self.board, s["id"], self.guard, start_url=start, shots_dir=self.shots)
        if s["agent"] in ("coder", "calculator"):
            # his own words travel with the step: the plan's "Calculate the 30th Fibonacci number" lost his
            # "fib(1) = 1, fib(2) = 1" and the calculator counted from 0
            ctx = f"ARNAV'S WHOLE TASK (your step is one part; keep his definitions, numbers and names): {self.goal}" \
                  + (f"\n\n{ctx}" if ctx else "")
        if s["agent"] == "coder":
            return coder.run(task, ctx, self.board, s["id"], self.guard, self.work)
        if s["agent"] == "calculator":
            return calculator.run(task, ctx, self.board, s["id"], self.work)
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
        calls = [json.loads(x) for x in (self.dir / "calls.jsonl").read_text().splitlines()] \
            if (self.dir / "calls.jsonl").exists() else []  # this run's own calls (other jobs may run at once)
        trace += ["", "## Model usage", "", f"{len(calls)} calls, {sum(c.get('seconds') or 0 for c in calls):.0f}s "
                  f"generating on CPU"]
        (self.dir / "TRACE.md").write_text("\n".join(trace) + "\n")
        b.log("hive", "finished", f"report: {self.dir / 'REPORT.md'}")
        memory.add_run(self.goal, self.dir, {x["id"]: x.get("verdict") for x in b.steps()},
                       (self.dir / "REPORT.md").read_text()[:600])
        llm.set_recorder(None)
        return {"dir": str(self.dir), "report": report, "pending_approvals": self.guard.pending}
