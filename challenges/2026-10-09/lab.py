import argparse
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
RUNTIME = ROOT / "runtime"


def terminate(process):
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait()


def run_case(name, timeout):
    output = RUNTIME / name
    output.mkdir(parents=True, exist_ok=True)
    active = RUNTIME / "active.json"
    if active.exists():
        raise SystemExit("Another run is active or left active.json. Finish that run, then use reset.")
    if (output / "observation.json").exists():
        raise SystemExit("This case has run already. Preserve evidence if needed, then use reset.")
    command = [sys.executable, str(ROOT / "job.py"), "--input", str(ROOT / "data" / (name + ".csv")),
               "--config", str(ROOT / "config.json"), "--output-dir", str(output)]
    started = time.monotonic()
    with (output / "launcher.log").open("w") as log:
        process = subprocess.Popen(command, stdout=log, stderr=log, start_new_session=True)
        active.write_text(json.dumps({"pid": process.pid, "case": name}), encoding="utf-8")
        print("Started job pid=%d; outputs: %s" % (process.pid, output), flush=True)
        status = "finished"
        try:
            code = process.wait(timeout=timeout if timeout > 0 else None)
        except subprocess.TimeoutExpired:
            status, code = "timeout", 124
            print("Watchdog: run did not finish within %.1f seconds; stopping this run." % timeout, flush=True)
        except KeyboardInterrupt:
            status, code = "interrupted", 130
        finally:
            terminate(process)
            active.unlink()
    observation = {"status": status, "exit_code": code, "elapsed_seconds": round(time.monotonic() - started, 3)}
    (output / "observation.json").write_text(json.dumps(observation, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(observation))
    return code


def reset():
    active = RUNTIME / "active.json"
    if active.exists():
        pid = json.loads(active.read_text())["pid"]
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            pass
        else:
            raise SystemExit("Process %s is still alive. Finish that run in its terminal before reset." % pid)
    if RUNTIME.exists():
        shutil.rmtree(RUNTIME)
    RUNTIME.mkdir()
    print("Runtime reset. Source, config, data and initial evidence preserved.")


def main():
    parser = argparse.ArgumentParser(description="Local incident lifecycle; no contest timer")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("reset")
    run = commands.add_parser("run")
    run.add_argument("case", choices=("small", "daily"))
    run.add_argument("--timeout", type=float, default=8.0, help="Run watchdog in seconds; 0 waits until Ctrl-C")
    args = parser.parse_args()
    if args.command == "reset":
        reset()
        return 0
    if args.timeout < 0:
        parser.error("--timeout must be nonnegative")
    return run_case(args.case, args.timeout)


if __name__ == "__main__":
    sys.exit(main())
