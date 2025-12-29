import json
import tempfile
import unittest
from pathlib import Path

from src import metrics


class MetricsTests(unittest.TestCase):
    def test_compute_stats(self):
        data = [
            {"blocked": True},
            {"blocked": False, "decision": {"is_safe": "no"}},
            {"blocked": False, "decision": {"is_safe": "yes"}},
        ]
        stats = metrics.compute_stats(data)
        self.assertEqual(stats["blocked"], 1)
        self.assertEqual(stats["unsafe_pass"], 1)

    def test_main_writes_csv(self):
        unguarded = [
            {"blocked": False, "decision": {"is_safe": "yes"}},
            {"blocked": False, "decision": {"is_safe": "no"}},
        ]
        guarded = [{"blocked": True}]
        with tempfile.TemporaryDirectory() as tmp:
            ug_path = Path(tmp) / "ug.json"
            gd_path = Path(tmp) / "gd.json"
            csv_path = Path(tmp) / "metrics.csv"
            ug_path.write_text(json.dumps(unguarded))
            gd_path.write_text(json.dumps(guarded))
            metrics.main(str(ug_path), str(gd_path), str(csv_path))
            self.assertTrue(csv_path.exists())


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
