"""agent = model + harness. Two loops around the same model."""
import json
import re

from .tools import TOOLS, describe_tools, validate_args
from .trace import Trace

PROTOCOL = """You are an agent. Reply with ONE JSON object and nothing else:
  {"thought": "...", "tool": "<name>", "args": {...}}   to call a tool
  {"thought": "...", "final": "<answer>"}                when you're done
Optionally add "note": "..." to save a fact to your scratchpad.

Tools:
"""


def system_prompt(scratchpad=()):
    s = PROTOCOL + describe_tools()
    if scratchpad:
        s += "\n\nScratchpad (your notes so far):\n" + "\n".join(f"- {n}" for n in scratchpad)
    return s


def parse(reply):
    """Pull the first {...} out of the reply and decode it. Returns (obj, err)."""
    m = re.search(r"\{.*\}", reply, re.S)
    if not m:
        return None, "no JSON object found in reply"
    try:
        obj = json.loads(m.group(0))
    except json.JSONDecodeError as e:
        return None, f"bad JSON: {e.msg.lower()}. reply with valid JSON only"
    if not isinstance(obj, dict) or not ("final" in obj or "tool" in obj):
        return None, "JSON must contain 'tool' or 'final'"
    return obj, None


# -----------------------------------------------------------------------------
# 1. The bare loop: what most "agents" start as. Trusts the model completely.
# -----------------------------------------------------------------------------
def bare_loop(model, task, trace=None, hard_stop=50):
    """No validation, no retries, no budget. `hard_stop` only exists so the demo halts."""
    trace = trace or Trace()
    messages = [{"role": "system", "content": system_prompt()}, {"role": "user", "content": task}]
    for n in range(1, hard_stop + 1):
        trace.step(n, "∞")
        reply = model.complete(messages)
        messages.append({"role": "assistant", "content": reply})
        try:
            obj = json.loads(reply)
        except json.JSONDecodeError:
            return {"answer": reply, "steps": n}  # "not a tool call, must be the answer"
        if "final" in obj:
            return {"answer": obj["final"], "steps": n}
        trace.call(obj["tool"], obj["args"])
        obs = TOOLS[obj["tool"]](**obj["args"])  # any bad call just crashes
        trace.observe(obs)
        messages.append({"role": "user", "content": f"Observation: {obs}"})
    return {"answer": None, "steps": hard_stop}


# -----------------------------------------------------------------------------
# 2. The harness: same model, wrapped in a loop that pushes back.
# -----------------------------------------------------------------------------
class Harness:
    def __init__(self, model, max_steps=8, max_retries=2, trace=None):
        self.model = model
        self.max_steps = max_steps      # step budget
        self.max_retries = max_retries  # per step, for malformed / invalid calls
        self.trace = trace or Trace()
        self.scratchpad = []            # notes, re-injected every step (see run(keep_notes=...))
        self.history = []
        self.rescues = 0                # per run; reset at the start of every run()

    def _ask(self):
        msgs = [{"role": "system", "content": system_prompt(self.scratchpad)}] + self.history
        return self.model.complete(msgs)

    def _push_back(self, reply, err):
        self.history += [{"role": "assistant", "content": reply},
                         {"role": "user", "content": f"ERROR: {err}"}]

    def _next_action(self):
        """Ask the model until it produces a valid action, or give up."""
        for attempt in range(self.max_retries + 1):
            reply = self._ask()
            obj, err = parse(reply)
            if obj and "tool" in obj:
                err = validate_args(obj["tool"], obj.get("args", {}))
            if not err:
                self.history.append({"role": "assistant", "content": reply})
                return obj
            if attempt < self.max_retries:
                self.rescues += 1
                self.trace.retry(err, attempt + 1, self.max_retries)
                self._push_back(reply, err)
        return None

    def run(self, task, keep_notes=False):
        """Run one task. Each run starts clean: fresh history and rescue count.

        Notes from earlier runs are cleared unless keep_notes=True, so reusing a
        Harness never leaks one task's scratchpad into the next by accident.
        Pass keep_notes=True when you *want* memory across tasks.
        """
        self.history = [{"role": "user", "content": task}]
        self.rescues = 0
        if not keep_notes:
            self.scratchpad = []
        for n in range(1, self.max_steps + 1):
            self.trace.step(n, self.max_steps)
            obj = self._next_action()
            if obj is None:
                self.trace.fail("model never produced a valid action")
                return {"answer": None, "steps": n, "rescues": self.rescues}
            if obj.get("thought"):
                self.trace.thought(obj["thought"])
            if obj.get("note"):
                self.scratchpad.append(obj["note"])
                self.trace.note(obj["note"])
            if "final" in obj:
                self.trace.done(obj["final"])
                return {"answer": obj["final"], "steps": n, "rescues": self.rescues}
            self.trace.call(obj["tool"], obj.get("args", {}))
            try:
                obs = TOOLS[obj["tool"]](**obj.get("args", {}))
                self.trace.observe(obs)
                self.history.append({"role": "user", "content": f"Observation: {obs}"})
            except Exception as e:  # tool errors become observations, not crashes
                self.rescues += 1
                self.trace.retry(f"{type(e).__name__}: {e}", 1, 1)
                self.history.append({"role": "user", "content": f"ERROR: {type(e).__name__}: {e}"})
        self.trace.fail(f"step budget ({self.max_steps}) exhausted, stopping")
        return {"answer": None, "steps": self.max_steps, "rescues": self.rescues}
