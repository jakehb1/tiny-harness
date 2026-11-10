"""Run the harness on your own task. Uses OPENAI_API_KEY if set, else the mock.

  OPENAI_API_KEY=... python run.py "what's 17% of the H100 rate times 730?"
  (optional) OPENAI_BASE_URL=... HARNESS_MODEL=...
"""
import sys

from harness import Harness, default_model

task = " ".join(sys.argv[1:]) or "How much do the H100s in inventory.txt cost per month?"
model = default_model(script=['{"thought": "no API key set, so I am the mock", "final": "set OPENAI_API_KEY to use a real model"}'])
print(f"model: {model.name}")
Harness(model, max_steps=10).run(task)
