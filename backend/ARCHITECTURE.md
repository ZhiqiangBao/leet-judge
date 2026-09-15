# 后端模块

给改 `backend/` 的人看。部署与磁盘约定见仓库 [`docs/server.md`](../docs/server.md)。语言适配器写法见 [`docs/adapters.md`](../docs/adapters.md)。

进程入口：`app.main:app`（`:8080`）。启动时顺带拉起管理员注册小应用（只监听本机 `:8081`），并启动判题队列 worker。构建好的前端在 `frontend/dist` 时由本进程挂静态文件。

**不要** `import` 仓库里的 `.qwen/`。出题工具不在本树。

## 目录

| 路径 | 做什么 |
| --- | --- |
| `app/main.py` | FastAPI 组装：中间件、路由、生命周期、SPA |
| `app/admin_register.py` | 本机注册管理员，与 `:8080` 上的普通注册分开 |
| `app/config.py` | 路径与环境变量（题库目录、数据目录、槽位数） |
| `app/db.py` | SQLite 引擎与 session |
| `app/models.py` | 表：用户、提交、草稿、对战 |
| `app/schemas.py` | API 出入结构 |
| `app/deps.py` | 登录、管理员、建用户 |
| `app/api/auth.py` | `/api/auth` |
| `app/api/problems.py` | 题目列表/详情、测试、提交、草稿、排行、语言列表 |
| `app/api/admin.py` | 统计、手册、git 同步、导入、按文件写盘、生成 starter |
| `app/api/duels.py` | 对战房间 |
| `app/services/problems.py` | 磁盘题库：加载、导入、合并文件。`reload` 不打开隐藏测例文件 |
| `app/services/starters.py` | 按签名写空函数模板 |
| `app/services/git_sync.py` | 评测机克隆上 `git pull` |
| `app/services/admin_stats.py` | 按题 / 按用户聚合提交 |
| `app/services/progress.py` / `ranking.py` / `duels.py` | 成绩、耗时榜、对战状态 |
| `app/judge/queue.py` | 提交与测试共用槽位；提交入队，测试当场抢槽 |
| `app/judge/engine.py` | wrap → 编译 → 按行喂该题测例 |
| `app/judge/sandbox.py` | 限时限内存跑子进程 |
| `app/judge/typespec.py` | 读 `rules/types.yaml`（与出题侧各加载，不互相 import） |
| `app/judge/languages/` | 各语言适配器 |
| `app/judge/runtimes/` | Python / Node 驱动文本 |
| `app/judge/traps.py` / `hints.py` | 题目页侧栏提示（用 meta，不扫隐藏测例） |
| `tests/` | pytest |

## 依赖方向

箭头表示「可以 import」。不要反向。

```text
main ──► api/* ──► services/* ──► models / schemas / db / config
              │         └──► judge.typespec
              └──► judge.queue / judge.engine

judge.engine ──► services.problems（只读 bank、按行读测例）
             ──► languages / sandbox

languages ──► sandbox / typespec / runtimes
starters  ──► typespec / schemas
admin_register ──► deps / db     （独立 ASGI，不经过 api/*）
```

| 允许 | 禁止 |
| --- | --- |
| HTTP 层调 `queue` / `engine` | `services` 去调 `engine` 或 `queue` |
| 判题读 `bank` | 题库服务去跑编译 |
| `typespec` 给签名和 starter 用 | 适配器 import 出题脚本 |
| `api/admin` 调 `git_sync`、`problems`、`starters` | 为每个提交再 `uvicorn` 一个新进程 |

`tests/` 可以按需 import `app`，不参与上图运行时环。
