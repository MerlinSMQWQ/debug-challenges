"""CI checks the delivered incident, not the participant's repair."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class Environment(unittest.TestCase):
    def test_preview(self):
        result = subprocess.run([sys.executable, "shipping.py", "preview"], cwd=ROOT,
                                capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.splitlines()[0], "orders=3")

    def test_incident_reproduces_without_completed_files(self):
        with tempfile.TemporaryDirectory() as directory:
            for attempt in range(3):
                output = Path(directory) / str(attempt)
                result = subprocess.run([sys.executable, "shipping.py", "export", "--output", str(output)],
                                        cwd=ROOT, capture_output=True, text=True, timeout=5)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout.count("packed "), 3)
                self.assertTrue((output / "manifest.csv.part").exists())
                self.assertFalse((output / "manifest.csv").exists())
                self.assertFalse((output / "summary.json").exists())


if __name__ == "__main__":
    unittest.main()
