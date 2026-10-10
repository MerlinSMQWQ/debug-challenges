# 赛前知识：从 Python 程序到运行中的任务

本题需要把 Python 代码、进程状态和文件输出联系起来。下面补齐调查所需的基础；可以在计时前阅读、练习这些一般机制。具体事故见[事故说明](incident.md)。

## 1. 一次数据转换有哪些状态

CSV 文件有表头，每行是一条记录。`csv.DictReader` 按表头把字段名映射到字符串值；例如 `row["cents"]` 仍是字符串，需要转换后才能参与整数运算。逐行迭代时，当前记录、计数和累计金额由执行循环的进程持有。

```python
import csv

with open("invoices.csv", newline="", encoding="utf-8") as source:
    for row in csv.DictReader(source):
        amount_cents = int(row["cents"])
```

`with` 让文件资源的生命周期与代码块对应，离开代码块时关闭文件。写入文件时，内容可能经过缓冲；文件已经出现，不能证明全部行已写完。业务完成还需要核对记录、汇总和程序的结束状态。

本题使用整数分表示金额，避免在货币累计中引入浮点误差。CSV 负责保存完整记录，JSON 负责表达汇总和逐条审计。相关接口见 [csv 官方文档](https://docs.python.org/3.9/library/csv.html)和[文件读写说明](https://docs.python.org/3.9/tutorial/inputoutput.html#reading-and-writing-files)。

## 2. 启动另一个程序以后，谁在执行

一个进程拥有自己的执行位置、内存和打开的资源。任务入口启动转换程序后，两者分别执行；启动成功只说明子进程已经创建。它是否仍在运行、是否退出、业务是否正确完成，需要分别观察。

Python 的 `subprocess.Popen(...)` 返回一个子进程对象。`pid` 标识这个进程；`poll()` 在进程还未退出时返回 `None`，退出后返回退出码；`wait()` 等待进程退出。退出码 `0` 是程序报告成功的方式，业务输出仍需要独立核对。[subprocess 官方文档](https://docs.python.org/3.9/library/subprocess.html#popen-objects)

本项目的调度程序负责启动转换程序、归档记录并保存汇总。转换程序负责读取发票、筛选记录并累计金额。源文件说明代码在哪里；PID 说明当前观察的是哪一次运行。

## 3. 程序之间怎样传递结果

进程通常有标准输入、标准输出和标准错误三个通道，对应文件描述符 `0`、`1`、`2`。文件描述符是访问已打开资源的编号；这些资源可以是终端、文件或管道。

标准输出（stdout）与标准错误（stderr）是独立通道。stderr 也可用于诊断和审计，出现内容并不必然意味着任务失败。例如：

```python
import sys

print('{"count": 1}')
print("processed one record", file=sys.stderr)
```

调用方可以使用 `stdout=PIPE` 或 `stderr=PIPE`，把对应的子进程输出接到可读取的管道。此时子进程写入，父进程持有读端。判断数据在哪里，需要看调用方怎样连接这些资源。[标准流说明](https://docs.python.org/3.9/library/sys.html#sys.stdout)、[PIPE 的定义](https://docs.python.org/3.9/library/subprocess.html#subprocess.PIPE)

## 4. 写入、刷新和读取之间有什么区别

一次输出通常先经过 Python 的流缓冲，再进入操作系统管理的资源，最后由接收方读取。`flush=True` 请求刷新 Python 层的缓冲；`python3 -u` 让标准输出和标准错误使用无缓冲模式。它们描述的是发送侧的行为，不能证明接收方已经读取。[Python 标准流的缓冲规则](https://docs.python.org/3.9/library/sys.html#sys.stdout)

管道是有限容量的字节队列，不保存“这一行”或“这条消息”的边界。读取和写入的分块不一定相同。在默认阻塞模式下，读取需要有可读数据，写入需要有可用空间；条件暂时不满足时，操作可以等待。

流结束标记 EOF 也有自己的条件：所有写端已关闭，且队列中的数据已读完，读取才得到 EOF。当前没有数据，和以后不会再有数据，是不同的状态。Python 文本流的 `read(n)` 最多读取 `n` 个字符；不指定长度的 `read()` 会一直读取到 EOF。[Python I/O 文档](https://docs.python.org/3.9/library/io.html#io.TextIOBase.read)、[POSIX read](https://pubs.opengroup.org/onlinepubs/9799919799/functions/read.html)、[POSIX write](https://pubs.opengroup.org/onlinepubs/9799919799/functions/write.html)

这些是一般规则，不说明本题现场必然处于哪种状态。缓冲容量因平台而异，本题不要求记住某个固定数值。

## 5. 把观察放回它所属的层

| 要观察的状态 | 由谁持有或管理 | 可以取得的证据 |
| --- | --- | --- |
| 当前执行到哪段 Python 代码 | 对应业务进程 | 当前调用栈 |
| 进程是否存在、是否消耗 CPU | 操作系统 | PID、进程状态、CPU 占用 |
| 哪些资源已打开 | 进程与操作系统 | 打开的文件和通道 |
| 已处理记录与业务结果 | 转换程序及输出文件 | CSV、汇总、审计 |
| 任务启动、归档和结束 | 调度程序 | 任务日志与退出码 |

低 CPU、某个文件已出现、某条日志已经打印，都只说明一部分状态。建立解释时，要说清楚当前操作等待什么、继续执行的条件是什么、由谁改变这个条件，再用现场证据核对。

本题提供了 Python 调用栈快照：给实际业务 PID 发送 `SIGUSR1` 后，程序会把当前栈写入独立文件并继续运行。工具用法见[运行指南](operations.md#观察正在运行的任务)；接口语义见 [faulthandler 官方文档](https://docs.python.org/3.9/library/faulthandler.html#faulthandler.register)。

读完后，确认自己能区分：启动与完成、文件存在与写入结束、刷新与接收、暂时无数据与 EOF，以及观察事实与故障假设。
