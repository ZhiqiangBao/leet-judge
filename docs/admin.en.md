# Admin UI

[简体中文](admin.md)

After an admin signs in, the top bar is **题目 / 数据 / 题库 / 手册** (Problems / Data / Bank / Manual). Normal users see **题目 / 成绩 / 提交记录**. Admins still solve under **题目** and see every imported problem, including unpublished ones. Normal logins only see published problems. **测试** (Test) runs samples; **提交** (Submit) runs hidden test cases. In the same interview window, resubmits are allowed; the best `AC` counts.

Imports are unpublished by default. To expose a problem: **题库 → 发布**.

Do not change other people’s passwords or delete accounts in the web UI.

On-screen labels are Chinese. This page uses those labels.

## 题目 (Problems)

Admin: the list includes unpublished items, marked **未发布**. Normal users: published items only. Tests do not count as a score; Submit runs hidden test cases.

## 数据 (Data)

| Entry | You do | You see |
| --- | --- | --- |
| Per-problem stats | Open the list; click a row | Submits, AC count, pass rate; then recent submits for that problem |
| User overview | Open the list; click a row | That user’s total submits, pass rate, per-language stats; then recent submits |

Pass rate = `AC` count / all formal submits. No submits shows **—**, not 0%. Logs keep at most 300 rows. Click a row for source. Normal users cannot see other people’s source.

## 题库 (Bank)

All three entries change problems on the judge host. Do not edit the same problem in the web UI and in Git at the same time.

File contents (`meta.yaml` and the rest): [problems.md](problems.md) (Chinese). This page is only what each button does.

### 远程同步 (Sync from Git)

**Do this** after you have already pushed problems to GitHub: click **从 Git 同步**. If you only changed files on the host disk and did not push: click **只重新加载磁盘**.

Paid zip packs use **本机导入**, not this.

| On screen | Next |
| --- | --- |
| Pulled and loaded N problems | Open **题目** and confirm they appear |
| No new remote commits | Stop clicking; push first if the laptop still has unpushed work |
| Restart required on the host | Restart the service; [server.md](server.md) |
| Red error | Fix the error (GitHub, permissions, conflict). Do not mash the button |

### 本机导入 (Import on this host)

**Do this:** use one of the two pickers. Choose a local `problems/<slug>` folder, or a `.zip` (do not unzip first). To replace a same-name problem, check **覆盖评测机上的同名题目**.

| On screen | Next |
| --- | --- |
| Wrote problem name(s) | Open **题目**, then **发布** if candidates should see them |
| Missing a file / not a valid zip | Add the four required files, or pick another pack |
| Problem already exists | Check overwrite and pick again, or use another directory name |

### 发布 (Publish)

**Do this** after import. Unpublished problems are only openable under **题目** by admins. **发布** makes them visible to normal logins. **撤回** removes them from the candidate list.

| On screen | Next |
| --- | --- |
| Published a problem | Refresh **题目** with a normal account; it should appear |
| No imported problems yet | Import a zip first |

### 按文件上传 (Upload by file)

**Do this:** fill in the directory name. For a new problem, select `meta.yaml`, `statement.md`, `signature.yaml`, and `tests.jsonl` together. For an existing problem you may select only the files you are changing. Click **写入目录**. For empty starters, click **生成 starter** after success.

| On screen | Next |
| --- | --- |
| Wrote, and **生成 starter** appears | Open the problem under **题目**; generate starters if needed |
| Still missing a file | A new problem needs all four files |
| Slug mismatch / invalid file | Fix the file or directory name against [problems.md](problems.md), then upload again |
| Starters generated | Open the problem and switch languages in the editor |

A failed upload does not leave a broken half-problem in the list. Do not paste hidden test cases into chat or a text box; upload files only.

## When submits slow down

When Test and Submit are busy, submits queue and the Test button spins longer. Wait for the result.

To change how many compiles/runs the host does at once, edit the host; see [server.md](server.md) **评测并发**. Do not treat repository code as live config.
