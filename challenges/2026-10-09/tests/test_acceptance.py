"""从输入独立计算期望结果，验收业务输出，不调用被测程序的内部函数。"""

import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "var/runs"
INPUTS = {
    "small": "data/samples/small.csv",
    "daily": "data/batches/daily.csv",
}


class SettlementAcceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        manifest = json.loads((ROOT / "tests/fixtures.sha256.json").read_text())
        for name, expected in manifest.items():
            actual = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            if actual != expected:
                raise AssertionError("参考材料已改变，请恢复后验收：" + name)
        if RUNTIME.exists() and any(RUNTIME.iterdir()):
            raise AssertionError(
                "验收需要空的 var/runs/。先保存证据并结束活动任务，"
                "再执行 python3 scripts/run_export.py reset。"
            )

    def check_batch(self, name):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/run_export.py"),
             "run", name, "--timeout", "8"],
            cwd=ROOT, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0,
                         "任务未正常完成，请查看 var/runs/%s/。\n%s%s" % (
                             name, result.stdout, result.stderr
                         ))

        with (ROOT / INPUTS[name]).open(newline="", encoding="utf-8") as file:
            rows = list(csv.DictReader(file))
        currencies = ("CNY", "USD", "EUR")
        accepted = [row for row in rows if row["currency"] in currencies]
        rejected = [row for row in rows if row["currency"] not in currencies]
        expected = {
            "input_count": len(rows),
            "exported_count": len(accepted),
            "rejected_count": len(rejected),
            "totals_cents": {
                currency: sum(int(row["cents"]) for row in accepted
                              if row["currency"] == currency)
                for currency in currencies
            },
        }
        output = RUNTIME / name
        with (output / "exported.csv").open(newline="", encoding="utf-8") as file:
            actual_rows = list(csv.DictReader(file))
        summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
        diagnostics = [
            json.loads(line)
            for line in (output / "worker.log").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        audited = [item["row"] for item in diagnostics
                   if item.get("event") == "rejected"
                   and item.get("reason") == "unsupported_currency"]
        events = [json.loads(line) for line in
                  (output / "job.log").read_text(encoding="utf-8").splitlines()]

        self.assertEqual(actual_rows, accepted, "导出记录的内容或顺序不符合契约")
        self.assertEqual(summary, expected, "汇总计数或金额不符合契约")
        self.assertEqual(audited, rejected, "拒绝审计必须包含每条完整原行")
        self.assertTrue(any(item.get("event") == "job_completed" for item in events),
                        "缺少任务完成记录")

    def test_small_batch(self):
        """样例批次符合完整业务契约。"""
        self.check_batch("small")

    def test_daily_batch(self):
        """日结批次符合完整业务契约。"""
        self.check_batch("daily")


if __name__ == "__main__":
    unittest.main(verbosity=2)
