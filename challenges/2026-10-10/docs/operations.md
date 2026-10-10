# 运行指南

## 赛前准备

Windows/macOS 安装并启动 Docker Desktop（Windows 使用 Linux containers）；Linux 使用 Docker Engine 和 Compose 插件。无需宿主机 Python 或云服务器。

```sh
git clone https://github.com/MerlinSMQWQ/debug-challenges.git
cd debug-challenges/challenges/2026-10-10
```

Linux 首次生成挂载目录的用户映射，避免权限问题。Windows/macOS 使用默认用户，不需要此步。

```sh
printf 'CHALLENGE_UID=%s\nCHALLENGE_GID=%s\n' "$(id -u)" "$(id -g)" > .env
```

构建和检查帮助可以在开始前完成：

```sh
docker compose build
docker compose run --rm challenge --help
```

命令不启动比赛计时。准备好后自行明确开始，再阅读事故说明并调查。

## 调查时运行

```sh
docker compose run --rm challenge preview
docker compose run --rm challenge export
```

默认输入为 `data/morning.json`，默认产物为 `runtime/morning/`。输入 JSON 是由记录组成的数组，字段为 `order_id`、`sku`、`quantity`。你可以建立自己的脱敏实验输入，并用 `--input` 和 `--output` 选择路径。没有实际订单或个人资料。

每次实验建议使用新的输出目录，以免把旧文件当成此次成功产物。正式输入、初始证据和测试文件保持原样；诊断和修复只改业务源码。初始记录位于 `evidence/initial/`，可只读查阅。

POSIX shell 可以保存完整输出与退出码：

```sh
mkdir -p runtime
docker compose run --rm challenge export --output runtime/experiment-01 > runtime/experiment-01.log 2>&1
echo $?
```

Windows PowerShell 可直接运行 Docker 命令，退出码看 `$LASTEXITCODE`，日志用 `*> runtime/experiment-01.log` 保存；先创建 `runtime` 目录。

## 修复后的业务验收

```sh
docker compose run --rm --entrypoint python challenge -m unittest tests.test_acceptance -v
```

此程序检查输入输出、空批次和序列接口契约，不评分、不提交、不计时。事故版本未修复时验收失败是正常现象。每个子进程最多运行 5 秒，这是运行保护，与 20 分钟比赛时限分别记录。

所有命令结束后没有后台服务。`runtime/` 可自行归档后删除；保留你需要提交的实验记录。不要删除别人的目录或使用旧题的清理命令清理本题。
