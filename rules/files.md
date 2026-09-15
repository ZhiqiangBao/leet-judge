# R2 · 题目文件

`v2026-09-08`。改完立即生效；子代理只认当前文件。

**读的人**：`author`、`quality`。

## 题目文件夹

`problems/<slug>/` 是一道题的文件夹。`author` 只写这三个文件，按这个顺序写：

```text
problems/<slug>/
  statement.md     # 1. 先出题目
  signature.yaml   # 2. 按 statement.md 填参数名、类型、返回值
  meta.yaml        # 3. 按 statement.md 填身份和约束数字；键看 signature.yaml
```

不要创建或修改 `tests.jsonl`。

1. `statement.md`：先写。标题、参数、返回值、约束、示例都在这里定。输入规模（字符串有几个字符、数组有几个元素、图有几个点），上限见 `{根}/rules/bank.md` 的规模。示例给出的数字必须符合约束。
2. `signature.yaml`：参数名、类型、返回值按 `statement.md`。
3. `meta.yaml`：`title` 抄 `statement.md` 首行；约束里的数字抄 `statement.md`。写哪些键看 `signature.yaml` 的类型和顺序，不要看参数叫不叫 `n`。

## statement.md

先写这份文件。首行是 `# <中文标题>`。标题下直接写说明，把参数和返回值写进这段，再接 2～3 个示例和约束。

- 不要要求从标准输入读入。不要把参考解或 `def solve` 写进 `statement.md`。
- 示例解释只说明这个输出为什么对（哪些计入、哪些不计入）。不要写算法步骤。
- 约束要写两类数。第一类：输入规模。参数全是单独的整数或小数时，只写每个参数能取哪些值。有字符串就写有几个字符（`n = s.length`）；有数组就写有几个元素（`n = nums.length`）；有图就写有几个点（不要写成有几条边）；有网格就写有几行或几列。这些数最大能到多少，见 `{根}/rules/bank.md` 的规模。第二类：每个参数上出现的数或字符。单独给出的整数、字符串能出现哪些字符、数组或格子里每个数、图上的顶点编号。不要写评测机内部用语。
- 示例的「输入」按 `signature.yaml` 的参数从左到右写，逗号隔开，不要写成 `name = ...`。比如两个整数写成 `3, 10`；字符串和整数写成 `"aaabb", 2`；数组和整数写成 `[1, 3, 2, 4], 5`；点数和边表写成 `3, [[0,1],[1,2]]`。
- 有数组、且限制某个元素能用几次时：按下标说（每个下标至多用一次），不要只写「每个数用一次」（同一个值可能出现在多个下标）。
- 示例给出的数字必须符合约束。
- 每个示例写「输入 / 输出 / 解释」三行即可。排版交给 `mcp__leet__fix_format`。

整数参数：

```text
# 区间计数

给定整数 `left` 和 `right`，返回区间里有多少个数。

## 示例

### 示例 1

输入：3, 10
输出：8
解释：3 到 10 一共 8 个数。

## 约束

- 1 <= left <= right <= 10^5
```

字符串：

```text
# 最长连续段

给定小写字符串 `s` 和整数 `k`，返回最长连续段的长度。

## 示例

### 示例 1

输入："aaabb", 2
输出：3
解释：前三个字符是同一段。

## 约束

- 1 <= n <= 10^5（n = s.length）
- s 只含小写字母
- 1 <= k <= n
```

数组：

```text
# 和受限的最多配对数

给你一个整数数组 `nums` 和一个上限 `hi`。把不同下标的两个元素配成一对，要求每对之和不超过 `hi`，每个下标至多用一次。返回最多能配出多少对。

## 示例

### 示例 1

输入：[1, 3, 2, 4], 5
输出：2
解释：下标 0 与 3 配 1+4，下标 1 与 2 配 3+2，两对都不超过 5，计入 2。

### 示例 2

输入：[1, 2, 4, 5, 7, 9], 6
输出：2
解释：下标 0 与 3 配 1+5，下标 1 与 2 配 2+4，计入 2。其余元素与任何数相加都超过 6，不计入。

### 示例 3

输入：[5, 5, 5, 5], 9
输出：0
解释：任意两数之和为 10，超过 9，没有计入的配对。

## 约束

- 1 <= n <= 10^5（n = nums.length）
- 1 <= nums[i] <= 10^6
- 1 <= hi <= 2 * 10^6
```

