# 🛡️ Regex-Safety: 纯 Python 手写正则安全分析器

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)]()

一个完全从零手写、零第三方依赖的 ReDoS（正则表达式拒绝服务）静态检测与安全改写工具。

## 🎯 为什么写这个项目？
市面上大部分 ReDoS 检测工具，通常是基于字符串匹配的启发式报警（比如看到 `(a+)+` 就报警），误报率极高，且无法给出精确的安全修复建议。
本项目使用纯 Python，手写了正则 AST 解析器、Thompson NFA 引擎、DFA 引擎，通过图同构算法在数学层面证明改写前后的等价性，从根本上解决正则回溯爆炸问题。

## 🏗️ 核心特性与架构
本项目没有任何“调包”行为，所有底层数据结构全部手写实现：

- `parser.py`：手写递归下降解析器，将正则表达式转化为抽象语法树（AST）。
- `risk.py`：基于 AST 遍历，精准定位嵌套量词、歧义分支等 ReDoS 风险节点。
- `nfa.py`：基于 Thompson 构造法生成 NFA，并在 `epsilon` 边上打上标签。实现了带捕获组（Capture Groups）的 DFS 状态机模拟、滑动窗口全局搜索、以及取反字符集（`[^a-z]`）支持。
- `dfa.py`：实现 NFA 到 DFA 的子集构造法（Subset Construction），并统计状态数。
- `rewrite.py`：对危险结构进行安全降级（如将 `(a+)+` 改写为 `a+`），并穿透捕获组括号。
- `equivalence.py`：结合样本随机对拍与 **DFA 图同构算法（Isomorphism）**，严格证明改写前后的数学等价性。

## 📊 核心实测数据 (ReDoS 免疫)
我们用经典恶意正则 `(a+)+b` 和 `25个a + '!'` 的文本进行压测：

| 执行引擎                    | 耗时         | 结果                                          |
| :-------------------------- | :----------- | :-------------------------------------------- |
| Python 原生 `re` (回溯引擎) | 1.6833 秒    | 极度危险，输入稍长会导致 CPU 100% 和拒绝服务  |
| 本项目 NFA 引擎             | 0.0001822 秒 | 毫秒级完成，安全（基于 DFS 模拟，无回溯爆炸） |
| 本项目 AST 改写后 (`a+b`)   | 0.0000904 秒 | 完美规避风险，速度提升近万倍                  |

*(注：实测本引擎在同场景下比 Python 原生 `re` 快了 **9,238 倍**)*

### 📉 DFA 状态膨胀测试
在实现子集构造法时，清晰验证了 DFA 在面对复杂正则时的状态爆炸问题：

| 测试正则             | NFA 状态数 (线性增长) | DFA 状态数 (指数爆炸) |
| :------------------- | :-------------------- | :-------------------- |
| `(a\|b)*`            | 10                    | 3                     |
| `(a\|b)*a(a\|b){5}`  | 62                    | 65                    |
| `(a\|b)*a(a\|b){10}` | 102                   | **2049**              |

## 🚀 使用演示

运行命令：
```bash
python -m regex_safety.cli "(a+)+b"