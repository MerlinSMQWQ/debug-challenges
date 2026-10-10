"""验证固定 Linux 容器中的事故现场、栈快照与进程清理。"""

import json
from pathlib import Path
import subprocess
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = [sys.executable, str(ROOT / "scripts/run_export.py")]


class EnvironmentSmoke(unittest.TestCase):
    def setUp(self):
        result = subprocess.run(RUNNER + ["reset"], cwd=ROOT,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def tearDown(self):
        result = subprocess.run(RUNNER + ["reset"], cwd=ROOT,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_small_batch_completes(self):
        result = subprocess.run(RUNNER + ["run", "small"], cwd=ROOT,
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        observation = json.loads(
            (ROOT / "var/runs/small/observation.json").read_text(encoding="utf-8")
        )
        self.assertEqual(observation["status"], "finished")

    def test_daily_snapshot_and_timeout_cleanup(self):
        process = subprocess.Popen(
            RUNNER + ["run", "daily"],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        try:
            deadline = time.monotonic() + 5
            active = ROOT / "var/runs/active.json"
            job_log = ROOT / "var/runs/daily/job.log"
            while time.monotonic() < deadline:
                if (active.exists() and job_log.exists()
                        and "exporter_started" in job_log.read_text(encoding="utf-8")):
                    break
                time.sleep(0.05)
            else:
                self.fail("日结现场未在 5 秒内启动")

            for target in ("job", "exporter"):
                snapshot = subprocess.run(
                    RUNNER + ["stack", "daily", target],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                self.assertEqual(snapshot.returncode, 0, snapshot.stdout + snapshot.stderr)
                stack = ROOT / ("var/runs/daily/%s.stack" % target)
                self.assertIn("Thread", stack.read_text(encoding="utf-8"))

            stdout, _ = process.communicate(timeout=15)
            self.assertEqual(process.returncode, 124, stdout)
            observation = json.loads(
                (ROOT / "var/runs/daily/observation.json").read_text(encoding="utf-8")
            )
            self.assertEqual(observation["status"], "timeout")
            self.assertFalse(active.exists())
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()


if __name__ == "__main__":
    unittest.main(verbosity=2)