图：

```text
# 连通点数

给定点数 `n` 和边列表 `edges`，返回连通块个数。

## 示例

### 示例 1

输入：3, [[0,1],[1,2]]
输出：1
解释：三个点连成一块。

## 约束

- 2 <= n <= 50
- 顶点编号从 0 到 n-1
- 0 <= edges.length <= n*(n-1)/2
```

## signature.yaml

| 字段 | 含义 |
|---|---|
| `class_name` | 固定写 `Solution` |
| `method` | 本题函数名，由 `author` 自拟，主编派工不给。用英文驼峰，按动作或返回值起名，例如 `maxPairs`、`twoSum`。不要中文，不要写成算法名（例如不要 `slidingWindow`） |
| `params` | 参数列表，从上到下就是函数参数顺序 |
| `- name` | 参数名 |
| `type` | 类型，默认为 `int`，可取值见 `{根}/rules/types.md` |
| `return_type` | 返回类型，可取值与 `type` 相同，见 `{根}/rules/types.md` |
| `compare` | 怎么比较函数的返回值和期望答案。`exact`：顺序必须一样。`any_order`：返回一组数时顺序可以不同，例如 `[0, 1]` 和 `[1, 0]` 都对。只看返回值，不看输入。返回 `float` 时填 `exact`，误差 1e-6 |

根据题目实际需要，填写符合规定的参数类型，示例如下：

```yaml
class_name: Solution
method: rangeCount
params:
  - name: left
    type: int
  - name: right
    type: int
return_type: int
compare: exact
```

```yaml
class_name: Solution
method: wideProduct
params:
  - name: a
    type: long
  - name: b
    type: long
return_type: long
compare: exact
```

```yaml
class_name: Solution
method: cubicRoot
params:
  - name: lo
    type: float
  - name: hi
    type: float
return_type: float
compare: exact
```

```yaml
class_name: Solution
method: canReach
params:
  - name: ok
    type: bool
return_type: bool
compare: exact
```

```yaml
class_name: Solution
method: longestRun
params:
  - name: s
    type: str
  - name: k
    type: int
return_type: int
compare: exact
```

```yaml
class_name: Solution
method: maxPairs
params:
  - name: nums
    type: List[int]
  - name: hi
    type: int
return_type: int
compare: exact
```

```yaml
class_name: Solution
method: prefixWide
params:
  - name: nums
    type: List[long]
return_type: List[long]
compare: exact
```

```yaml
class_name: Solution
method: scaledMeans
params:
  - name: vals
    type: List[float]
  - name: c
    type: float
return_type: List[float]
compare: exact
```

```yaml
class_name: Solution
method: flipMask
params:
  - name: flags
    type: List[bool]
return_type: List[bool]
compare: exact
```

```yaml
class_name: Solution
method: countLakes
params:
  - name: grid
    type: List[str]
return_type: int
compare: exact
```

矩阵、格子、边的列表都填 `List[List[int]]`。

```yaml
class_name: Solution
method: maxPath
params:
  - name: grid
    type: List[List[int]]
  - name: k
    type: int
return_type: int
compare: exact
```

```yaml
class_name: Solution
method: connectedCount
params:
  - name: n
    type: int
  - name: edges
    type: List[List[int]]
return_type: int
compare: exact
```

```yaml
class_name: Solution
method: wideGridSum
params:
  - name: grid
    type: List[List[long]]
return_type: long
compare: exact
```

```yaml
class_name: Solution
method: matrixMean
params:
  - name: grid
    type: List[List[float]]
return_type: float
compare: exact
```

```yaml
class_name: Solution
method: closedRooms
params:
  - name: blocked
    type: List[List[bool]]
return_type: int
compare: exact
```

```yaml
class_name: Solution
method: joinCells
params:
  - name: board
    type: List[List[str]]
return_type: str
compare: exact
```

返回一组下标、顺序无所谓时：

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

## meta.yaml · 身份

每题都写：

