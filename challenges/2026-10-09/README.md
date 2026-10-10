# 门店结算导出 · 测试题 #000

本题现作为测试题，历史编号为 #001。日期 `2026-10-09`、工程路径和原网站链接继续有效；已有答卷、成绩和历史验证记录保留，不改写或重新评分。正式 #001 为 `2026-10-10` 的新题。

这是一个用 Python 编写的本地结算工具。运营人员提供门店发票 CSV，工具根据币种配置生成结算记录、金额汇总和拒绝审计。项目只使用标准库，没有网络服务或数据库。

你接手的是一个发生故障的版本。业务背景、已知现象和交付要求见事故说明；调查目标是解释故障发生的过程，并用证据和修复验证自己的判断。

## 开始前怎样阅读

| 顺序 | 材料 | 读完后应当知道什么 |
| --- | --- | --- |
| 1 | [赛前知识](docs/pre_read.md) | Python 程序怎样处理文件、启动进程并交换数据 |
| 2 | [运行指南](docs/operations.md) | 环境要求、启动命令、日志位置、观察和清理方式 |
| 3 | [事故说明](docs/incident.md) | 发生了什么，正常结果应满足哪些业务要求 |
| 4 | [比赛规则](docs/rules.md) | 可用工具、时限、提示、提交和评分方式 |

完成学习和环境检查后，由参赛者明确开始，再进入限时调查。运行脚本只管理程序，不记录比赛开始时间。当前交付仍处于赛前准备阶段。

本题综合难度为 **Medium**，知识难度 ★★☆☆☆、推理难度 ★★★☆☆；采用系统调试工具范围（手册 C 档），比赛时限 **45 分钟**。

## 项目怎样运行

在仓库根目录进入本项目：

```sh
cd challenges/2026-10-09
docker compose build
docker compose run --rm challenge --help
```

参赛环境是题目提供的 Linux 容器。Windows 和 macOS 安装 Docker Desktop，Linux 安装 Docker Engine 与 Compose 插件即可；不需要宿主机 Python、云服务器或额外依赖。已实测的镜像和范围见[验证记录](docs/validation.md)。

开始调查后，用运行脚本执行样例和日结批次：

```sh
docker compose run --rm challenge reset
docker compose run --rm challenge run small
docker compose run --rm challenge run daily
```

输出分别写入 `var/runs/small/` 和 `var/runs/daily/`。脚本默认在 8 秒后停止尚未结束的任务，超时退出码为 `124`；这是运行保护时限。比赛的 45 分钟需要另外记录。

修复后的业务验收使用 Python 自带的测试工具：

```sh
docker compose run --rm challenge reset
docker compose run --rm --entrypoint python challenge \
  -m unittest discover -s tests -p "test_acceptance.py" -v
```

验收检查完整导出记录、计数、金额、拒绝审计和任务完成记录。事故版本的验收失败是待调查的现场；修复后两组测试都应通过。每次清理前请先保存需要保留的运行记录。

## 文件放在哪里

```text
.
├── settlement_export/       # 业务代码：任务调度与发票转换
├── config/                  # 支持币种配置
├── data/
│   ├── samples/             # 小批次样例
│   └── batches/             # 日结批次输入
├── scripts/                 # 启动、运行保护和清理
├── tests/                   # 外部行为验收与参考材料校验值
├── docs/                    # 学习、运行、事故与比赛说明
├── evidence/initial/        # 一次真实事故运行的初始记录
├── Dockerfile、compose.yaml # 统一的 Linux 参赛环境
├── pyproject.toml           # 容器内 Python 版本与依赖声明
└── var/runs/                # 运行时生成的文件，不纳入版本控制
```

`settlement_export/job.py` 是任务入口，调用 `settlement_export/exporter.py` 进行转换；`settlement_export/diagnostics.py` 提供容器间可请求的调用栈快照。Compose 会把当前项目挂载进容器，所以参赛者修改源码后无需重新构建镜像。运行脚本负责启动和回收进程，验收测试独立计算期望结果。

可以在 `notes/` 保存自己的调查记录、备份和实验副本，该目录不会进入版本控制。`reset` 只清空 `var/runs/`，不会恢复你的源码修改。

赛前请勿阅读或搜索仓库中的 `organizer/`，其中保存答案、修复和出题验证记录。提交并结束挑战后，再按[比赛手册](../../Debug%20挑战赛手册.md)复盘。
