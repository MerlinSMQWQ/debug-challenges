# Debug #001 Docker 环境验证

验证日期：2026-10-10。验证对象为事故版本；比赛未开始。本文件属于出题者证据，包含故障位置，不应向参赛者公开。

## 固定环境

- 构建入口：`Dockerfile` 与 `compose.yaml`
- 基础镜像：`python:3.13-slim-bookworm`
- 本地执行：Docker Desktop 4.94.0，Linux arm64 引擎
- 持续验证：GitHub Actions 的 Ubuntu runner 从零构建同一配置

## 实际结果

1. `docker compose build` 成功。
2. 容器环境测试共 2 项，全部通过：small 正常结束；daily 超时后清理；两份栈快照可生成。
3. 终端 A 用 `run daily --timeout 0` 保持现场时，终端 B 分别请求 `job` 和 `exporter` 栈成功。job 主线程位于 `job.py` 的 `child.stdout.read()`，exporter 主线程位于 `exporter.py` 向 stderr 写拒绝审计的位置。
4. 现场活动期间从另一个容器执行 `reset` 返回 1，并明确要求先结束任务；终端 A 按 Ctrl-C 后记录 `interrupted` 和退出码 130，容器退出。
5. 恢复事故版本后执行标准业务验收，small 通过，daily 在 8 秒后返回 124，验收整体失败。
6. 临时把顺序读取换成 `child.communicate()` 后，两组业务验收均通过。随后已恢复事故代码。
7. 最终日结证据使用 12 秒保护时限，以便采集两个容器的栈；结果仍为 `timeout`、退出码 124。父进程和工作进程分别停在上述相同位置。

## 交付边界

交付保留故障代码、固定输入和业务契约。容器化只替换环境与诊断入口，没有改变 stdout/stderr 的连接方式、读取顺序或触发数据。初始事故记录已由 Linux 容器重新生成；最终提交前清空 `var/runs/`。
