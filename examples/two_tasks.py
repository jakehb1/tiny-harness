"""One Harness, two tasks. Shows what carries over between runs.

Run: python examples/two_tasks.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from harness import Harness, ScriptedModel  # noqa: E402
from harness.trace import Trace, c  # noqa: E402


def J(**kw):
    return json.dumps(kw)


class Recorder:
    """Wraps a model and remembers every system prompt it was shown."""

    def __init__(self, model):
        self.model, self.prompts = model, []

    def complete(self, messages):
        self.prompts.append(messages[0]["content"])
        return self.model.complete(messages)


def script():
    return ScriptedModel([
        # task 1: learn a fact, save it as a note
        J(thought="look up the rate", tool="lookup", args={"query": "h100 hourly rate"}),
        J(thought="done", note="H100 rate is $2.49/hr", final="$2.49/hr"),
        # task 2: a different question
        J(thought="done", final="ok"),
    ])


def run(keep_notes):
    m = Recorder(script())
    h = Harness(m, max_steps=4, trace=Trace(quiet=True))
    h.run("What's the H100 hourly rate?")
    n = len(m.prompts)
    h.run("Summarize the inventory.", keep_notes=keep_notes)
    saw = any("$2.49/hr" in p for p in m.prompts[n:])
    return saw, h.rescues


if __name__ == "__main__":
    print(c(" one Harness, two tasks", "bold", "cyan"))
    saw, _ = run(keep_notes=False)
    print("   default:          task 2 sees task 1's notes?", c(str(saw), "green" if not saw else "red"))
    saw, _ = run(keep_notes=True)
    print("   keep_notes=True:  task 2 sees task 1's notes?", c(str(saw), "green" if saw else "red"))
    print(c(" memory across tasks is a choice, not a side effect.", "gray"))
