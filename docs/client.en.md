# Candidate UI

[简体中文](client.md)

The client is the device that opens the judge site: Windows, macOS, a phone, or the host’s own browser. Do not install Python / gcc / g++ on the client, and do not keep accounts there. Accounts, problems, and judging live on the judge host.

Host install and start/stop: [server.md](server.md) (Chinese). No host yet: [host.md](host.md) (Chinese).

On-screen labels are Chinese. This page uses those labels, with an English gloss.

## Open the site

In a browser:

```text
http://<judge-LAN-IP>:8080
```

Dual-boot / dedicated Ubuntu: run `hostname -I` on the host. Port `8080` is required.

WSL as the judge: on **that same Windows machine**, use `http://127.0.0.1:8080`. Other devices usually cannot connect; see [host.md](host.md).

If the address is `localhost:5173`, you are on the frontend dev server, not the home judge.

## Register and sign in

On the judge host browser, open `http://127.0.0.1:8081` to register an **admin** (that port is not reachable from the LAN). Registration on `:8080` is always a normal user, including the first account. After the admin exists, sign in from any client at `:8080`. The top bar becomes **题目 / 数据 / 题库 / 手册** (Problems / Data / Bank / Manual).

Username: 3–32 characters, letters, digits, underscore. Password: at least 4 characters. The same username on any client is the same account on the host.

## Solve

1. After login, the problem list supports search, difficulty, and topic filters. Status: passed is `AC`; attempted but not passed is **尝试过**.
2. Open a problem: statement on the left, editor on the right.
3. The language dropdown lists languages this problem accepts **and** that the host has installed. A missing compiler is grey and submits as `NA`. Common options: Python 3, C, C++20, JavaScript, TypeScript, Go, Rust, Zig (Go / Rust / Zig: [toolchains.md](toolchains.md)).
4. Fill in the starter: Python / C++ / JavaScript / TypeScript use a `class Solution` method; C uses a free function. Do not write `main` (including Go `func main`). Keep `package main` in the Go starter.
5. **测试** (Test): statement samples only. Does not count toward score, ranking, or “passed”. The button may spin longer when the judge is busy.
6. **提交** (Submit): all tests, including hidden test cases (candidates never see those inputs); written to the submission log. All-pass counts as passed and enters that language’s time ranking. The page waits when the judge is busy.

Verdicts:

| Result | Meaning |
| --- | --- |
| `AC` | All tests passed |
| `WA` | Wrong answer |
| `TLE` | Time limit |
| `MLE` | Memory limit |
| `RE` | Runtime error |
| `CE` | Compile error |
| `NA` | Language unavailable |

Public-sample failures show input, expected, and output. Failures on hidden test cases show the case number only.

Top bar **成绩** lists your best AC time and rank per problem and language. The problem page has a ranking for the current language. The editor autosaves a draft per account; reopening the same problem and language restores the last code.

**提交记录** lists only the signed-in user’s history. Test runs do not appear in submissions or scores. Those two items are on the normal-user top bar; admins use **数据** for site-wide summaries.

Normal users only see **published** problems. Unpublished items are admin-only.

## Admin (in the browser)

Top bar **题目 / 数据 / 题库 / 手册**. The problem page matches normal users, except admins see unpublished items. What the other tabs do: [admin.en.md](admin.en.md).

Do not edit the same problem in the web UI and in Git at the same time.

## API docs

```text
http://<judge-IP>:8080/docs
```

This is the API page, not the solving UI.
