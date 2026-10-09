import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def check(name):
    result = subprocess.run([sys.executable, str(ROOT / "lab.py"), "run", name, "--timeout", "8"],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if result.returncode != 0:
        print("FAIL %s: job did not complete successfully (exit %d); see runtime/%s/" % (name, result.returncode, name))
        return False
    output = ROOT / "runtime" / name
    with (ROOT / "data" / (name + ".csv")).open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    currencies = ("CNY", "USD", "EUR")
    accepted = [row for row in rows if row["currency"] in currencies]
    rejected = [row for row in rows if row["currency"] not in currencies]
    expected = {"input_count": len(rows), "exported_count": len(accepted), "rejected_count": len(rejected),
                "totals_cents": {currency: sum(int(row["cents"]) for row in accepted if row["currency"] == currency) for currency in currencies}}
    with (output / "exported.csv").open(newline="", encoding="utf-8") as file:
        actual_rows = list(csv.DictReader(file))
    summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    diagnostics = [json.loads(line) for line in (output / "worker.log").read_text(encoding="utf-8").splitlines() if line.strip()]
    audited = [item["row"] for item in diagnostics if item.get("event") == "rejected" and item.get("reason") == "unsupported_currency"]
    events = [json.loads(line) for line in (output / "job.log").read_text(encoding="utf-8").splitlines()]
    success = actual_rows == accepted and summary == expected and audited == rejected and any(item.get("event") == "job_completed" for item in events)
    print(("PASS" if success else "FAIL") + " " + name + ": completion, exported records, totals, rejection audit")
    return success


def main():
    manifest = json.loads((ROOT / "fixtures.sha256.json").read_text())
    for name, expected in manifest.items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected:
            print("FAIL: reference fixture changed: " + name)
            return 1
    if (ROOT / "runtime").exists() and any((ROOT / "runtime").iterdir()):
        print("Run reset first. Verification requires an empty runtime directory.")
        return 1
    checks = []
    for name in ("small", "daily"):
        try:
            checks.append(check(name))
        except (OSError, ValueError, KeyError) as error:
            print("FAIL %s: missing or invalid output: %s" % (name, error))
            checks.append(False)
    return 0 if all(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
