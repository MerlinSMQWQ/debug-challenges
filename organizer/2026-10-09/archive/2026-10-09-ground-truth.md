# 出题者 Ground Truth · Debug #001 · 2026-10-09

**赛后才揭示。赛前禁止阅读、检索或引用本文。**

本题按《Debug 挑战赛手册》出题。固定的是缺陷、参考输入与业务契约，具体 PID、时间和管道调度可以变化。不得随参赛者的猜测改设定；工具返回必须来自实际运行，不得伪造栈、日志或实验结果。推荐路径不限制其他有效调查方法。

日期为用户时区 UTC+8 的 2026-10-09。当前只完成出题与环境验证：未开始比赛、未启动比赛计时、未提交、未评分。下方运行耗时是准备阶段的程序验证数据。

## 1 原正常系统与故障注入

正常系统读取门店 CSV；接受配置内币种的行，写出原始行并累计整数金额；不支持的币种通过 stderr 发出每行一条完整 JSON 审计记录；最终通过 stdout 发出汇总 JSON。job.py 启动 exporter.py、取得两个标准流的内容，归档 worker.log 和 summary.json，记录 job_completed，退出 0。

正常版本使用 `result, diagnostics = child.communicate()` 收集两个独立输出流并等待工作进程退出。已先用这个正常基线实际通过两组外部验收，再恢复故障版本进行故障验证。

唯一业务故障注入：将上述调用改为顺序执行 `child.stdout.read()`、`child.stderr.read()`、`child.wait()`。没有修改业务过滤规则、计数、输入数据或工作进程。设定在首次故障验证之前冻结，校验值见下。

根因位于 job.py 的收集输出逻辑：两个有限容量的管道都接到父进程，但父进程坚持把 stdout 读到 EOF 后才开始读取 stderr。诊断产出足够多时，工作进程可能无法完成，它也就无法使 stdout 达到 EOF。

## 2 触发条件与完整因果链

small 含 12 行，其中 3 行按业务规则拒绝；完整 stderr 输出为 2541 字节。daily 含 2400 行，其中 600 行拒绝；正常运行完整 stderr 输出为 509327 字节。触发取决于累计未被读取的诊断字节超过该平台管道可容纳的数量，不是“第几条记录”或某个固定跨平台容量。本次未直接测量管道容量，不把经验值写作实测。

1. 调度进程建立 stdout、stderr 两根管道并启动工作进程。
2. 调度进程进入 stdout.read()，要求一直读到 EOF 才返回。工作进程尚未写最终汇总，且写端仍开放。
3. 工作进程持续处理行，并对拒绝行写 stderr。因为父进程尚未读取 stderr，字节在该管道累计。
4. stderr 可用空间不足，工作进程阻塞在诊断输出。`-u` 与 flush=True 已让语言层刷新，它们不能消除内核管道的有限容量。
5. 工作进程不能继续循环、输出汇总或退出，因此 stdout 写端不关闭，父进程仍无法取得 EOF。
6. 父进程等待 stdout 的结束；子进程等待父进程读取 stderr。这构成等待环。两个进程还在，但均不是持续业务计算。
7. 记录、汇总和 job_completed 的保存位于两次读取之后，因此出现已有部分 exported.csv、仅启动日志、无完成日志的外部症状。8 秒后的终止是运行器保护行为，不是业务程序的自动超时。

小输入碰巧没有填满管道，子进程可以结束，stdout 达到 EOF 后父进程才能读 stderr，故 small 成功不证明该收集策略正确。增加超时不会打破等待环；丢弃或减少审计能影响触发，但不满足原契约。

## 3 支撑机制的权威资料

