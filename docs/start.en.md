# After you buy a problem pack

[简体中文](start.zh.md)

For someone who already installed the judge and just downloaded the zip. The same text in the zip is `GETTING-STARTED.en.md`.

## 1. Confirm the judge is running

The browser should open `http://<host-ip>:8080`. If it does not, see [host.md](host.md) and [server.md](server.md) (Chinese).

## 2. Sign in as admin

Register an admin only on the judge host at `http://127.0.0.1:8081`. Then sign in at `:8080`. The top bar is **题目 / 数据 / 题库 / 手册** (Problems / Data / Bank / Manual). The on-screen UI is Chinese.

## 3. Import the zip

**题库 → 本机导入** → choose the downloaded zip. Do not unzip first. Success lists the problem names that were written.

To replace an existing problem of the same name, check **覆盖评测机上的同名题目**.

## 4. Publish for candidates

Imported problems are admin-only until you publish. Open **题库 → 发布** and publish each problem for the exam.

If you skip publish, candidates see an empty list.

## 5. Let candidates solve

Candidates register themselves at `:8080` (not as admin). They only see published problems.

- **测试** (Test): statement samples only; does not count as a score.
- **提交** (Submit): hidden test cases (candidates never see the input). A failure shows the case number only, not the input.
- Resubmits in the same session are allowed; the best Accepted result counts.

Use **数据** to review per-problem and per-user submissions. Do not paste hidden test cases into chat or slides.

## Refunds

Store rule: refund within 7 days if you have not used hidden test cases in a formal Submit. After that, no refund.
