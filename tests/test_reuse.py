import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "examples"))
import demo  # noqa: E402
from harness import Harness  # noqa: E402
from harness.trace import Trace  # noqa: E402
from two_tasks import run  # noqa: E402


class TestReuse(unittest.TestCase):
    def test_notes_cleared_by_default(self):
        saw, _ = run(keep_notes=False)
        self.assertFalse(saw)

    def test_notes_kept_when_asked(self):
        saw, _ = run(keep_notes=True)
        self.assertTrue(saw)

    def test_rescues_are_per_run(self):
        h = Harness(demo.sloppy_model(), max_steps=8, trace=Trace(quiet=True))
        first = h.run(demo.TASK)
        self.assertEqual(first["rescues"], 2)
        self.assertIn(demo.EXPECTED, first["answer"])
        second = h.run("again")  # script is exhausted; no retries happen here
        self.assertEqual(second["rescues"], 0)


if __name__ == "__main__":
    unittest.main()
