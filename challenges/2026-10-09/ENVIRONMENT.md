# 运行环境与准备状态

日期：2026-10-09（UTC+8）。状态：赛前准备；未开始、未计时、未提交、未评分。

## 实测组合

- 系统：macOS 27.0.1，arm64。
- Python：3.9.6 (default, Aug 25 2026, 21:26:21) ；执行文件 `/Applications/Xcode.app/Contents/Developer/usr/bin/python3`。
- 依赖：仅标准库，无第三方包、容器、网络服务或数据库。
- 最低使用条件：macOS、Python 3.9+；程序使用 POSIX 进程组与 SIGUSR1。
- Linux 也具备相应接口，但本次没有在 Linux 或其他 Python 版本实测；Windows 不在本题支持范围。

## 验证范围

已实际运行正常基线与故障环境，验证两组输入、复现、按外部行为验收、栈快照、Ctrl-C 清理和重置。具体诊断、正常代码和泄题性记录仅保存在分离的赛后 Ground Truth 中。初始事故日志来自真实运行。所有运行保护均已停止，本题没有后台服务。

8 秒是运行保护时限，赛题时限为 45 分钟，待你主动开始才计时。机器负载和其他平台可能影响运行时间；本次验证范围仅为以上组合。

## 原始事故文件校验值

用于核对自己是否还持有原始事故材料，不包含正常版本或修复。

| 文件 | SHA-256 |
| --- | --- |
| `job.py` | `a45023161b9fe4006b787ceb2ca106502482fae95c65ba049f8d9dc45e62cb2c` |
| `exporter.py` | `4e197e0072e2333ac596f06d99a2f8d086c6dc15d98564c6e0905118b9b58164` |
| `lab.py` | `dfe9b5cd2c5f67127f6391d07ea912cdcd42c8b8481e863afa58963187b1ad1c` |
| `verify.py` | `922c6ad2b2158b9a6c403c7b97b384cbfe7ec8e2456858b0b0e763cdeb123468` |
| `config.json` | `d94e5cadbd391e33957dfdb886f73049fb924ca998cd7fd7901c3a746fa7d214` |
| `data/small.csv` | `670473b92cf0073fe6abacb4e875aec229ee89fdbb54e786555d49a06778b7cc` |
| `data/daily.csv` | `db7dfb1fcf363924d310c01f0b3479b18eb89adfa5e43e2e46d50e9c2694060b` |

机器可读版本见 `environment.json`。`runtime/` 是重置可清理的输出，`evidence/initial/` 保留初始观察。
