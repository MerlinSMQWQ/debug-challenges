import argparse
import json
from pathlib import Path
import subprocess
import sys

from settlement_export.diagnostics import stack_probe


def main():
    parser = argparse.ArgumentParser(description="执行一次门店发票结算导出")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with (args.output_dir / "job.log").open("w", encoding="utf-8") as log:
        def event(name, **fields):
            print(json.dumps({"event": name, **fields}), file=log, flush=True)

        with stack_probe(args.output_dir, "job"):
            event("job_started", input=str(args.input), output_dir=str(args.output_dir))
            command = [
                sys.executable, "-u", "-m", "settlement_export.exporter",
                "--input", str(args.input),
                "--config", str(args.config),
                "--output-dir", str(args.output_dir),
            ]
            child = subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            event("exporter_started", pid=child.pid)
            result = child.stdout.read()
            diagnostics = child.stderr.read()
            child.wait()
            (args.output_dir / "worker.log").write_text(diagnostics, encoding="utf-8")
            if child.returncode != 0:
                event("job_failed", returncode=child.returncode)
                return child.returncode
            summary = json.loads(result)
            (args.output_dir / "summary.json").write_text(
                json.dumps(summary, indent=2) + "\n", encoding="utf-8"
            )
            event("job_completed", **summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
