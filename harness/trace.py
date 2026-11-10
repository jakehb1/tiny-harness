"""Pretty colored step trace. Set NO_COLOR=1 to disable."""
import os
import sys

_ON = (sys.stdout.isatty() or os.getenv("FORCE_COLOR", "0") != "0") and not os.getenv("NO_COLOR")
_C = {"dim": "2", "bold": "1", "red": "31", "green": "32", "yellow": "33",
      "blue": "34", "magenta": "35", "cyan": "36", "gray": "90"}


def c(text, *styles):
    if not _ON:
        return str(text)
    codes = ";".join(_C[s] for s in styles)
    return f"\033[{codes}m{text}\033[0m"


def short(text, n=56):
    text = " ".join(str(text).split())
    return text if len(text) <= n else text[: n - 1] + "…"


class Trace:
    def __init__(self, quiet=False):
        self.quiet = quiet

    def _p(self, *parts):
        if not self.quiet:
            print(*parts)

    def step(self, n, budget):
        self._p(c(f"  step {n}/{budget}", "gray"))

    def thought(self, t):
        self._p("   ", c("think", "magenta"), c(short(t), "dim"))

    def call(self, name, args):
        a = ", ".join(f"{k}={v!r}" for k, v in args.items())
        self._p("   ", c("tool ", "cyan"), c(short(f"{name}({a})", 52), "bold"))

    def observe(self, obs):
        self._p("   ", c("  ->", "blue"), short(obs, 52))

    def note(self, n):
        self._p("   ", c("note ", "yellow"), short(n, 52))

    def retry(self, err, k, max_k):
        self._p("   ", c(f"retry {k}/{max_k}", "yellow", "bold"), c(short(err, 48), "yellow"))

    def fail(self, msg):
        self._p("   ", c("✗ FAIL", "red", "bold"), c(short(msg, 50), "red"))

    def done(self, answer):
        self._p("   ", c("✓ DONE", "green", "bold"), c(short(answer, 50), "green"))
