# 评测主机工具链

面向评测机上的 **Ubuntu**（独立安装、[双系统](host.md)、或 [WSL2](host.md) 里的 Ubuntu）。答题端不用装这些。WSL 请把发行版尽量选接近 **26.04**；更旧的 apt 没有 `zig` 包时按下文「低版本 Ubuntu」装官方二进制。

评测会读主机上的编译器版本再选驱动，不必为了适配器去锁死某一个小版本。当前这台双系统机上核对过：

| 命令 | 版本 | 来源 |
| --- | --- | --- |
| `go version` | `go1.26.0 linux/amd64` | apt `golang-go` |
| `rustc --version` | `rustc 1.93.1` | apt `rustc` |
| `zig version` | `0.16.0` | [ziglang.org](https://ziglang.org/zh-CN/download/) 官方 Linux 包（apt 默认是 0.14.1） |

Zig **0.14.x** 与 **0.16.x** 都已按标准库对过驱动（Windows 上 `zig build-exe` 能过）。**0.15** 有代码分支，未在本机实编。**0.17-dev** 不要装。

## 26.04：Go / Rust 用 apt，Zig 看版本

```bash
sudo apt update
sudo apt install golang-go rustc
go version
rustc --version
```

`apt install zig` 在 26.04 装的是 **0.14.1**（包名 `zig` / `zig0.14`）。要用 0.16 时不要指望 apt 换源，按下面「装 Zig 0.16」做。

应出现在 `/usr/bin` 或 `/usr/local/bin`，systemd 服务 `local-leet` 能直接找到。装完后：

```bash
sudo systemctl restart local-leet
```

打开 `GET /api/languages`，`go` / `rust` / `zig` 的 `available` 应为 true，`runtime_version` 应能读到版本号。

首次部署用仓库里的 `./scripts/setup-ubuntu.sh`（其中仍会 apt 装 `zig` 0.14）。若主机已改成官方 0.16，不要再 apt 装回 0.14 盖掉 `/usr/bin/zig`。

## 装 Zig 0.16（官方包）

二进制从 [ziglang.org/download](https://ziglang.org/zh-CN/download/) 下，不要 GitHub，不要 snap。Linux x86_64 文件名是 `zig-x86_64-linux-0.16.0.tar.xz`（约 53MiB），不要下源码包 `zig-0.16.0.tar.xz`。

适配器**先找** `/usr/bin/zig`，再找 `/usr/local/bin/zig`。apt 的 0.14 若还在 `/usr/bin/zig`，后面装的 0.16 不会被用到。

```bash
sudo apt remove --purge zig zig0.14 zig0.14-dev   # 没有的包会报错，删掉那几个名字再跑

cd /tmp
curl -fL --retry 3 -o zig-x86_64-linux-0.16.0.tar.xz \
  https://ziglang.org/download/0.16.0/zig-x86_64-linux-0.16.0.tar.xz

sudo mkdir -p /usr/local/zig-0.16.0
sudo tar -xJf zig-x86_64-linux-0.16.0.tar.xz -C /usr/local/zig-0.16.0 --strip-components=1
sudo ln -sfn /usr/local/zig-0.16.0/zig /usr/local/bin/zig

hash -r
which zig          # /usr/local/bin/zig
zig version        # 0.16.0
ls /usr/bin/zig    # 应不存在

sudo systemctl restart local-leet
```

官网下不动时可用社区镜像，文件名不变，例如：

```bash
curl -fL --retry 3 -o zig-x86_64-linux-0.16.0.tar.xz \
  https://fs.liujiacai.net/zigbuilds/zig-x86_64-linux-0.16.0.tar.xz
```

只改 `.bashrc` 里的 `PATH` 不够：评测跑在 systemd 里，看不到交互式环境。软链接到 `/usr/local/bin` 即可。

## 低版本 Ubuntu

语言适配器已经进 Git，**编译器仍要本机有**。

### 先看缺什么

```bash
go version
rustc --version
zig version
```

网页语言下拉框灰色、提交 `NA`、接口文案「未安装编译器」，就是评测进程找不到对应二进制。

### Go

`sudo apt install golang-go` 在旧版 Ubuntu 也有。Go 1.22 及以上即可（模块、`any`）。apt 更旧时：

1. 仍先试 `golang-go`，能编过 `scripts/selftest.py` 里的 Go 用例就不用换。
2. 不行再装官方包（不是本仓库源码站）：<https://go.dev/dl/> ，解压到 `/usr/local/go`，保证 `/usr/local/go/bin/go` 存在。适配器会找 `/usr/bin/go` 与 `/usr/local/go/bin/go`。

评测设置了 `GOPROXY=off`，不要 `go get`。构建缓存写在作业临时目录，评测结束删除，不占用 `~/.cache/go-build`。

### Rust

优先 `sudo apt install rustc`。只要 `rustc` 能编 edition 2021 即可，**不要**为评测装 rustup default（带 docs，体积大）。

找不到 `/usr/bin/rustc` 时（例如只装了 rustup 且 systemd 没有 `~/.cargo/bin`）：

```bash
sudo ln -sf "$HOME/.cargo/bin/rustc" /usr/local/bin/rustc
sudo systemctl restart local-leet
```

禁止判题时 `cargo add`。JSON 用仓库内置小解析器。

### Zig

官方 Ubuntu 源从 **25.10** 才有 `zig` 包。26.04 apt 默认 **0.14.1**。驱动按 `zig version` 分派：

| 主机 `zig version` | 驱动要点 |
| --- | --- |
| 0.14.x | `GeneralPurposeAllocator`、`std.io.getStdIn`、`ObjectMap.init` |
| 0.16.x | `smp_allocator`、`posix`/`linux.write` 读写 stdin（不拉 `Threaded`）、`ObjectMap = .empty` 且 `put(alloc, …)` |
| 0.15.x | 有分支，未实编 |
| 0.17+ | 不要用 |

| 情况 | 做法 |
| :--- | :--- |
| 已是 0.14.x 或 0.16.x，且 `/api/languages` 里 zig 可用 | 不用改 |
| 想用 0.16，apt 仍是 0.14 | 按上文卸 apt 包，装官方 0.16 到 `/usr/local` |
| 误装 snap / 0.17-dev | 卸掉，改回 0.14 或 0.16 |
| **25.04 及更早**，仓库里没有 `zig` | **不要** `snap install zig`。从 [ziglang.org/download](https://ziglang.org/zh-CN/download/) 下 **0.14.1** 或 **0.16.0** 的 `zig-x86_64-linux-*.tar.xz` |

编译用 `-O Debug`（Linux x86_64 走自托管后端，比 LLVM `ReleaseFast` 快很多；运行会慢于优化编译）。稳定驱动源码在 `data/zig-harness/`（很小、覆盖写入）。编译缓存只写在当次作业目录，评测结束删掉，避免 `~/.cache/zig` 或 `data/zig-cache` 一直涨。

Zig 源码托管已迁到 Codeberg，**二进制仍从 ziglang.org 下**。

```bash
# 仅当 apt 没有 zig、且选用 0.14.1 时
cd /tmp
curl -fLO https://ziglang.org/download/0.14.1/zig-x86_64-linux-0.14.1.tar.xz
sudo tar -xJf zig-x86_64-linux-0.14.1.tar.xz -C /usr/local
sudo ln -sfn /usr/local/zig-x86_64-linux-0.14.1/zig /usr/local/bin/zig
zig version   # 0.14.1
```

### 服务找不到编译器

`node` / `tsc` / `go` / `rustc` / `zig` 若只在用户交互式 `PATH` 里（nvm、rustup、手动解压目录），systemd 里的 `local-leet` 看不见。处理：

- 用 apt 装到 `/usr/bin`，或
- `sudo ln -s` 到 `/usr/local/bin`，然后 `sudo systemctl restart local-leet`

不要改评测机上的 `git config`。改完工具链后必须重启服务再看 `/api/languages`。
