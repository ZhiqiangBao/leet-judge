# Leet Judge

[简体中文](README.zh.md)

A self-hosted programming judge. This repository is the program only — **no problem bank**. Import a problem-pack zip, then publish. Candidates see and submit only published problems.

[Install](#install) · [Import a pack](#import-a-pack) · [What candidates do](#what-candidates-do) · [Docs](#docs)

Languages: Python 3, C, C++, JavaScript, TypeScript, Go, Rust, Zig. Candidates do not install compilers on their own machines.

## Install

Use Ubuntu (a dedicated machine, dual boot, or [WSL](docs/host.md) — that page is in Chinese), then:

```bash
git clone https://github.com/ZhiqiangBao/leet-judge.git
cd leet-judge
chmod +x scripts/*.sh
./scripts/setup-ubuntu.sh
```

Open `http://<host-ip>:8080` in a browser. Register an admin only on the host: `http://127.0.0.1:8081`.

If the service is down: `sudo systemctl start local-leet`. Do not re-run the install script to start the service (it can replace the installed Zig version).

## Import a pack

1. Admin login → **题库 → 本机导入**, upload the zip (do not unzip first).
2. **题库 → 发布** the problems for the exam. Imports are unpublished by default.
3. Candidates register at `:8080` and only see published problems.

Admins can open **Problems** and see every imported item, including unpublished ones, and can solve them there.

## What candidates do

Open a problem and fill in the empty function. **测试** (Test) runs statement samples only and does not count as a score. **提交** (Submit) runs the hidden test cases (candidates never see those inputs); a failure shows the case number only. Resubmits in the same window are allowed; the best Accepted result counts. The on-screen UI is Chinese.

## Docs

| Audience | English | 中文 |
| --- | --- | --- |
| After buying a pack | [docs/start.en.md](docs/start.en.md) | [docs/start.zh.md](docs/start.zh.md) |
| Candidate UI | [docs/client.en.md](docs/client.en.md) | [docs/client.md](docs/client.md) |
| Admin buttons | [docs/admin.en.md](docs/admin.en.md) | [docs/admin.md](docs/admin.md) |
| Host setup / start-stop | Chinese only: [docs/host.md](docs/host.md), [docs/server.md](docs/server.md) | same |
| Problem files on disk | Chinese only: [docs/problems.md](docs/problems.md) | same |
| Extra compilers | Chinese only: [docs/toolchains.md](docs/toolchains.md) | same |
