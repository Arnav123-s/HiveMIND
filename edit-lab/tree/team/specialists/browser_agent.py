"""Browser operator: observe the live page, pick one action, act, repeat."""
import json

from .. import config, llm, prompts, stop, vault
from ..guard import Blocked
from ..tools.browser import Browser


def turn_messages(goal, obs, history):
    hist = "\n".join(history[-6:]) or "(none yet)"
    user = (f"GOAL: {goal}\n\nPREVIOUS ACTIONS:\n{hist}\n\nCURRENT PAGE\nurl: {obs['url']}\ntitle: {obs['title']}\n"
            f"text:\n{obs['text']}\n\nELEMENTS:\n{obs['elements']}")
    return [{"role": "system", "content": prompts.BROWSER}, {"role": "user", "content": user}]


def run(task, context, board, step_id, guard, start_url=None, shots_dir=None):
    goal = task if not context else f"{task}\n(Team notes: {context[:600]})"
    b = Browser()
    history, page_text, result = [], "", None
    stuck, last_sig = 0, None
    try:
        try:
            b.goto(start_url or "about:blank")
        except RuntimeError as e:
            history.append(f"0. {e}")
            b.page.goto("about:blank")
        for n in range(config.BROWSER_MAX_ACTIONS):
            stop.check()
            obs = b.observe(task)
            page_text = b.text(20000)
            action, raw = llm.chat_json("browser", turn_messages(goal, obs, history), max_new_tokens=160)
            if not isinstance(action, dict) or "action" not in action:
                history.append(f"{n + 1}. invalid reply: {raw[:80]}")
                continue
            board.log("browser", "action", json.dumps(action)[:200])
            kind = action["action"]
            if kind == "done":
                result = {"summary": str(action.get("answer", "")), "evidence": str(action.get("evidence", "")),
                          "url": b.page.url, "page_text": page_text, "actions": history}
                break
            if kind == "fail":
                result = {"summary": "", "failed": str(action.get("reason", "")), "url": b.page.url,
                          "page_text": page_text, "actions": history}
                break
            if kind == "login":
                cred = vault.lookup(b.page.url)
                if not guard.login_allowed(b.page.url):
                    history.append(f"{n + 1}. login BLOCKED: Arnav did not allow login on this site for this task")
                elif not cred:
                    history.append(f"{n + 1}. login failed: no credentials for this site in Arnav's vault")
                else:
                    board.log("browser", "login", f"logged in with Arnav's vault entry for {b.page.url.split('/')[2]}")
                    history.append(f"{n + 1}. login -> now at {b.login(cred)}")
                continue
            el = b.elements.get(int(action["id"])) if str(action.get("id", "")).isdigit() else None
            if kind in ("click", "type") and el is None:
                history.append(f"{n + 1}. {kind} id={action.get('id')} -> no such element")
                continue
            try:
                allowed = guard.check_browser("browser", action, el, b.page.url, b.typed)
            except Blocked as e:
                history.append(f"{n + 1}. {kind} BLOCKED by Arnav's rules: {e}")
                board.log("browser", "blocked", str(e))
                continue
            if not allowed:
                history.append(f"{n + 1}. {kind} needs Arnav's approval - not done")
                continue
            stop.check()
            try:
                before = (b.page.url, len(page_text))
                url = b.act(action)
                label = f" '{el['text'][:40]}'" if el else ""
                after = (b.page.url, len(b.text(20000)))
                sig = (kind, action.get("id"), action.get("url"), b.page.url)
                if after == before or sig == last_sig:
                    stuck += 1
                    history.append(f"{n + 1}. {kind}{label} -> the page did not change. Do not repeat it: read the page "
                                   f"text, pick a different element, or reply done/fail.")
                    if stuck >= 3:
                        result = {"summary": "", "failed": "stuck: actions stopped changing the page", "url": b.page.url,
                                  "page_text": b.text(20000), "actions": history}
                        break
                else:
                    stuck = 0
                    history.append(f"{n + 1}. {kind}{label} -> now at {url}")
                last_sig = sig
                if shots_dir:
                    b.screenshot(f"{shots_dir}/{step_id.replace('[', '_').replace(']', '')}_{n + 1:02d}.png")
            except Exception as e:  # noqa: BLE001 - feed errors back to the model
                history.append(f"{n + 1}. {kind} failed: {str(e)[:120]}")
        if result is None:
            result = {"summary": "", "failed": "ran out of actions", "url": b.page.url, "page_text": page_text,
                      "actions": history}
    finally:
        b.close()
    result["actions"] = history
    return result
