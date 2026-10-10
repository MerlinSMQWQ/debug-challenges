# 赛前知识：让自定义对象参与 Python 操作

这份材料提供调查需要的语言规则。只要认识类、函数、列表和异常，就可以开始；示例与赛题业务无关。

## 1 对象通过协议接入语言

Python 中的 `len(x)`、`x[i]`、`for value in x` 有共同规则。自定义类型实现相应的特殊方法，就能接入这些操作，不必让调用者知道内部数据怎么保存。

| 操作 | 对自定义类型使用的接口 |
| --- | --- |
| `len(x)` | 类上的 `__len__`，返回非负整数 |
| `x[i]` | 类上的 `__getitem__`，参数为下标 |
| `iter(x)`、`for` | 优先使用 `__iter__`；未实现时可使用下面的序列遍历规则 |

特殊方法写在类中，名称前后各有两个下划线。日常调用用 `len(x)` 等语言接口。内部保存列表是一种组合方式：把相应操作委托给列表，就能沿用列表已经实现的规则。这里不要求继承抽象基类，也不要求实现全套容器方法。

## 2 长度和下标

长度为 `n` 的序列，普通正下标为 `0` 到 `n-1`。有效下标返回对应元素，超出范围应抛出 `IndexError`；参数类型不合适通常抛出 `TypeError`。`None` 是一个普通 Python 值，可以是数据本身，和异常不同。

Python 列表也支持负下标和切片：`values[-1]` 为最后一项，`values[:2]` 为前两项组成的新列表。空列表长度为 0，切片可以为空；对空列表取单个元素会越界。

```python
values = ["red", "green"]
print(len(values))      # 2
print(values[0])        # red
print(values[-1])       # green
print(values[:1])       # ['red']
# values[2] 会抛出 IndexError
```

## 3 遍历怎样结束

`for` 通过迭代接口逐个取值，迭代结束时停止。若对象没有 `__iter__`，但提供 `__getitem__`，Python 可以从下标 0 开始，依次请求 1、2……，直到请求抛出 `IndexError`。这个过程不靠预先读取 `len(x)` 来确定终点。

返回一个值表示“取得一项”；抛出规定的异常表示“这一操作不能继续”。在序列遍历的适配过程中，`IndexError` 会转成迭代结束的信号 `StopIteration`。业务循环不会拿到这个结束异常。其他异常通常继续向外传播，不会自动当成正常结束。

```python
class Colors:
    def __init__(self):
        self._values = ["red", "green"]

    def __len__(self):
        return len(self._values)

    def __getitem__(self, index):
        return self._values[index]

palette = Colors()
print(len(palette))
for color in palette:
    print(color)
```

自己预测这段独立示例的输出，再用允许的解释器检查。赛前学习可以讨论这份示例；开始挑战后，当前事故的分析应由参赛者完成。

## 4 文件、异常与证据

本地导出程序常先写临时文件，完整成功后再改成正式文件名。看到临时文件或“已处理”日志，不代表整次任务完成。异常会中断后续语句，`with` 仍会关闭文件；关闭文件和业务成功是两件事。

看日志时区分实际记录与推测。比较两个命令、控制输入大小、打印变量或在解释器中单独检查一个对象，都是基础实验。实验前写下预测，实验后保留输出；每次尽量只改变一个条件。

## 5 工具最小用法

运行和查看 CLI：`docker compose run --rm challenge --help`。运行解释器：`docker compose run --rm --entrypoint python challenge`。查看文本可用编辑器、`cat` 或 shell 文件搜索；写临时 Python 脚本后，在同一容器里运行。使用 Ctrl-C 停止自己启动的命令。运行指南提供日志保存和业务验收命令。

本题开放工具 B：shell、Python 解释器、标准库、编辑器和基础文件命令；没有必须使用的高级调试器。官方资料可用于查规则，不能将当前事故交给搜索引擎或 AI 分析。

## 官方依据

- [Python 3.13 数据模型：模拟容器类型](https://docs.python.org/3.13/reference/datamodel.html#emulating-container-types)：长度、下标及非法下标的异常契约。
- [Python 3.13 内置函数 iter](https://docs.python.org/3.13/library/functions.html#iter)：迭代协议与序列协议的回退。
- [Python 3.13 for 语句](https://docs.python.org/3.13/reference/compound_stmts.html#the-for-statement)：循环取值和结束方式。

以上为独立讲解，不复制原书正文；出题者已读原书相应范围并核对官方规则。
