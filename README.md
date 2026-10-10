# Debug Challenges

一个以真实故障调查为核心的挑战赛题库。每道题提供必要知识、事故说明、可运行的工程和赛后故障真相，训练参赛者用观察与实验解释系统为什么出错。

第一次参加，先阅读 [Debug 挑战赛手册](Debug%20挑战赛手册.md)第 1–4 节；准备出题时，再阅读第 5–7 节。

近期按 [参考文档](参考文档.md) 中《流畅的 Python（第2版）》的章节与小节顺序选题。每次根据正文内容确定合适范围，赛题设计继续遵循比赛手册。

## 现有挑战

| 编号 | 项目与事故 | 主题 | 难度 | 时限 |
| --- | --- | --- | --- | --- |
| #001 | [发货清单导出失败](challenges/2026-10-10/README.md) | Python 数据模型、序列协议 | Easy | 20 分钟 |
| #000 | [【测试题】门店结算导出：日结任务未完成](challenges/2026-10-09/README.md) | Python、本地批处理、进程与 I/O | Medium | 45 分钟 |

每道题的 README 是入口，先读赛前知识和运行指南，再读事故与比赛规则，准备好后明确开始调查。工具范围以具体赛题说明为准。

**赛前请勿阅读或搜索 `organizer/`。** 这里保存答案、修复和出题验证记录，提交并结束挑战后用于复盘。

正式序号从 #001 开始；旧题显示为测试题 #000，历史材料中的旧编号不改写。网站与提交以日期识别赛题：`2026-10-09` 与 `2026-10-10` 独立，旧链接、答卷和成绩保留，不迁移或重新评分。

## 运行正式第一题

先阅读[正式 #001 入口](challenges/2026-10-10/README.md)中的赛前知识与规则，再准备 Docker。只使用标准库，唯一业务源码为 64 行。

```sh
git clone https://github.com/MerlinSMQWQ/debug-challenges.git
cd debug-challenges/challenges/2026-10-10
docker compose build
docker compose run --rm challenge --help
```

Linux 首次需按[运行指南](challenges/2026-10-10/docs/operations.md)配置挂载目录用户。构建和帮助不启动比赛计时；准备好后由参赛者自行明确开始。

## 运行测试题

本题提供完整 Docker 配置。Windows 和 macOS 参赛者使用 Docker Desktop，Linux 参赛者使用 Docker Engine；所有人运行同一个 Linux 赛题镜像，不需要云服务器或宿主机 Python。具体范围见[验证记录](challenges/2026-10-09/docs/validation.md)。

```sh
git clone https://github.com/MerlinSMQWQ/debug-challenges.git
cd debug-challenges/challenges/2026-10-09
docker compose build
docker compose run --rm challenge --help
```

接下来按[项目 README](challenges/2026-10-09/README.md)完成阅读和环境准备。比赛计时由参赛者明确开始后记录，运行工具不自动启动计时。

## 调查与复盘

保留观察、假设、预测、实验、结果和判断更新；正式提交解释根因、因果机制、证据、触发条件与修复。手册按 100 分评价调查质量，用时和提示单独记录。

普通挑战允许查官方规则和工具用法，禁止查本题现成答案或让 AI 代为分析当前故障。赛前可以用 AI 学习一般知识；AI 辅助挑战须明确标记并独立记录成绩。

参赛者材料和工程在 `challenges/` 中按发布日期组织；出题者材料在 `organizer/` 中按相同日期对应。提交并结束挑战后，结合固定故障真相回看自己的证据和判断。

## 网站内容同步

网站读取 GitHub `main` 的公开题目，无需 Mac 常驻。内容更新与整站部署的区别、校验命令和生产启用步骤见 [发布与同步说明](website/README.md)。新题答案与参考修复保持本地隔离，不能加入公开包或强制加入 Git。
