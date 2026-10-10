# 运行指南

以下命令都在 `challenges/2026-10-09/` 下执行。运行脚本负责保存现场和结束自己启动的进程，不记录比赛计时。

## 准备环境

需要 macOS 和 Python 3.9 或更新版本，只用标准库，无需下载依赖。程序使用 POSIX 进程组和 `SIGUSR1`；Linux 尚未实测，Windows 不在支持范围。具体实测组合见[验证记录](validation.md)。

```sh
python3 --version
python3 scripts/run_export.py --help
python3 scripts/run_export.py run --help
```

赛前完成版本和命令检查即可。先阅读赛前知识、事故说明和规则，明确开始后再运行事故和记录实验。

## 运行两个参考批次

```sh
python3 scripts/run_export.py reset
python3 scripts/run_export.py run small
python3 scripts/run_export.py run daily
```

`small` 使用 `data/samples/small.csv`；`daily` 使用 `data/batches/daily.csv`。运行脚本显示调度进程 PID，并把记录写入 `var/runs/批次名/`。

脚本默认启用 8 秒运行保护。任务及时结束时返回其退出码；到期仍未结束时，停止本次任务的进程组并返回 `124`。按 `Ctrl-C` 手动停止时返回 `130`。这些状态会写入 `observation.json`。

| 运行产物 | 可以了解什么 |
| --- | --- |
| `launcher.log` | 程序启动输出和未处理异常 |
| `job.log` | 调度程序已记录的业务事件 |
| `exported.csv`、`summary.json`、`worker.log` | 转换结果、汇总和拒绝审计；业务要求见事故说明 |
| `job.stack`、`exporter.stack` | 按需请求的 Python 调用栈；未请求时可以为空 |
| `observation.json` | 运行结束方式、退出码和实际耗时 |

输出文件可能尚未生成或尚未完整写入，需要结合程序状态解释。同一批次重跑前必须清理；不同批次可以先后运行。

业务入口也可直接启动，适合在自己的实验副本中调整输入或连接方式：

```sh
python3 -m settlement_export.job \
  --input data/samples/small.csv \
  --config config/settlement.json \
  --output-dir notes/manual-run
```

直接启动不经过运行保护。比赛中的默认复现和验收使用运行脚本。

## 观察正在运行的任务

终端 A 清理后启动持续运行的现场：

```sh
python3 scripts/run_export.py reset
python3 scripts/run_export.py run daily --timeout 0
```

`--timeout 0` 关闭运行保护，任务会等待到结束或手动停止。在终端 B 查看日志和进程；调度 PID 来自终端 A，转换 PID 来自 `job.log` 的 `exporter_started` 记录。

```sh
cat var/runs/daily/job.log
ps -p PID -o pid,ppid,state,%cpu,rss,command
lsof -p PID
kill -USR1 PID
```

把 `PID` 替换为本次运行的实际业务进程编号。两个业务程序都已注册 `SIGUSR1`，收到信号后把当前调用栈分别写入 `job.stack` 或 `exporter.stack`，并继续运行。可以多次请求；每次快照会追加到文件。

观察结束后，在终端 A 按 `Ctrl-C`。运行脚本会结束它创建的本次进程组。使用 `pdb`、新增日志或修改代码可能影响执行时序，请同时记录实验目的和改动。

## 保存证据和清理

可以在 `notes/` 下按实验编号保存日志、源码备份和判断记录，例如：

```sh
mkdir -p notes/experiment-01
cp -R var/runs/daily notes/experiment-01/
python3 scripts/run_export.py reset
```

`reset` 清空全部 `var/runs/`，保留业务源码修改、配置、输入、初始记录和 `notes/`。它发现活动任务时会拒绝清理：先在启动任务的终端按 `Ctrl-C`，再重试。若终端意外关闭，按错误信息确认 `active.json` 中的 PID 已退出后再清理。

清理运行产物不会恢复源码。首次修改前保存自己的源码备份；交付时的源码和参考输入校验值见 `tests/reference.sha256`，可用 `shasum -a 256 -c tests/reference.sha256` 核对。修改业务代码后，源码校验值变化是正常现象。

## 验收修复

```sh
python3 scripts/run_export.py reset
python3 -m unittest discover -s tests -v
```

验收从固定输入独立计算期望结果，检查记录内容及顺序、汇总、金额、拒绝审计和完成事件。两组测试通过、退出码为 `0` 才满足业务要求；失败信息说明未满足的条件，对应运行目录可继续查看。

验收前会检查参考输入与配置的校验值，并要求运行目录为空。验收失败后会保留产物，重跑前先保存需要的证据并清理。通过测试是提交证据的一部分，还需要解释根因和因果机制。