| 字段 | 含义 |
|---|---|
| `slug` | 主编定题时写在派工里的名字，只含小写字母、数字、连字符。`author` 按这个名字写三个文件，文件夹 `problems/<slug>/` 随之出现。主编不预建目录，也不要另起名字 |
| `title` | 中文标题，抄 `statement.md` 首行（去掉 `# `） |
| `difficulty` | `easy` / `medium` / `hard` |
| `time_limit_ms` | 时限，毫秒。取值 1000–5000，缺了当 2000 |
| `memory_limit_mb` | 内存上限，MB。缺了当 256 |
| `tags` | 1～3 个标签，词表见 `{根}/rules/bank.md` 的 tags 一节 |

## meta.yaml · 约束里的数字

把 `statement.md` 约束里的数字填进 `meta.yaml`。写哪些键，只看 `signature.yaml` 里每个参数的类型、以及它们从上到下的顺序。不要看参数叫不叫 `n`。下面两张表是通用写法；再下面的 YAML 只是实例，不要把实例当成所有题都要照抄的模板。

### 输入规模

有的题需要写输入规模（数组的长度、字符串的长度、图上点的个数）。用 `scale_min` / `scale_max`。从上到下看，对上第一行就用那一行：

| 题是哪种 | 规模指什么 | 怎么写 |
|---|---|---|
| 图：先说有几个点，再列出谁和谁相连 | 点的个数，而非点的连线的个数 | 只写 `scale_min` / `scale_max`。那个「有几个点」不要放进 `bounds` |
| 有数组或格子 | 参数里最先出现的那个数组的长度（格子就是行数） | 只写一对 `scale_min` / `scale_max`。后面还有别的数组，不要再写一套 |
| 有字符串 | 字符串的长度 | 写 `scale_min` / `scale_max` |
| 只有单独的整数、小数、`bool` | 不用写 | 不要写 `scale_min` / `scale_max` |

缺了 `scale_min` / `scale_max`（本题需要写时）`mcp__leet__fix_format` 会补 `1` / `100000`。补出来的数若和 `statement.md` 不同，改 `meta.yaml` 去对齐 `statement.md`。`mcp__leet__fix_format` 不会替你编每个参数上的数或字符。

### 每个参数上出现的数或字符

`bounds` 一张表，键等于 `signature.yaml` 里每个参数的 `name`。有几个要写范围的参数，就有几份；每一份只描述这一个参数在题面里能取到的全局两端。字段种类看 `{根}/rules/types.md` 那一列「这个参数上的数怎么写进 meta.yaml」。数字从 `statement.md` 约束抄：

| 题面约束 | 这个参数在 `bounds` 里 |
|---|---|
| `0 <= nums[i] <= 10^9` | `nums.min: 0`，`nums.max: 1000000000` |
| `1 <= k <= n`，且 `n` 最大 `10^5` | `k.min: 1`，`k.max: 100000` |
| 顶点编号从 `0` 到 `n-1`，`n` 最大 `10^5` | 边或顶点编号那个参数：`min: 0`，`max: 99999` |
| 顶点编号从 `1` 到 `n`，`n` 最大 `10^5` | 同一参数：`min: 1`，`max: 100000` |
| 边为 `[u, v, w]`，顶点编号到 `n`、权到 `10^9` | 这一份的下界取题面更小的那个，上界 `1000000000` |
| `0 <= pref[i][j] <= E-1`，`E` 最大 `256` | `pref.min: 0`，`pref.max: 255` |
| 掩码 `0 .. 2^32-1` | 该参数 `min: 0`，`max: 4294967295` |
| `-1e9 <= x <= 1e9`（小数） | `min: -1.0e+9`，`max: 1.0e+9`（YAML 写成带小数点的指数，如 `-1.0e+9`）。题面仍可写 `-1e9`、`10^9` |
| 只含小写字母 / 01 串 | `charset: abcdefghijklmnopqrstuvwxyz` / `01` |
| `true` 或 `false` | 不写这一项 |

边列表前面「有几个点」那个整数的范围写在 `scale_min` / `scale_max`。

漏写某个该写的参数：`mcp__leet__fix_format` 的 `issues` 和 `bounds_notes` 里会出现 `unbounded_param:<name>`。

