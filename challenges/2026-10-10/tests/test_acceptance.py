"""Business and public sequence contracts; this suite does not award a score."""
import csv
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from shipping import OrderBatch

ROOT = Path(__file__).resolve().parents[1]


class Acceptance(unittest.TestCase):
    def export_case(self, rows):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, output = root / "input.json", root / "output"
            source.write_text(json.dumps(rows), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(ROOT / "shipping.py"), "export",
                 "--input", str(source), "--output", str(output)],
                capture_output=True, text=True, timeout=5)
            self.assertEqual(result.returncode, 0, result.stderr)
            with (output / "manifest.csv").open(encoding="utf-8", newline="") as file:
                actual = list(csv.DictReader(file))
            self.assertEqual(actual, [
                {key: str(row[key]) for key in ("order_id", "sku", "quantity")}
                for row in rows])
            self.assertEqual(json.loads((output / "summary.json").read_text()),
                             {"orders": len(rows), "units": sum(r["quantity"] for r in rows)})
            self.assertFalse((output / "manifest.csv.part").exists())
            self.assertEqual(result.stdout.count("completed "), 1)

    def test_morning(self):
        self.export_case(json.loads((ROOT / "data/morning.json").read_text()))

    def test_empty(self):
        self.export_case([])

    def test_single(self):
        self.export_case([{"order_id": "X1", "sku": "纸", "quantity": 3}])

    def test_long_batch_preserves_order(self):
        self.export_case([{"order_id": "X{}".format(i), "sku": "A", "quantity": i % 5 + 1}
                          for i in range(25)])

    def test_index_contract(self):
        batch = OrderBatch(["a", "b"])
        self.assertEqual(len(batch), 2)
        self.assertEqual(batch[0], "a")
        self.assertEqual(batch[-1], "b")
        self.assertEqual(batch[:], ["a", "b"])
        for index in (2, 8, -3):
            with self.assertRaises(IndexError):
                batch[index]
        with self.assertRaises(TypeError):
            batch["0"]

    def test_iteration_is_finite_and_repeatable(self):
        batch = OrderBatch(["a", "b"])
        for _ in range(2):
            iterator = iter(batch)
            self.assertEqual(next(iterator), "a")
            self.assertEqual(next(iterator), "b")
            with self.assertRaises(StopIteration):
                next(iterator)

    def test_preview_has_no_output_files(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([sys.executable, str(ROOT / "shipping.py"), "preview",
                                     "--input", str(ROOT / "data/morning.json"),
                                     "--output", directory],
                                    capture_output=True, text=True, timeout=5)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.splitlines()[0], "orders=3")
            self.assertEqual(len(result.stdout.splitlines()), 4)
            self.assertEqual(list(Path(directory).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
