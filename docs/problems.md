# 题目目录

本仓库 **不带题**。评测机磁盘上的 `problems/` 由管理员用 zip 导入（网页「题库 → 本机导入」），或把符合下表的目录拷进去后点「只重新加载磁盘」。

## 类型与语言（和评测对齐）

机器词表是 [`rules/types.yaml`](../rules/types.yaml)。评测机只读这份 YAML。

允许的签名类型：叶子 `int` / `long` / `float` / `bool` / `str`，以及一层、两层 `List[T]`（含 `List[float]`、`List[bool]`）。不要三层列表、不要链表/树节点。

当前这些类型在 YAML 里对八种语言都是 `langs: all`，所以默认下拉里会有 Python 3、C、C++20（id 仍是 `cpp17`）、JavaScript、TypeScript、Go、Rust、Zig——再和主机 `GET /api/languages` 求交。某类型将来若某语言还不能 wrap，该语言**不会出现在本题下拉**，不是灰项 `NA`。

值按签名类型与参数顺序写入 `meta.yaml`，见 [`rules/files.md`](../rules/files.md)：

| 键 | 适用 |
| --- | --- |
| `scale_min` / `scale_max` | 输入规模：图有几个点，或数组/字符串有多长。没有数组、字符串、图时不写 |
| `bounds` | 每个参数自己的数或字符：整数/小数写该参数的 `min`/`max`，字符串写 `charset`。数字从题面约束抄，对照 [`rules/files.md`](../rules/files.md)「每个参数上出现的数或字符」。边列表前「有几个点」写在 `scale_min` / `scale_max` |

`meta.languages` 是可选白名单（如只允许 `python3`）。出题流水线默认不要写；缺省 = 该签名能 wrap 的全部语言。网页下拉 = 本题列表 ∩ 主机已实现且 `detect()` 为真的适配器。提交一种不在列表里的语言会 400「本题不支持该语言」。

## 添加一道题

1. 选定 `slug`：只含小写字母、数字和连字符。目录名必须等于 slug。
2. 目录里写入下表所列文件（付费题包已打好）。
3. 管理员登录 `:8080` →「题库 → 本机导入」上传 zip。按钮见 [admin.md](admin.md)。

不要把 `tests.jsonl` 提交进本仓库。

## 目录结构

```text
problems/
  catalog.md          # 已出题表；脚本生成，不要手改
  <slug>/
    meta.yaml
    statement.md
    signature.yaml
    tests.jsonl
    starter/
      python3.py
      c.c
      cpp17.cpp
      javascript.js
      typescript.ts
      go.go
      rust.rs
      zig.zig
```

| 文件 | 必填 | 说明 |
| --- | --- | --- |
| `catalog.md` | 是（题库根） | 已出题表。由 `mcp__leet__write_catalog` 在 commit 前生成，不要手改 |
| `meta.yaml` | 是 | 标题、难度、时限、内存、标签 |
| `statement.md` | 是 | 题面（Markdown），显示在题目页左侧 |
| `signature.yaml` | 是 | 类名、方法名、参数、返回类型、比较方式 |
| `tests.jsonl` | 是 | 测试集，一行一个 JSON |
| `starter/python3.py` | 建议 | 打开题目时 Python 编辑器的初始代码 |
| `starter/c.c` | 建议 | C 初始代码（力扣式自由函数） |
| `starter/cpp17.cpp` | 建议 | C++ 初始代码 |
| `starter/javascript.js` | 建议 | JavaScript 初始代码 |
| `starter/typescript.ts` | 建议 | TypeScript 初始代码 |
| `starter/go.go` | 建议 | Go 初始代码 |
| `starter/rust.rs` | 建议 | Rust 初始代码 |
| `starter/zig.zig` | 建议 | Zig 初始代码 |

## meta.yaml

```yaml
slug: two-sum
title: 两数之和
difficulty: easy
time_limit_ms: 2000
memory_limit_mb: 256
tags:
  - array
  - hash
```

- `difficulty`：`easy`、`medium` 或 `hard`。
- `time_limit_ms`：用户程序运行时限（毫秒），建议 1000–5000。
- `memory_limit_mb`：运行内存上限（MB）。编译阶段不使用此值。
- `tags`：小写英文 id，1～3 个。题库页按知识点筛选；中文名在 `frontend/src/tags.ts`。
- `scale_min` / `scale_max`：输入规模的下界/上界。图题写点数；有数组或字符串时写长度。纯整数/小数/`bool` 不写。缺了由 `mcp__leet__fix_format` 按签名补（需要写时才补 `1` / `100000`）。
- `bounds`：每个参数自己的数或字符，键是 `signature.yaml` 的 `name`。整数/小数写该参数在题面里的全局 `min`/`max`，字符串写 `charset`，抄法见 [`rules/files.md`](../rules/files.md)「每个参数上出现的数或字符」。边列表前「有几个点」写在 `scale_min` / `scale_max`。缺了工具不补。
- `languages`：可选。本题允许的语言 id 列表。缺省不要写。

## statement.md

