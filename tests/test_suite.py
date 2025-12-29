import json
import sys
import tempfile
import types
import unittest
from pathlib import Path

if "google" not in sys.modules:
    fake_module = types.SimpleNamespace(genai=types.SimpleNamespace(Client=lambda *args, **kwargs: object()))
    sys.modules["google"] = fake_module

from src import run_suite


def fake_call_model(_client, _model_id, prompt):
    return json.dumps({"is_safe": "no" if "unsafe" in prompt else "yes", "rationale": "stub"})


class RunSuiteTests(unittest.TestCase):
    def test_run_guarded_blocks_input(self):
        attacks = ["unsafe attack", "another"]
        policy = {"deny_input_regex": ["unsafe"]}
        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "guarded.json"
            run_suite.run(attacks, "guarded", str(out_path), client="client", model_id="model", policy=policy, call_model_fn=fake_call_model, sleep_seconds=0)
            data = json.loads(out_path.read_text())
        self.assertEqual(len(data), 2)
        self.assertTrue(data[0]["blocked"])

    def test_run_unguarded_generates_decisions(self):
        attacks = ["hello"]
        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "unguarded.json"
            run_suite.run(attacks, "unguarded", str(out_path), client="client", model_id="model", policy={}, call_model_fn=fake_call_model, sleep_seconds=0)
            data = json.loads(out_path.read_text())
        self.assertFalse(data[0]["blocked"])
        self.assertIn("decision", data[0])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
