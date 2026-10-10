# 运行指南

以下命令都在 `challenges/2026-10-09/` 下执行。参赛者只需要本机 Docker，不需要宿主机 Python 或云服务器。

## 准备 Docker

Windows 和 macOS 使用 Docker Desktop，Windows 应使用 Linux containers；Linux 使用 Docker Engine 与 Compose 插件。先确认 Compose 可用，再构建题目镜像：

```text
docker compose version
docker compose build
docker compose run --rm challenge --help
```

镜像基于 Debian Linux 和 Python 3.13，内置本题允许的进程观察工具。Compose 会把当前题目目录挂载到 `/challenge`，所以在宿主机编辑源码后立即生效，无需重建镜像。只有 `Dockerfile` 或系统工具发生变化时才需要重新执行 `build`。

赛前完成这些检查即可；先阅读赛前知识、事故说明和规则，明确开始后再运行事故并记录实验。

## 运行两个参考批次

```text
docker compose run --rm challenge reset
docker compose run --rm challenge run small
docker compose run --rm challenge run daily
```

`small` 使用 `data/samples/small.csv`；`daily` 使用 `data/batches/daily.csv`。运行记录通过挂载写回宿主机的 `var/runs/批次名/`。

脚本默认启用 8 秒运行保护。任务及时结束时返回其退出码；到期仍未结束时，停止本次任务的进程组并返回 `124`。在前台运行中按 `Ctrl-C`，Compose 和运行脚本会回收该临时容器及其业务进程。这些状态会写入 `observation.json`。

| 运行产物 | 可以了解什么 |
| --- | --- |
| `launcher.log` | 程序启动输出和未处理异常 |
| `job.log` | 调度程序已记录的业务事件 |
| `exported.csv`、`summary.json`、`worker.log` | 转换结果、汇总和拒绝审计；业务要求见事故说明 |
| `job.stack`、`exporter.stack` | 按需请求的 Python 调用栈；未请求时可以为空 |
| `observation.json` | 运行结束方式、退出码和实际耗时 |

输出文件可能尚未生成或尚未完整写入，需要结合程序状态解释。同一批次重跑前必须清理；不同批次可以先后运行。

## 观察正在运行的任务

终端 A 清理后启动持续运行的现场：

```text
docker compose run --rm challenge reset
docker compose run --rm challenge run daily --timeout 0
```

`--timeout 0` 关闭运行保护，任务会等待到结束或手动停止。在终端 B 请求两份 Python 栈：

```text
docker compose run --rm challenge stack daily job
docker compose run --rm challenge stack daily exporter
```

终端 B 的临时容器会在共享目录写入请求；终端 A 的业务进程收到后，把所有线程的当前栈分别追加到 `var/runs/daily/job.stack` 和 `exporter.stack`。请求不会中断业务，也不依赖宿主机 PID。重复执行可以取得不同时刻的快照。

需要查看 Linux 进程和打开资源时，可以进入任务容器的 shell。先在宿主机取得通过 `compose run` 启动的一次性容器名：

```text
docker ps --filter ancestor=debug-challenge-001:local
docker exec -it 容器名 sh
```

容器内提供 `ps`、`top`、`lsof`、`rg`、`grep` 和常见文件工具。

结束观察时回到终端 A 按 `Ctrl-C`。

## 保存证据和清理

`var/runs/` 位于宿主机，可以直接用文件管理器或当前系统的复制命令保存到 `notes/`。`notes/` 和运行目录都不会进入版本控制。

正常清理：

```text
docker compose run --rm challenge reset
```

存在 `active.json` 时，清理会拒绝继续，避免另一个容器仍在写入时破坏现场。先在终端 A 结束任务。若 Docker 或终端异常退出并留下了标记，确认相关容器已停止后再执行：

```text
docker compose run --rm challenge reset --force
```

清理只删除 `var/runs/`，不会恢复源码。首次修改前保存自己的源码备份。

## 直接实验与验收

需要绕过运行保护做最小实验时，可以覆盖镜像入口：

```text
docker compose run --rm --entrypoint python challenge \
  -m settlement_export.job \
  --input data/samples/small.csv \
  --config config/settlement.json \
  --output-dir notes/manual-run
```

PowerShell 可以把多行命令写成一行。修复后的业务验收：

```text
docker compose run --rm challenge reset
docker compose run --rm --entrypoint python challenge \
  -m unittest discover -s tests -p "test_acceptance.py" -v
```

验收从固定输入独立计算期望结果，检查记录内容及顺序、汇总、金额、拒绝审计和完成事件。两组测试通过、退出码为 `0` 才满足业务要求；失败信息说明未满足的条件，对应运行目录会保留供调查。

通过测试是提交证据的一部分，还需要解释根因和因果机制。
