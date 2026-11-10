"""Same model. Bare loop vs. harness. Run: python demo.py"""
import json

from harness import Harness, ScriptedModel, bare_loop
from harness.trace import Trace, c

TASK = ("Our cluster inventory is in inventory.txt. What does it cost per month "
        "to run every H100 on-demand?")
EXPECTED = "$58,166.40"


def J(**kw):
    return json.dumps(kw)


def sloppy_model():
    """A model that's right in spirit but sloppy in format, like real ones."""
    return ScriptedModel([
        J(thought="count the GPUs first", tool="read_file", args={"path": "inventory.txt"}),
        # malformed: chatty preamble + trailing comma
        ('Sure! {"thought": "need the rate", "tool": "lookup", "args": {"query": "h100 hourly rate"},}',
         J(thought="need the rate", note="32x H100 total", tool="lookup", args={"query": "h100 hourly rate"})),
        # wrong arg name: tool takes `expr`, not `expression`
        (J(thought="do the math", tool="calculator", args={"expression": "32 * 2.49 * 730"}),
         J(thought="do the math", note="rate $2.49/hr", tool="calculator", args={"expr": "32 * 2.49 * 730"})),
        J(thought="done", final="32 H100s x $2.49/hr x 730h = $58,166.40/mo"),
    ])


def runaway_model():
    """A model that never stops calling the same tool."""
    return ScriptedModel([J(thought="let me check again", tool="lookup", args={"query": "h100 hourly rate"})])


def header(title, sub):
    print()
    print(c(f" {title} ", "bold"), c(sub, "gray"))


def verdict(ok, msg):
    print("   " + (c("✓ " + msg, "green", "bold") if ok else c("✗ " + msg, "red", "bold")))


def main():
    print(c(" agent = model + harness", "bold", "cyan"), c("· same mock model, two loops", "gray"))
    print(c(" task:", "gray"), "monthly cost of every H100 in inventory.txt")

    header("1. BARE LOOP", "while True: call model, run tool")
    try:
        out = bare_loop(sloppy_model(), TASK)
        ok = EXPECTED in str(out["answer"])
        verdict(ok, f"returned: {out['answer'][:44]}…" if not ok else out["answer"])
        if not ok:
            print("   " + c("  malformed JSON got returned as the answer", "red"))
    except Exception as e:
        verdict(False, f"crashed: {type(e).__name__}: {e}")

    header("2. HARNESS", "validate · retry · memory · budget")
    h = Harness(sloppy_model(), max_steps=8, max_retries=2)
    out = h.run(TASK)
    ok = EXPECTED in str(out["answer"])
    verdict(ok, f"correct in {out['steps']} steps, {out['rescues']} rescues")

    header("3. RUNAWAY MODEL", "calls the same tool forever")
    bare = bare_loop(runaway_model(), TASK, trace=Trace(quiet=True), hard_stop=50)
    har = Harness(runaway_model(), max_steps=8, trace=Trace(quiet=True)).run(TASK)
    print("   " + c(f"bare loop: {bare['steps']} calls, still going (demo pulled the plug)", "red"))
    print("   " + c(f"harness:   stopped at budget, {har['steps']} steps", "green"))

    print()
    print(c(" same model. the harness is the product.", "bold"))
    print(c(" built by @jakehbradley · Applied Logic (a-l.studio)", "gray"))
    print()


if __name__ == "__main__":
    main()