### 实例（不是通用规则）

`statement.md` 约束写成：`1 <= left <= right <= 10^5`。两个单独的整数，不写输入规模。

```yaml
slug: range-count
title: 区间计数
difficulty: easy
time_limit_ms: 2000
memory_limit_mb: 256
tags:
  - math
bounds:
  left:
    min: 1
    max: 100000
  right:
    min: 1
    max: 100000
```

`statement.md` 约束写成：`-1e9 <= lo <= hi <= 1e9`。小数同样写进 `bounds`。

```yaml
slug: cubic-root
title: 区间内的立方根
difficulty: medium
time_limit_ms: 2000
memory_limit_mb: 256
tags:
  - math
  - newton
bounds:
  lo:
    min: -1.0e+9
    max: 1.0e+9
  hi:
    min: -1.0e+9
    max: 1.0e+9
```

只有 `bool`：`bounds` 也不用写。

```yaml
slug: can-reach
title: 能否到达
difficulty: easy
time_limit_ms: 2000
memory_limit_mb: 256
tags:
  - math
```

`statement.md` 约束写成：`1 <= n <= 10^5`（`n = s.length`）；`s` 只含小写；`1 <= k <= n`。输入规模是字符串有几个字符。

```yaml
slug: longest-run
title: 最长连续段
difficulty: medium
time_limit_ms: 2000
memory_limit_mb: 256
tags:
  - string
scale_min: 1
scale_max: 100000
bounds:
  s:
    charset: abcdefghijklmnopqrstuvwxyz
  k:
    min: 1
    max: 100000
```

`statement.md` 约束写成：`1 <= n <= 10^5`（`n = nums.length`）；`1 <= nums[i] <= 10^6`；`1 <= hi <= 2 * 10^6`。数组里的数和旁边的整数都写在 `bounds` 里，按参数名分开。

```yaml
slug: max-bounded-pairs
title: 和受限的最多配对数
difficulty: medium
time_limit_ms: 2000
memory_limit_mb: 256
tags:
  - greedy
  - sorting
  - two-pointers
scale_min: 1
scale_max: 100000
bounds:
  nums:
    min: 1
    max: 1000000
  hi:
    min: 1
    max: 2000000
```

`k` 写在数组前面时，输入规模仍是数组有几个元素；`k` 自己的范围写在 `bounds.k`。

```yaml
slug: k-then-nums
title: 先 k 后数组
difficulty: medium
time_limit_ms: 2000
memory_limit_mb: 256
tags:
  - array
scale_min: 1
scale_max: 100000
bounds:
  k:
    min: 1
    max: 100000
  nums:
    min: 1
    max: 1000000000
```

`n: int` 后面是一层 `parent: List[int]`（不是边的列表）。输入规模是 `parent` 有几个元素。`n` 要写进 `bounds`（题面通常保证 `len(parent) = n`）。

```yaml
slug: parent-tree
title: 父数组树上的点
difficulty: medium
time_limit_ms: 2000
memory_limit_mb: 256
tags:
  - tree-dp
scale_min: 1
scale_max: 100000
bounds:
  n:
    min: 1
    max: 100000
  parent:
    min: 0
    max: 99999
```

点数 + 边的列表。输入规模是前面那个整数（改名叫 `vertices` 也一样），范围写在 `scale_min` / `scale_max`。边的端点写在 `bounds.edges`。边数按题面（树常 `n-1`）。

```yaml
slug: connected-count
title: 连通点数
difficulty: medium
time_limit_ms: 2000
memory_limit_mb: 256
tags:
  - graph
  - union-find
scale_min: 2
scale_max: 50
bounds:
  edges:
    min: 0
    max: 49
  k:
    min: 1
    max: 1000000000
```

网格在前。输入规模是有几行。格子里的数写在 `bounds.grid`。

```yaml
slug: max-path
title: 最大路径
difficulty: medium
time_limit_ms: 2000
memory_limit_mb: 256
tags:
  - grid
  - dp
scale_min: 1
scale_max: 300
bounds:
  grid:
    min: 0
    max: 2
  k:
    min: 1
    max: 100000
```
