<div align="center">

# Leet Judge

**家里那台 Ubuntu，就是评测机。**

本仓库只有评测程序（网页 + 沙箱判题），**不含题库**。题目用付费或自备的 zip 导入。隐藏测例只在「提交」时跑，失败只给序号。

[仓库](https://github.com/ZhiqiangBao/leet-judge)
·
[评测机从哪来](docs/host.md)
·
[服务端](docs/server.md)
·
[客户端](docs/client.md)
·
[题目录](docs/problems.md)

```
  手机 / Windows / Mac              评测机（Linux）
 ┌─────────────────────┐         ┌──────────────────────────┐
 │  题面 · 编辑器 · 榜   │ :8080  │  FastAPI · 沙箱判题       │
 │  浅色 / 深色  切换    │ ─────► │  python3 gcc g++ node …  │
 └─────────────────────┘         │  题库 = 本机 problems/    │
      答题端不装编译器            │  zip 导入，不进本仓库     │
                                 └──────────────────────────┘
```

</div>

## 能评什么

| | 语言 | 状态 |
| :--- | :--- | :--- |
| ● | Python 3 · C · C++20 | 主机 `/usr/bin/python3`、`gcc`、`g++` |
| ● | JavaScript · TypeScript | 主机 `node`；TypeScript 另需 `sudo npm install -g typescript` |
| ● | Go · Rust · Zig | `sudo apt install golang-go rustc`；Zig 见 [toolchains.md](docs/toolchains.md) |

「测试」只跑题面示例、不计分。「提交」跑全部隐藏测例。

浏览器：

```text
http://<Ubuntu局域网IP>:8080
```

管理员只在本机 `http://127.0.0.1:8081` 注册。

## 第一次装

先有一台 Ubuntu（[双系统 / WSL](docs/host.md)），再：

```bash
git clone https://github.com/ZhiqiangBao/leet-judge.git
cd leet-judge
chmod +x scripts/*.sh
./scripts/setup-ubuntu.sh
```

装好后：顶栏「题库 → 本机导入」，上传题包 zip（不用先解压）。

**不要再跑 `setup-ubuntu.sh` 来启动服务**（会把官方 Zig 盖成 apt 的 0.14）。服务停了用：

```bash
sudo systemctl start local-leet
```

## 文档

| | |
| :--- | :--- |
| [评测机从哪来](docs/host.md) | Windows 双系统、WSL2 |
| [题目录](docs/problems.md) | zip 里每题要有哪些文件 |
| [服务端](docs/server.md) | 部署、systemd、导入 |
| [客户端](docs/client.md) | 注册、测试 / 提交 |
| [管理页](docs/admin.md) | 管理员按钮 |
| [语言](docs/languages.md) / [工具链](docs/toolchains.md) / [适配器](docs/adapters.md) | 加编译器 |

本仓库不含出题流水线、MCP、查重索引。
