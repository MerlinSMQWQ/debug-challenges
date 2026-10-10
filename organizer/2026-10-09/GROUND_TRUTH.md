# 出题者故障真相 · Debug #001

**赛后才公开。赛前不得向参赛者展示、引用或搜索本文及本目录的验证记录。**

本题仅完成出题与环境验证，未开始比赛、未启动比赛计时、未提交、未评分。缺陷、参考输入和业务要求在调查前固定；PID、耗时和调度顺序以每次真实运行为准。

## 正常系统与故障注入

`settlement_export/exporter.py` 逐行读取发票，保留配置支持的币种并累计整数分金额；每条拒绝记录通过 stderr 输出完整 JSON 审计，最后通过 stdout 输出汇总 JSON。

`settlement_export/job.py` 启动转换程序，取得结果和审计，保存 `summary.json`、`worker.log`，写入 `job_completed` 后退出。正常基线使用 `child.communicate()` 收集两个输出流并等待退出。

事故版本唯一的业务故障是把上述操作换成依次读取 stdout、读取 stderr、等待退出：

```python
result = child.stdout.read()
diagnostics = child.stderr.read()
child.wait()
```

2026-10-10 的目录重构保留这段故障逻辑和相同业务输入。随后的环境修复把 Docker 中的 Linux 固定为比赛环境：Windows 和 macOS 只作为 Docker Desktop 宿主机。栈快照从宿主机相关的 `SIGUSR1` 改成标准库诊断线程监听共享请求文件，两个终端可以通过 Compose 使用同一入口。该改动服务于环境与观察，不改变业务输出收集顺序或故障因果链。

## 触发条件与因果链

small 有 12 行，其中 3 行拒绝，完整审计为 2541 字节；daily 有 2400 行，其中 600 行拒绝，完整审计为 509327 字节。触发条件是未消费的诊断数据超过当前平台管道可容纳的数量，不是固定的记录编号或跨平台缓冲容量。

1. 父进程建立两根输出管道，启动转换进程。
2. 父进程先把 stdout 读取到 EOF；此时子进程尚未完成，stdout 写端仍开放。
3. 子进程处理拒绝行时持续写 stderr，而父进程尚未读取这个通道。
4. stderr 空间不足，子进程阻塞在审计写入，无法继续处理、输出汇总或退出。
5. 父进程等待 stdout 结束，子进程等待 stderr 被消费，形成等待环。
6. 结果归档和完成日志位于输出收集之后，因此现场只有部分业务产物和启动记录。

small 的诊断量没有填满管道，故它能够结束；这不能证明输出收集方式正确。`-u` 和 `flush=True` 已用于语言层刷新，它们不能让接收方自动读取。8 秒后停止是运行脚本的保护行为，延长时限不会解除等待环。

## 证据与调查路径

合理的初始假设包括输入处理、计算量、磁盘写入、结果解析和结束流程异常。先重现 small/daily 的差异，再用实际进程、输出和栈区分这些解释。

持续现场中，分别执行 `docker compose run --rm challenge stack daily job` 和对应的 `exporter` 命令：父进程栈落在 stdout 读取处；转换进程栈落在向 stderr 打印审计的位置。请求容器通过共享运行目录与任务容器通信，不依赖宿主机 PID 或信号。将这些位置与通道所有者、容量和 EOF 条件连接起来，才能解释等待关系。低 CPU 本身不足以确诊。

可以保持输入不变，直接运行转换程序并把 stderr 归档到普通文件，或尝试同时消费两条流。对照能说明输出连接方式影响完成状态；还需结合代码、真实栈以及保留完整审计的修复验收形成证据链。参赛者采用其他成立的路径同样有效。

## 修复与工程取舍

最小修复如下，其余业务行为不变：

```diff
-            result = child.stdout.read()
-            diagnostics = child.stderr.read()
-            child.wait()
+            result, diagnostics = child.communicate()
```

本题输出量有界，约半 MB 审计可以由 `communicate()` 收集到内存。现实任务若输出可能无界，可将 stderr 直接连接到审计文件，或持续并发消费到文件，并考虑磁盘错误及失败记录的保留。当前题目不需要额外异步框架或调度层。

删除审计、改变支持币种或减少输入可能改变触发，却违反业务要求。合并两个流也会破坏 stdout 中独立汇总 JSON 的通道契约。超时与进程清理只能限制影响，不能代替根因修复。

权威依据：[subprocess 输出收集](https://docs.python.org/3.9/library/subprocess.html#subprocess.Popen.communicate)、[文本流读取](https://docs.python.org/3.9/library/io.html#io.TextIOBase.read)、[faulthandler 栈输出](https://docs.python.org/3.9/library/faulthandler.html#faulthandler.dump_traceback)、[POSIX read](https://pubs.opengroup.org/onlinepubs/9799919799/functions/read.html)、[POSIX write](https://pubs.opengroup.org/onlinepubs/9799919799/functions/write.html)。接口语义与实际环境验证分别保留。

## 提示与复盘

按请求逐级给出，不一次连发：

1. 方向：确认未完成的是业务处理、结果归档还是退出收尾；区分进程存在与正在计算。
2. 证据：取得两个业务进程的 Python 栈，说明各自继续执行需要什么条件。
3. 机制：检查两个独立标准流的缓冲、消费行为和 EOF 条件。

评分沿用手册：根因 30、因果机制 20、证据链 15、假设 10、实验 10、系统模型 10、修复 5。只背出 `communicate()`，没有等待关系和实测证据，不能获得完整机制与证据分。

赛后从正常系统、故障注入和因果链开始，将关键证据放回对应状态，再回看参赛者的假设、实验和判断更新。后续值得覆盖的行为是：诊断输出较多时仍保持完整业务输出，子进程失败时保留记录，以及中止任务后确实完成清理。

本题覆盖 Python 的逐行迭代、字典记录、整数累计、上下文管理与文件生命周期，以及进程、标准流、缓冲、EOF 和跨进程等待。书籍尚未提供，本题不标注《流畅的 Python》的具体章节来源。

## 验证与历史资料

当前 Docker 环境验证见 [evidence/2026-10-10/docker-validation.md](evidence/2026-10-10/docker-validation.md)。此前目录重构的原始验证记录保留在 [validation.json](evidence/2026-10-10/validation.json)，其中的平台和命令只对应 Docker 化之前的版本。

已验证事故版本的小/大批次差异、标准验收入口、容器间栈请求、活动任务清理保护、超时回收、源码挂载、正常基线，以及验收对审计缺失和参考材料篡改的拒绝。Linux 镜像是唯一比赛环境，仓库工作流持续构建并运行该镜像。交付恢复为事故源码，运行目录清空。

原始 2026-10-09 故障真相和环境记录保存在 `archive/`，内容按原样保留。历史路径、源码行号和校验值仅对应当时版本；当前参赛者应使用项目 README 中的新入口。历史记录不应被改写成当前版本已通过的证明。