Markdown 题面。`# 标题` 下直接写说明（参数和返回值写进这段），再接 `## 示例` 和 `## 约束`。用户不读写标准输入，只实现函数。形状由 `mcp__leet__fix_format` 收齐，与 `{根}/rules/files.md` 的 statement.md 中的样例相同。

## signature.yaml

评测机按此签名注入驱动并调用用户代码。

```yaml
class_name: Solution
method: twoSum
params:
  - name: nums
    type: List[int]
  - name: target
    type: int
return_type: List[int]
compare: any_order
```

- Python / C++：用户实现 `class Solution` 中的方法，方法名与 `method` 一致。
- C：力扣式自由函数，无 `class Solution`。`List[int]` / `List[long]` / `List[float]` / `List[bool]` 参数展开为指针加长度（`int*` / `long long*` / `double*` / `bool*` 加 `numsSize`）；返回数组时再加 `int* returnSize`，返回值须 `malloc`。`List[List[T]]` 展开为 `T** matrix, int matrixSize, int* matrixColSize`，返回二维再加 `int** returnColumnSizes`。`str` 为 `char*`，`List[str]` 为 `char**` 加长度。yaml `long` 在 C/C++ 为 `long long`，yaml `float` 在 C 为 `double`，Python 注解仍为 `int` / `float`。
- `params` 顺序必须与 `tests.jsonl` 里 `args` 的顺序一致。
- `compare`：`exact` 表示按结构对位比较；`any_order` 表示顶层列表元素顺序无关（如下标数组）。浮点（含嵌在列表里的）一律绝对/相对误差约 `1e-6`，机检与评测相同，不要求与题面打印值逐 bit 相等。

支持的 `type` 见上一节与 [`rules/types.md`](../rules/types.md)。默认用 `int`；仅答案或参数会超 32 位有符号整数时用 `long`。C 的二维按力扣约定展开为指针加行列数。链表、二叉树尚未支持。三层列表不支持。

## tests.jsonl

公开样例必须写在文件前部：所有 `hidden: false` 在所有 `hidden: true` 之前。打开题目和「测试」读到第一条隐藏行即停。评测机如何读该文件见 [server.md](server.md)。

每行一个 JSON 对象，UTF-8，行与行之间不要逗号。

```json
{"args":[[2,7,11,15],9],"expected":[0,1],"hidden":false}
{"args":[[3,2,4],6],"expected":[1,2],"hidden":false}
{"args":[[1,2,3,4,5,6,7,8,9,10],19],"expected":[8,9],"hidden":true}
```

- `args`：参数列表，与 `signature.params` 一一对应。
- `expected`：期望返回值，类型与 `return_type` 一致。
- `hidden: false`：该测例失败时，网页展示输入、期望与实际输出。
- `hidden: true`：只提示第几号测例失败。正式数据放隐藏测例。

公开测例 2～3 条，与题面示例一致。提交用隐藏测例不少于 20 条；每个参数顶到它在 `bounds` 的两端，顶点编号和 `k` 还要落在本条规模内。口径见 [`rules/tests.md`](../rules/tests.md)，写法见 [design-problem-tests](../.cursor/skills/design-problem-tests/SKILL.md)。

## starter

与力扣相同：只给出类/函数签名，函数体留空，不要写 `return {}`、`return false` 等占位返回值。Python 空缩进块是语法错误，提交空 starter 得到 `CE` 即可。

两处都可以按 `signature.yaml` 生成，**不要互相 import**：

| 在哪 | 谁写 | 代码 |
| --- | --- | --- |
| 出题电脑 | `mcp__leet__fix_format` | `.qwen/tools/write_starters.py` |
| 评测机管理页 | 「按文件上传」成功后的「生成 starter」 | [`backend/app/services/starters.py`](../backend/app/services/starters.py) |

不要手抄。管理页生成只读签名，不读 `tests.jsonl`。

不要在用户代码里定义 `main`，否则与驱动中的 `main` 冲突，结果为 `CE`。

Python：

```python
class Solution:
    def twoSum(self, nums: list[int], target: int) -> list[int]:
        
```

C（驱动已包含 `json.h`，其中有 `stdbool.h` / `stdlib.h`）：

```c
/**
 * Note: The returned array must be malloced, assume caller calls free().
 */
int* twoSum(int* nums, int numsSize, int target, int* returnSize) {
    
}
```

C++（驱动已包含 `iostream` 等常用 STL 与 `using namespace std;`，不要再 `#include <bits/stdc++.h>`）：

```cpp
class Solution {
public:
    vector<int> twoSum(vector<int>& nums, int target) {
        
    }
};
```

## 在评测机磁盘上直接改题

适用于临时改一题、且立刻要在本机生效：

```bash
cd ~/leet-hub          # 实际克隆路径；WSL 用 Linux 家目录，不要 /mnt/c
# 编辑 problems/<slug>/ 下文件
sudo systemctl restart local-leet
```

或管理员登录网页后在「题库 → 远程同步」点「只重新加载磁盘」。改完后若需与 GitHub 一致，在能推送的电脑上把同一改动提交并 `git push`。

网页「题库」写入的也是评测主机上的 `problems/`，效果与直接改磁盘相同，同样需要再推送到 GitHub 才能成为仓库真源。