- [Python 3.9 subprocess / Popen.communicate](https://docs.python.org/3.9/library/subprocess.html#subprocess.Popen.communicate)：读取 stdout、stderr 到 EOF 并等待退出；官方特别要求在使用管道时避免被另一管道的填满阻塞。communicate 的输出缓存在内存中，本题约半 MB 的诊断是有界的小任务。
- [Python subprocess 流属性说明](https://docs.python.org/3.9/library/subprocess.html#subprocess.Popen.stdout)：官方建议用 communicate 代替分别读取 stdout/stderr 或交错读写，以避免操作系统管道缓冲相关死锁。赛前材料没有引用该诊断性提醒。
- [POSIX read](https://pubs.opengroup.org/onlinepubs/9799919799/functions/read.html)：无数据但仍有写端时，阻塞读等待；无写端时，空管道读返回 0，表示 EOF。
- [POSIX write](https://pubs.opengroup.org/onlinepubs/9799919799/functions/write.html)：在未设置 O_NONBLOCK 的管道上，空间不足可以使 write 阻塞。不能依赖一个全平台固定容量。
- [Python I/O read](https://docs.python.org/3.9/library/io.html#io.TextIOBase.read)：缺省/负数长度读取到 EOF；TextIOWrapper 返回的是字符。
- [Python sys 标准流与 -u](https://docs.python.org/3.9/library/sys.html#sys.stdout)：用户态缓冲行为和无缓冲模式的范围。
- [Python faulthandler.register](https://docs.python.org/3.9/library/faulthandler.html#faulthandler.register)：本环境用 SIGUSR1 把真实调用栈写入独立文件；Windows 不支持该接口。

核对日期：2026-10-09。POSIX、subprocess、sys、faulthandler 通过官方页面实时核对；I/O 页面另行实时核对。资料语义与本机实际故障验证分开，官方描述不是伪造实测的依据。

## 4 可获得的关键证据与一条调查路径

合理起点包括输入处理错误、计算过慢、磁盘写入异常、结果格式或退出/归档路径异常。不能只凭“CPU 低”下结论，关键是能解释全部观测的等待关系。

可先重现 small/daily 的外部区别，再定位未完成的操作：启动的两个进程、日志、输出文件和实际调用栈全部可读。无须读本文件或向出题者申请额外证据。

在 `lab.py run daily --timeout 0` 的现场，以实际 PID 请求 SIGUSR1，job.stack 显示父进程停在 stdout.read()；exporter.stack 显示工作进程停在向 stderr 打印拒绝审计的位置。结合两条管道的所有者、字节流和 EOF 条件，得到等待环假设。

可改变一个因素做反证：直接运行 exporter，将 stderr 写入普通文件，保持相同输入；本次实际顺利完成，并保留全部拒绝记录。这个对照本身尚不完整证明父进程根因，但与真实栈、代码的通道关系、正常收集方式保持全部数据仍能完成的修复验证一起，构成因果证据链。

也可以自写并发读取实验，或把 stderr 直接归档到文件后观察 stdout。任何能解释等待环、保持原契约并有实测的独立路径均有效，不必复现以上顺序。

## 5 最小修复与工程选择

把三条顺序收集操作恢复为 communicate，一次收集两个通道并等待进程退出。其余业务不变，正常 small/daily 的 CSV、汇总、审计及完成事件均通过相同外部验收。

若现实任务诊断输出可能无界，不宜全量存在父进程内存：可以把 stderr 直接连接到审计文件，或者持续并发消费到文件。直接落文件的方案简单，保留分流契约；应考虑磁盘错误、磁盘容量与失败任务的记录保留。没有证据要求为了本题引入异步框架、消息队列或通用调度层。

communicate 不自动提供本题外的端到端业务时限；生产中可加合理超时和明确的进程清理，但这是限制故障影响，不是修复本次等待环。把 stderr 合并 stdout 会破坏 stdout 单个汇总 JSON 的通道契约，需额外解析且没有必要。关闭诊断、改变币种或扩容缓冲只能改症状/触发，不满足原约束。

最小修复补丁：

```diff
--- job.py (incident)
+++ job.py (normal)
@@ -26,9 +26,7 @@
                        "--output-dir", str(args.output_dir)]
             child = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
             event("exporter_started", pid=child.pid)
-            result = child.stdout.read()
-            diagnostics = child.stderr.read()
-            child.wait()
+            result, diagnostics = child.communicate()
             (args.output_dir / "worker.log").write_text(diagnostics, encoding="utf-8")
             if child.returncode != 0:
                 event("job_failed", returncode=child.returncode)
```

原始正常版本（赛后参考，未放入参赛者目录）：

```python
import argparse
import faulthandler
import json
from pathlib import Path
import signal
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description="Run one settlement export job")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with (args.output_dir / "job.log").open("w", encoding="utf-8") as log:
        def event(name, **fields):
            print(json.dumps({"event": name, **fields}), file=log, flush=True)

        with (args.output_dir / "job.stack").open("a") as trace:
            faulthandler.register(signal.SIGUSR1, file=trace, all_threads=True)
            event("job_started", input=str(args.input), output_dir=str(args.output_dir))
            command = [sys.executable, "-u", str(Path(__file__).with_name("exporter.py")),
                       "--input", str(args.input), "--config", str(args.config),
                       "--output-dir", str(args.output_dir)]
            child = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            event("exporter_started", pid=child.pid)
            result, diagnostics = child.communicate()
            (args.output_dir / "worker.log").write_text(diagnostics, encoding="utf-8")
            if child.returncode != 0:
                event("job_failed", returncode=child.returncode)
                return child.returncode
            summary = json.loads(result)
            (args.output_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
            event("job_completed", **summary)
            faulthandler.unregister(signal.SIGUSR1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```


## 6 提示，按请求逐级给出

1. 方向：先确认仍未完成的是业务处理、结果保存还是退出收尾；将“进程存在”与“正在计算”分开。
2. 证据：获取两个业务进程的当前 Python 栈，并分别写出它们继续运行需要什么条件。
3. 机制：检查标准输出与标准错误这两个独立通道的有限缓冲、消费行为与 EOF 条件。

提示不得一次连发，不直接给上述根因或修复。用时、次数和级别单独记录。参赛者请求的有效实验应执行并报告真实结果，不能为了保留提示等级而扣留证据。

## 7 实际验证与接受范围

以下检查是出题准备，不是参赛者答题：

- 正常基线：两组 8 秒内结束，验收退出 0。
- 故障版本：small 完成，daily 超时；相同故障再次复现两次。故障版本验收退出 1。
- 真实活动现场：两个业务进程低 CPU、真实 SIGUSR1 栈；运行中 reset 拒绝；Ctrl-C 后无继续运行的业务子进程。
- 同一 daily 输入直接运行 exporter，stderr 归档文件：成功完成。
- 关闭拒绝审计的变体：验收退出 1；改变配置的变体：固定参考校验拒绝。
- 最小修复：相同验收退出 0。
- 最终恢复的是原始故障版本，runtime 已清空；没有比赛开始时间、提交或分数。

实测为 macOS 27.0.1 arm64、/usr/bin/python3 3.9.6 [Clang 21.0.0]。未测 Linux、其他 Python 或 Windows。第一次验证在执行沙箱中因 ps 被禁止停止；源码与现场已清理恢复，随后在获得本次本机验证执行权限后完整重跑。该工具限制不作为题目故障，没有把受限调用冒充实际进程证据。

下面原始记录包含准备阶段路径、真实 PID、栈位置、诊断字节数和正常/故障验收输出，**有泄题性，仅能赛后阅读**。完整 CSV 的字节哈希与摘要用于保留验证证据，不把打印海量 CSV 作为证明。安装路径的最终检查另在文末追加。

固定版本校验：

```json
{
  "faulty_job_sha256": "a45023161b9fe4006b787ceb2ca106502482fae95c65ba049f8d9dc45e62cb2c",
  "normal_job_sha256": "daabb001a57c1142cfad10858696851d45fe9de9fc270a98c79b2bbf97441a14",
  "frozen_before_fault_runs": true
}
```

准备阶段实测记录：

```json
[
  {
    "check": "reset",
    "exit_code": 0,
    "expected_exit": 0,
    "elapsed_seconds": 0.026,
    "stdout": "Runtime reset. Source, config, data and initial evidence preserved.\n",
    "stderr": ""
  },
  {
    "check": "normal baseline acceptance",
    "exit_code": 0,
    "expected_exit": 0,
    "elapsed_seconds": 0.308,
    "stdout": "PASS small: completion, exported records, totals, rejection audit\nPASS daily: completion, exported records, totals, rejection audit\n",
    "stderr": ""
  },
  {
    "run_snapshot": "normal baseline",
    "files": {
      "daily/exported.csv": {
        "sha256": "6e68adef55b65e5008bf1380faa9ee4891f376b4298f9d2b8165492c51aafe26",
        "bytes": 1288620
      },
      "daily/exporter.stack": {
        "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "bytes": 0,
        "text": ""
      },
      "daily/job.log": {
        "sha256": "1b81cc82cbe2aee752159fb0c41a06374b99c519f8b6907dcacd7cda447ed556",
        "bytes": 419,
        "text": "{\"event\": \"job_started\", \"input\": \"/private/tmp/debug-20261009-prep/delivery/challenges/2026-10-09/data/daily.csv\", \"output_dir\": \"/private/tmp/debug-20261009-prep/delivery/challenges/2026-10-09/runtime/daily\"}\n{\"event\": \"exporter_started\", \"pid\": 34831}\n{\"event\": \"job_completed\", \"input_count\": 2400, \"exported_count\": 1800, \"rejected_count\": 600, \"totals_cents\": {\"CNY\": 26655600, \"USD\": 26677800, \"EUR\": 26700000}}\n"
      },
      "daily/job.stack": {
        "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "bytes": 0,
        "text": ""
      },
      "daily/launcher.log": {
        "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "bytes": 0,
        "text": ""
      },
      "daily/observation.json": {
        "sha256": "fb56719da42728469a75c4d521eba8741c3011e6e6c16071b5c1934768196190",
        "bytes": 73,
        "text": "{\n  \"status\": \"finished\",\n  \"exit_code\": 0,\n  \"elapsed_seconds\": 0.127\n}\n"
      },
      "daily/summary.json": {
        "sha256": "6734d2d3b057a03a74ec2cd3a43280989cf23e459a433d8405472a251e728582",
        "bytes": 164,
        "text": "{\n  \"input_count\": 2400,\n  \"exported_count\": 1800,\n  \"rejected_count\": 600,\n  \"totals_cents\": {\n    \"CNY\": 26655600,\n    \"USD\": 26677800,\n    \"EUR\": 26700000\n  }\n}\n"
      },
      "daily/worker.log": {
        "sha256": "230014f84714626aa2d647182ff9ffa3240966e26f58ef4c5bd248d0148801bb",
        "bytes": 509327
      },
      "small/exported.csv": {
        "sha256": "99332d4136dced5289c02c8d2b4edf7d63d405b1157c30517c93c15cf9d92ad1",
        "bytes": 6466
      },
      "small/exporter.stack": {
        "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "bytes": 0,
        "text": ""
      },
      "small/job.log": {
        "sha256": "01a12b24921cb579250af215a692f4b8ca8f1c68429ced77d829fe9347039b79",
        "bytes": 397,
        "text": "{\"event\": \"job_started\", \"input\": \"/private/tmp/debug-20261009-prep/delivery/challenges/2026-10-09/data/small.csv\", \"output_dir\": \"/private/tmp/debug-20261009-prep/delivery/challenges/2026-10-09/runtime/small\"}\n{\"event\": \"exporter_started\", \"pid\": 34828}\n{\"event\": \"job_completed\", \"input_count\": 12, \"exported_count\": 9, \"rejected_count\": 3, \"totals_cents\": {\"CNY\": 744, \"USD\": 855, \"EUR\": 966}}\n"
      },
      "small/job.stack": {
        "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "bytes": 0,
        "text": ""
      },
      "small/launcher.log": {
        "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "bytes": 0,
        "text": ""
      },
      "small/observation.json": {
        "sha256": "a7053403ee9db2d54794d93b0187bf10903bdde72cdcf6e52ed7a124957ea3d1",
        "bytes": 73,
        "text": "{\n  \"status\": \"finished\",\n  \"exit_code\": 0,\n  \"elapsed_seconds\": 0.073\n}\n"
      },
      "small/summary.json": {
        "sha256": "7be8d645d36fc4a52a87a9a3329fc7b4f3f60d0a2bdd6a0d3efb07140d853705",
        "bytes": 142,
        "text": "{\n  \"input_count\": 12,\n  \"exported_count\": 9,\n  \"rejected_count\": 3,\n  \"totals_cents\": {\n    \"CNY\": 744,\n    \"USD\": 855,\n    \"EUR\": 966\n  }\n}\n"
      },
      "small/worker.log": {
        "sha256": "d12861eab8c2607d9a900bf45ebc79e136603f0a71fd38dded3880d9ab43af8d",
        "bytes": 2541,
        "text": "{\"event\": \"rejected\", \"reason\": \"unsupported_currency\", \"row\": {\"invoice_id\": \"INV-000004\", \"account\": \"branch-03\", \"currency\": \"HKD\", \"cents\": \"211\", \"note\": \"Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending.\"}}\n{\"event\": \"rejected\", \"reason\": \"unsupported_currency\", \"row\": {\"invoice_id\": \"INV-000008\", \"account\": \"branch-07\", \"currency\": \"HKD\", \"cents\": \"359\", \"note\": \"Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending.\"}}\n{\"event\": \"rejected\", \"reason\": \"unsupported_currency\", \"row\": {\"invoice_id\": \"INV-000012\", \"account\": \"branch-11\", \"currency\": \"HKD\", \"cents\": \"507\", \"note\": \"Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending.\"}}\n"
      }
    }
  },
  {
    "check": "reset",
    "exit_code": 0,
    "expected_exit": 0,
    "elapsed_seconds": 0.03,
    "stdout": "Runtime reset. Source, config, data and initial evidence preserved.\n",
    "stderr": ""
  },
  {
    "check": "faulty acceptance",
    "exit_code": 1,
    "expected_exit": 1,
    "elapsed_seconds": 8.187,
    "stdout": "PASS small: completion, exported records, totals, rejection audit\nFAIL daily: job did not complete successfully (exit 124); see runtime/daily/\n",
    "stderr": ""
  },
  {
    "run_snapshot": "faulty acceptance",
    "files": {
      "daily/exported.csv": {
        "sha256": "a6938c661a9101c42f8a444b5fc767d74c40c825139d957d364a8652d915ebe6",
        "bytes": 165216
      },
      "daily/exporter.stack": {
        "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "bytes": 0,
        "text": ""
      },
      "daily/job.log": {
        "sha256": "ec2dad795d99bd4c1ec8044c4a1e0d3eb239e7fd41df40290484b2e5e6908b54",
        "bytes": 255,
        "text": "{\"event\": \"job_started\", \"input\": \"/private/tmp/debug-20261009-prep/delivery/challenges/2026-10-09/data/daily.csv\", \"output_dir\": \"/private/tmp/debug-20261009-prep/delivery/challenges/2026-10-09/runtime/daily\"}\n{\"event\": \"exporter_started\", \"pid\": 34839}\n"
      },
      "daily/job.stack": {
        "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "bytes": 0,
        "text": ""
      },
      "daily/launcher.log": {
        "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "bytes": 0,
        "text": ""
      },
      "daily/observation.json": {
        "sha256": "f467d991f70fde26e9d2ede5a9dda987082452bc333795a6276bedefe503eea9",
        "bytes": 74,
        "text": "{\n  \"status\": \"timeout\",\n  \"exit_code\": 124,\n  \"elapsed_seconds\": 8.012\n}\n"
      },
      "small/exported.csv": {
        "sha256": "99332d4136dced5289c02c8d2b4edf7d63d405b1157c30517c93c15cf9d92ad1",
        "bytes": 6466
      },
      "small/exporter.stack": {
        "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "bytes": 0,
        "text": ""
      },
      "small/job.log": {
        "sha256": "c6a19f8200ba898a24b47bfcab601d7fdd0228a3dd879be8e8a3757e68007b80",
        "bytes": 397,
        "text": "{\"event\": \"job_started\", \"input\": \"/private/tmp/debug-20261009-prep/delivery/challenges/2026-10-09/data/small.csv\", \"output_dir\": \"/private/tmp/debug-20261009-prep/delivery/challenges/2026-10-09/runtime/small\"}\n{\"event\": \"exporter_started\", \"pid\": 34836}\n{\"event\": \"job_completed\", \"input_count\": 12, \"exported_count\": 9, \"rejected_count\": 3, \"totals_cents\": {\"CNY\": 744, \"USD\": 855, \"EUR\": 966}}\n"
      },
      "small/job.stack": {
        "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "bytes": 0,
        "text": ""
      },
      "small/launcher.log": {
        "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "bytes": 0,
        "text": ""
      },
      "small/observation.json": {
        "sha256": "0ee96dfcd755ed53aebe1db7b54f4ffae5d71190298e9ea416487bb6ab52daa4",
        "bytes": 73,
        "text": "{\n  \"status\": \"finished\",\n  \"exit_code\": 0,\n  \"elapsed_seconds\": 0.075\n}\n"
      },
      "small/summary.json": {
        "sha256": "7be8d645d36fc4a52a87a9a3329fc7b4f3f60d0a2bdd6a0d3efb07140d853705",
        "bytes": 142,
        "text": "{\n  \"input_count\": 12,\n  \"exported_count\": 9,\n  \"rejected_count\": 3,\n  \"totals_cents\": {\n    \"CNY\": 744,\n    \"USD\": 855,\n    \"EUR\": 966\n  }\n}\n"
      },
      "small/worker.log": {
        "sha256": "d12861eab8c2607d9a900bf45ebc79e136603f0a71fd38dded3880d9ab43af8d",
        "bytes": 2541,
        "text": "{\"event\": \"rejected\", \"reason\": \"unsupported_currency\", \"row\": {\"invoice_id\": \"INV-000004\", \"account\": \"branch-03\", \"currency\": \"HKD\", \"cents\": \"211\", \"note\": \"Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending.\"}}\n{\"event\": \"rejected\", \"reason\": \"unsupported_currency\", \"row\": {\"invoice_id\": \"INV-000008\", \"account\": \"branch-07\", \"currency\": \"HKD\", \"cents\": \"359\", \"note\": \"Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending.\"}}\n{\"event\": \"rejected\", \"reason\": \"unsupported_currency\", \"row\": {\"invoice_id\": \"INV-000012\", \"account\": \"branch-11\", \"currency\": \"HKD\", \"cents\": \"507\", \"note\": \"Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending.\"}}\n"
      }
    }
  },
  {
    "check": "reset",
    "exit_code": 0,
    "expected_exit": 0,
    "elapsed_seconds": 0.04,
    "stdout": "Runtime reset. Source, config, data and initial evidence preserved.\n",
    "stderr": ""
  },
  {
    "check": "fault repeat 1",
    "exit_code": 124,
    "expected_exit": 124,
    "elapsed_seconds": 5.04,
    "stdout": "Started job pid=34866; outputs: /private/tmp/debug-20261009-prep/delivery/challenges/2026-10-09/runtime/daily\nWatchdog: run did not finish within 5.0 seconds; stopping this run.\n{\"status\": \"timeout\", \"exit_code\": 124, \"elapsed_seconds\": 5.007}\n",
    "stderr": ""
  },
  {
    "check": "reset",
    "exit_code": 0,
    "expected_exit": 0,
    "elapsed_seconds": 0.04,
    "stdout": "Runtime reset. Source, config, data and initial evidence preserved.\n",
    "stderr": ""
  },
  {
    "check": "fault repeat 2",
    "exit_code": 124,
    "expected_exit": 124,
    "elapsed_seconds": 5.039,
    "stdout": "Started job pid=34872; outputs: /private/tmp/debug-20261009-prep/delivery/challenges/2026-10-09/runtime/daily\nWatchdog: run did not finish within 5.0 seconds; stopping this run.\n{\"status\": \"timeout\", \"exit_code\": 124, \"elapsed_seconds\": 5.007}\n",
    "stderr": ""
  },
  {
    "check": "reset",
    "exit_code": 0,
    "expected_exit": 0,
    "elapsed_seconds": 0.039,
    "stdout": "Runtime reset. Source, config, data and initial evidence preserved.\n",
    "stderr": ""
  },
  {
    "check": "reset refuses active process",
    "exit_code": 1,
    "stdout": "",
    "stderr": "Process 34878 is still alive. Finish that run in its terminal before reset.\n"
  },
  {
    "check": "live process state",
    "stdout": "  PID  PPID STAT  %CPU    RSS COMMAND\n34878 34877 Ss     1.2  11936 /Applications/Xcode.app/Contents/Developer/Library/Frameworks/Python3.framework/Versions/3.9/Resources/Python.app/Contents/MacOS/Python /private/tmp/debug-20261009-prep/delivery/challenges/2026-10-09/job.py --input /private/tmp/debug-20261009-prep/delivery/challenges/2026-10-09/data/daily.csv --config /private/tmp/debug-20261009-prep/delivery/challenges/2026-10-09/config.json --output-dir /private/tmp/debug-20261009-prep/delivery/challenges/2026-10-09/runtime/daily\n34879 34878 S      1.4  11568 /Applications/Xcode.app/Contents/Developer/Library/Frameworks/Python3.framework/Versions/3.9/Resources/Python.app/Contents/MacOS/Python -u /private/tmp/debug-20261009-prep/delivery/challenges/2026-10-09/exporter.py --input /private/tmp/debug-20261009-prep/delivery/challenges/2026-10-09/data/daily.csv --config /private/tmp/debug-20261009-prep/delivery/challenges/2026-10-09/config.json --output-dir /private/tmp/debug-20261009-prep/delivery/challenges/2026-10-09/runtime/daily\n",
    "stderr": ""
  },
  {
    "run_snapshot": "live stacks",
    "files": {
      "active.json": {
        "sha256": "e2d734d6e545872e331df7c8dc58a6af72e262ad2bdc5f2a6397431b2dc19a5f",
        "bytes": 31,
        "text": "{\"pid\": 34878, \"case\": \"daily\"}"
      },
      "daily/exported.csv": {
        "sha256": "a6938c661a9101c42f8a444b5fc767d74c40c825139d957d364a8652d915ebe6",
        "bytes": 165216
      },
      "daily/exporter.stack": {
        "sha256": "ff94438910f8539f84a68784503669878817edb3af59d5291d2f2d9cf9b963ad",
        "bytes": 268,
        "text": "Current thread 0x00000001efdbbf80 (most recent call first):\n  File \"/private/tmp/debug-20261009-prep/delivery/challenges/2026-10-09/exporter.py\", line 31 in main\n  File \"/private/tmp/debug-20261009-prep/delivery/challenges/2026-10-09/exporter.py\", line 41 in <module>\n"
      },
      "daily/job.log": {
        "sha256": "58fa951458251c42d4a3209ea413d23a68991d8b332f5327b79a309e91f0e5b3",
        "bytes": 255,
        "text": "{\"event\": \"job_started\", \"input\": \"/private/tmp/debug-20261009-prep/delivery/challenges/2026-10-09/data/daily.csv\", \"output_dir\": \"/private/tmp/debug-20261009-prep/delivery/challenges/2026-10-09/runtime/daily\"}\n{\"event\": \"exporter_started\", \"pid\": 34879}\n"
      },
      "daily/job.stack": {
        "sha256": "b1da7e6ada1341888d9c04ce68589d41fb6694e090bdb2c3e9d6af03bb5db392",
        "bytes": 258,
        "text": "Current thread 0x00000001efdbbf80 (most recent call first):\n  File \"/private/tmp/debug-20261009-prep/delivery/challenges/2026-10-09/job.py\", line 29 in main\n  File \"/private/tmp/debug-20261009-prep/delivery/challenges/2026-10-09/job.py\", line 44 in <module>\n"
      },
      "daily/launcher.log": {
        "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "bytes": 0,
        "text": ""
      }
    }
  },
  {
    "check": "Ctrl-C cleanup",
    "exit_code": 130
  },
  {
    "check": "reset",
    "exit_code": 0,
    "expected_exit": 0,
    "elapsed_seconds": 0.044,
    "stdout": "Runtime reset. Source, config, data and initial evidence preserved.\n",
    "stderr": ""
  },
  {
    "check": "isolated exporter with diagnostic file",
    "exit_code": 0,
    "stdout": "{\"input_count\": 2400, \"exported_count\": 1800, \"rejected_count\": 600, \"totals_cents\": {\"CNY\": 26655600, \"USD\": 26677800, \"EUR\": 26700000}}\n",
    "diagnostic_bytes": 509327
  },
  {
    "check": "reset",
    "exit_code": 0,
    "expected_exit": 0,
    "elapsed_seconds": 0.029,
    "stdout": "Runtime reset. Source, config, data and initial evidence preserved.\n",
    "stderr": ""
  },
  {
    "check": "acceptance rejects missing rejection audit",
    "exit_code": 1,
    "expected_exit": 1,
    "elapsed_seconds": 0.316,
    "stdout": "FAIL small: completion, exported records, totals, rejection audit\nFAIL daily: completion, exported records, totals, rejection audit\n",
    "stderr": ""
  },
  {
    "check": "reset",
    "exit_code": 0,
    "expected_exit": 0,
    "elapsed_seconds": 0.026,
    "stdout": "Runtime reset. Source, config, data and initial evidence preserved.\n",
    "stderr": ""
  },
  {
    "check": "acceptance rejects changed reference config",
    "exit_code": 1,
    "expected_exit": 1,
    "elapsed_seconds": 0.024,
    "stdout": "FAIL: reference fixture changed: config.json\n",
    "stderr": ""
  },
  {
    "check": "reset",
    "exit_code": 0,
    "expected_exit": 0,
    "elapsed_seconds": 0.026,
    "stdout": "Runtime reset. Source, config, data and initial evidence preserved.\n",
    "stderr": ""
  },
  {
    "check": "minimal repair acceptance",
    "exit_code": 0,
    "expected_exit": 0,
    "elapsed_seconds": 0.306,
    "stdout": "PASS small: completion, exported records, totals, rejection audit\nPASS daily: completion, exported records, totals, rejection audit\n",
    "stderr": ""
  },
  {
    "run_snapshot": "minimal repair",
    "files": {
      "daily/exported.csv": {
        "sha256": "6e68adef55b65e5008bf1380faa9ee4891f376b4298f9d2b8165492c51aafe26",
        "bytes": 1288620
      },
      "daily/exporter.stack": {
        "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "bytes": 0,
        "text": ""
      },
      "daily/job.log": {
        "sha256": "8acf5df5c3f646b9ec120ebeaef15424174c088edcbfa97e84b1b5b0ca391254",
        "bytes": 419,
        "text": "{\"event\": \"job_started\", \"input\": \"/private/tmp/debug-20261009-prep/delivery/challenges/2026-10-09/data/daily.csv\", \"output_dir\": \"/private/tmp/debug-20261009-prep/delivery/challenges/2026-10-09/runtime/daily\"}\n{\"event\": \"exporter_started\", \"pid\": 34903}\n{\"event\": \"job_completed\", \"input_count\": 2400, \"exported_count\": 1800, \"rejected_count\": 600, \"totals_cents\": {\"CNY\": 26655600, \"USD\": 26677800, \"EUR\": 26700000}}\n"
      },
      "daily/job.stack": {
        "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "bytes": 0,
        "text": ""
      },
      "daily/launcher.log": {
        "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "bytes": 0,
        "text": ""
      },
      "daily/observation.json": {
        "sha256": "0965d041dfefa24c1ebbdf800935c53cc9e3e094bf2a64a224c55305180fd9ba",
        "bytes": 72,
        "text": "{\n  \"status\": \"finished\",\n  \"exit_code\": 0,\n  \"elapsed_seconds\": 0.13\n}\n"
      },
      "daily/summary.json": {
        "sha256": "6734d2d3b057a03a74ec2cd3a43280989cf23e459a433d8405472a251e728582",
        "bytes": 164,
        "text": "{\n  \"input_count\": 2400,\n  \"exported_count\": 1800,\n  \"rejected_count\": 600,\n  \"totals_cents\": {\n    \"CNY\": 26655600,\n    \"USD\": 26677800,\n    \"EUR\": 26700000\n  }\n}\n"
      },
      "daily/worker.log": {
        "sha256": "230014f84714626aa2d647182ff9ffa3240966e26f58ef4c5bd248d0148801bb",
        "bytes": 509327
      },
      "small/exported.csv": {
        "sha256": "99332d4136dced5289c02c8d2b4edf7d63d405b1157c30517c93c15cf9d92ad1",
        "bytes": 6466
      },
      "small/exporter.stack": {
        "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "bytes": 0,
        "text": ""
      },
      "small/job.log": {
        "sha256": "0c26bc4ba06b6dba32889b96a7109849868139e5eee04b9d0d158b92ac8533ca",
        "bytes": 397,
        "text": "{\"event\": \"job_started\", \"input\": \"/private/tmp/debug-20261009-prep/delivery/challenges/2026-10-09/data/small.csv\", \"output_dir\": \"/private/tmp/debug-20261009-prep/delivery/challenges/2026-10-09/runtime/small\"}\n{\"event\": \"exporter_started\", \"pid\": 34900}\n{\"event\": \"job_completed\", \"input_count\": 12, \"exported_count\": 9, \"rejected_count\": 3, \"totals_cents\": {\"CNY\": 744, \"USD\": 855, \"EUR\": 966}}\n"
      },
      "small/job.stack": {
        "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "bytes": 0,
        "text": ""
      },
      "small/launcher.log": {
        "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "bytes": 0,
        "text": ""
      },
      "small/observation.json": {
        "sha256": "6339305b29d6b1590ace90a76b1f561fc53dac7df7c43fd7edb6276892ed280d",
        "bytes": 73,
        "text": "{\n  \"status\": \"finished\",\n  \"exit_code\": 0,\n  \"elapsed_seconds\": 0.072\n}\n"
      },
      "small/summary.json": {
        "sha256": "7be8d645d36fc4a52a87a9a3329fc7b4f3f60d0a2bdd6a0d3efb07140d853705",
        "bytes": 142,
        "text": "{\n  \"input_count\": 12,\n  \"exported_count\": 9,\n  \"rejected_count\": 3,\n  \"totals_cents\": {\n    \"CNY\": 744,\n    \"USD\": 855,\n    \"EUR\": 966\n  }\n}\n"
      },
      "small/worker.log": {
        "sha256": "d12861eab8c2607d9a900bf45ebc79e136603f0a71fd38dded3880d9ab43af8d",
        "bytes": 2541,
        "text": "{\"event\": \"rejected\", \"reason\": \"unsupported_currency\", \"row\": {\"invoice_id\": \"INV-000004\", \"account\": \"branch-03\", \"currency\": \"HKD\", \"cents\": \"211\", \"note\": \"Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending.\"}}\n{\"event\": \"rejected\", \"reason\": \"unsupported_currency\", \"row\": {\"invoice_id\": \"INV-000008\", \"account\": \"branch-07\", \"currency\": \"HKD\", \"cents\": \"359\", \"note\": \"Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending.\"}}\n{\"event\": \"rejected\", \"reason\": \"unsupported_currency\", \"row\": {\"invoice_id\": \"INV-000012\", \"account\": \"branch-11\", \"currency\": \"HKD\", \"cents\": \"507\", \"note\": \"Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending. Submitted by branch kiosk; attachment reference pending.\"}}\n"
      }
    }
  },
  {
    "check": "final reset",
    "exit_code": 0,
    "expected_exit": 0,
    "elapsed_seconds": 0.026,
    "stdout": "Runtime reset. Source, config, data and initial evidence preserved.\n",
    "stderr": ""
  }
]
```


## 8 赛后评分与复盘

按手册：根因 30、机制 20、证据 15、假设 10、实验 10、系统模型 10、修复 5。根因与机制应解释两个进程的等待环、两个独立流及 EOF 生命周期。只说“subprocess 卡住”或背出 communicate 不构成完整机制和证据。

复盘顺序：正常系统 → 唯一注入 → 因果链 → 逐条证据 → 对照实际调查中的有效/无效判断 → 最小与工程修复 → 可迁移的机制。合理假设被证据排除不等于它起初不合理；承认未知、主动找反证、小范围实验及更新模型应获得对应评分。

参赛者调查尚未开始，不能预填其得分、假设或表现。赛后根据实际记录讨论：是否把低 CPU 当作结束、是否把 flush 当作另一端已消费、是否把当前无数据误认为 EOF、是否忽略输出通道拥有不同生命周期。

值得增加的回归是输出超过正常管道缓冲量时，全部业务和完整审计仍能在合理时限内完成；还应验证子进程失败与清理。当前外部验收已覆盖有界的大/小批次和完整业务输出，不用锁定某个调用顺序。现实指标可记录任务阶段、进度和失败/超时状态；增加日志前先判断日志通道本身会否影响被观测系统。

可以带走的知识：调用方不只是等待返回值，还负责它建立的资源与通道；一条流的结束取决于写端生命周期。调试要把“谁等待什么、谁改变条件”连起来，并用真实对照区分等待与计算。

## 9 指定目录落盘后验证

参赛者原事故版本已在指定项目路径实际运行，再次确认 small 成功、daily 超时且验收失败。重置成功，runtime 为空，原始故障源码哈希一致，手册未被本任务改写。

```json
{
  "check": "installed path smoke and faulty acceptance",
  "project": "/Users/a1234/WorkingSpace/Debug 挑战赛",
  "returncode": 1,
  "stdout": "PASS small: completion, exported records, totals, rejection audit\nFAIL daily: job did not complete successfully (exit 124); see runtime/daily/\n",
  "stderr": "",
  "observed": {
    "status": "timeout",
    "exit_code": 124,
    "elapsed_seconds": 8.011
  },
  "manual_sha256": "15149448df1723f01d50d5a973f408f7afcfb2ffbee559230d8bf4694a9f0f37",
  "job_log": "{\"event\": \"job_started\", \"input\": \"/Users/a1234/WorkingSpace/Debug \\u6311\\u6218\\u8d5b/challenges/2026-10-09/data/daily.csv\", \"output_dir\": \"/Users/a1234/WorkingSpace/Debug \\u6311\\u6218\\u8d5b/challenges/2026-10-09/runtime/daily\"}\n{\"event\": \"exporter_started\", \"pid\": 35260}\n"
}
```
