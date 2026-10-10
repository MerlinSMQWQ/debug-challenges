import argparse
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "var/runs"
INPUTS = {
    "small": "data/samples/small.csv",
    "daily": "data/batches/daily.csv",
}
STACK_TARGETS = ("job", "exporter")


def terminate(process):
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
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
        raise SystemExit(
            "发现 var/runs/active.json。先在原终端结束任务，再执行 reset；"
            "若上次运行异常退出，也请先确认该文件中的 PID 已退出。"
        )
    if (output / "observation.json").exists():
        raise SystemExit("本批次已有运行记录。请先保存证据，再执行 reset 后重跑。")
    command = [
        sys.executable, "-m", "settlement_export.job",
        "--input", INPUTS[name],
        "--config", "config/settlement.json",
        "--output-dir", str(output.relative_to(ROOT)),
    ]
    started = time.monotonic()
    with (output / "launcher.log").open("w") as log:
        process = subprocess.Popen(
            command,
            cwd=ROOT,
            stdout=log,
            stderr=log,
            start_new_session=True,
        )
        active.write_text(json.dumps({"pid": process.pid, "case": name}), encoding="utf-8")
        print("任务已启动，PID=%d；运行记录：%s" % (
            process.pid, output.relative_to(ROOT)
        ), flush=True)
        status = "finished"
        try:
            code = process.wait(timeout=timeout if timeout > 0 else None)
        except subprocess.TimeoutExpired:
            status, code = "timeout", 124
            print("任务在 %.1f 秒内未结束，运行保护将停止本次任务。" % timeout, flush=True)
        except KeyboardInterrupt:
            status, code = "interrupted", 130
        finally:
            terminate(process)
            active.unlink(missing_ok=True)
    observation = {"status": status, "exit_code": code, "elapsed_seconds": round(time.monotonic() - started, 3)}
    (output / "observation.json").write_text(json.dumps(observation, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(observation))
    return code


def reset(force=False):
    active = RUNTIME / "active.json"
    if active.exists() and not force:
        state = json.loads(active.read_text(encoding="utf-8"))
        raise SystemExit(
            "检测到活动任务标记（批次=%s，PID=%s）。先在原终端结束任务后再执行 reset；"
            "若容器或终端异常退出，确认任务已结束后使用 reset --force 清理残留。"
            % (state.get("case"), state.get("pid"))
        )
    if RUNTIME.exists():
        shutil.rmtree(RUNTIME)
    RUNTIME.mkdir(parents=True)
    print("已清空 var/runs/。源码修改、配置、输入和初始事故记录均已保留。")


def request_stack(case, target):
    active = RUNTIME / "active.json"
    if not active.exists():
        raise SystemExit("当前没有活动任务。先用 run --timeout 0 启动现场。")
    state = json.loads(active.read_text(encoding="utf-8"))
    if state.get("case") != case:
        raise SystemExit("当前活动批次是 %s，不是 %s。" % (state.get("case"), case))

    output = RUNTIME / case
    stack_path = output / (target + ".stack")
    request_path = output / (target + ".stack.request")
    previous_size = stack_path.stat().st_size if stack_path.exists() else 0
    request_path.write_text(str(time.time_ns()), encoding="ascii")

    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if stack_path.exists() and stack_path.stat().st_size > previous_size:
            print("已追加 %s 的 Python 调用栈：%s" % (
                target, stack_path.relative_to(ROOT)
            ))
            return 0
        time.sleep(0.05)
    raise SystemExit(
        "5 秒内没有收到 %s 的栈快照。请确认该业务进程仍在运行，并查看 launcher.log。" % target
    )


def main():
    parser = argparse.ArgumentParser(description="运行结算导出、保存记录或清理运行产物")
    commands = parser.add_subparsers(dest="command", required=True)
    reset_command = commands.add_parser("reset", help="清空全部运行产物；保留源码修改")
    reset_command.add_argument(
        "--force", action="store_true",
        help="确认活动任务已经结束后，清理异常退出遗留的标记",
    )
    run = commands.add_parser("run", help="运行一个参考批次")
    run.add_argument("case", choices=("small", "daily"))
    run.add_argument("--timeout", type=float, default=8.0,
                     help="运行保护时限（秒），默认 8；0 表示等待到手动 Ctrl-C")
    stack = commands.add_parser("stack", help="请求活动业务进程写出 Python 调用栈")
    stack.add_argument("case", choices=tuple(INPUTS))
    stack.add_argument("target", choices=STACK_TARGETS)
    args = parser.parse_args()
    if args.command == "reset":
        reset(force=args.force)
        return 0
    if args.command == "stack":
        return request_stack(args.case, args.target)
    if args.timeout < 0:
        parser.error("--timeout 不能小于 0")
    return run_case(args.case, args.timeout)


if __name__ == "__main__":
    sys.exit(main())
