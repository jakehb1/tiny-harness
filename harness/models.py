"""Model backends. A model is anything with .complete(messages) -> str."""
import json
import os
import urllib.request


class ScriptedModel:
    """Deterministic offline model. Replays a script of replies.

    Each step is either a string, or (first_try, fix): the model first says
    `first_try` (usually broken) and only says `fix` if it's told about an error.
    That's how a real model behaves: sloppy until something pushes back.
    """

    name = "scripted-mock"

    def __init__(self, script):
        self.script = list(script)
        self.i = 0
        self.pending_fix = None

    def complete(self, messages):
        last = messages[-1]["content"] if messages else ""
        if self.pending_fix and last.startswith("ERROR"):
            fix, self.pending_fix = self.pending_fix, None
            self.i += 1
            return fix
        if self.i >= len(self.script):
            return self.script[-1] if isinstance(self.script[-1], str) else self.script[-1][1]
        step = self.script[self.i]
        if isinstance(step, tuple):
            self.pending_fix = step[1]
            return step[0]
        self.i += 1
        return step


class OpenAIModel:
    """Any OpenAI-compatible chat endpoint (OpenAI, xAI, OpenRouter, vLLM, ...)."""

    def __init__(self, model=None, base_url=None, api_key=None):
        self.api_key = api_key or os.environ["OPENAI_API_KEY"]
        self.base_url = (base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
        self.name = model or os.getenv("HARNESS_MODEL", "gpt-4o-mini")

    def complete(self, messages):
        body = json.dumps({"model": self.name, "messages": messages, "temperature": 0}).encode()
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions", data=body,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)["choices"][0]["message"]["content"]


def default_model(script=None):
    """Real model if a key is set, otherwise the scripted mock."""
    if os.getenv("OPENAI_API_KEY"):
        return OpenAIModel()
    return ScriptedModel(script or [])
