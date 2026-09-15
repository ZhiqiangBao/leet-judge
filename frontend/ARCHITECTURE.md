# 前端模块

给改 `frontend/` 的人看。页面上怎么点见仓库 [`docs/admin.md`](../docs/admin.md)、[`docs/client.md`](../docs/client.md)。HTTP 契约以后端路由为准。

开发时 Vite `:5173` 把 `/api` 转到 `:8080`。上线后 `npm run build` 的 `dist/` 由后端挂载，浏览器只打同一个源。

## 目录

| 路径 | 做什么 |
| --- | --- |
| `src/main.ts` | 挂应用、读主题 |
| `src/App.vue` | 顶栏 / 二级导航；按是否管理员切换入口 |
| `src/router.ts` | 路由表；除登录页外先 `Auth.me()` |
| `src/api.ts` | 唯一 `fetch` 出口；类型与 `Auth` / `Problems` / `Admin` 等命名空间 |
| `src/views/LoginView.vue` | 登录、普通注册 |
| `src/views/ProblemListView.vue` | 题列表 |
| `src/views/ProblemView.vue` | 一题：题面、编辑器、测试、提交 |
| `src/views/ScoresView.vue` / `SubmissionsView.vue` | 普通用户成绩与自己的提交 |
| `src/views/DuelView.vue` | 对战 |
| `src/views/Admin*Stats*.vue` / `Admin*Log*.vue` | 数据：每题 / 用户及日志 |
| `src/views/AdminBank*.vue` | 题库三入口 + 发布 |
| `src/views/AdminGuideView.vue` | 拉手册 markdown 渲染 |
| `src/components/CodeEditor.vue` | 编辑器 |
| `src/components/GridPlay.vue` / `LangBingo.vue` | 题目页小部件、成绩页语言格 |
| `src/markdown.ts` | 题面 / 手册 Markdown |
| `src/theme.ts` | 浅色 / 深色 |
| `src/tags.ts` | 筛选标签展示名（词表在此；对错以后端题目为准） |
| `src/languages.ts` | 语言展示名 |
| `src/format.ts` | 时间、通过率格式 |

## 依赖方向

箭头表示「可以 import」。不要反向。

```text
main ──► App, router, theme

App    ──► router, api.Auth, theme
router ──► views/*, api.Auth

views/* ──► api.ts
         ──► components/*（需要时）
         ──► markdown / theme / tags / languages / format

components/* ──► api.ts（类型）、theme、languages
api.ts       ──► 浏览器 fetch（/api/...）
```

| 允许 | 禁止 |
| --- | --- |
| 页面只经 `api.ts` 访问后端 | 在 `.vue` 里直接 `fetch` |
| 组件被多个页面用 | `views` 互相 import |
| `tags.ts` / `languages.ts` 管展示 | 前端决定某语言能不能交（以 `/api/languages` 与题详情为准） |

列表页只拉题目摘要；点进一题再拉题面、签名、模板、公开样例。
