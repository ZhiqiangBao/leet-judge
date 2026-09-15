# 服务端操作

服务端即**评测主机**：安装并运行本仓库的那台 Linux（独立 Ubuntu、[Windows 双系统里的 Ubuntu](host.md)，或 [WSL2 里的 Ubuntu](host.md)）。它提供网页、保存账号与提交，用本机 `python3`、`gcc`、`g++`、`node`、`tsc`、`go`、`rustc`、`zig` 判题。GitHub 仓库名是 `leet-judge`；systemd 服务名是 `local-leet`。本仓不含题目。

还没有这台 Linux 时先看 [host.md](host.md)，不要在 Windows 上用 README 的开发机命令冒充评测机。

浏览器所在电脑不是服务端。客户端说明见 [client.md](client.md)。

## 日常：启停（已经跑过 setup 之后）

服务停了、重启过机器、或者 `serve-window.sh` 把后台停掉了，用这一条，**不要再跑 `setup-ubuntu.sh`**：

```bash
sudo systemctl start local-leet
systemctl status local-leet
```

`active (running)` 即可。本机打开 `http://127.0.0.1:8080`。

```bash
sudo systemctl stop local-leet      # 停
sudo systemctl restart local-leet   # 重启（改代码 / 拉题后）
journalctl -u local-leet -f         # 日志；关掉这个窗口不会停服务
```

开机不要自启：`sudo systemctl disable local-leet`。停用并立刻关掉：`sudo systemctl disable --now local-leet`。

提示 `Unit local-leet.service not found`：这台机器还没装过，才走下面「首次部署」。

## 首次部署

依赖：Ubuntu（或 WSL 中的 Ubuntu）、`python3`、`gcc`、`g++`、Node.js / npm（构建前端，并作为 JavaScript 评测运行时）。TypeScript 评测另需全局 `tsc`（`setup-ubuntu.sh` 会 `npm install -g typescript`）。脚本还会 apt 装 Go / Rust / Zig（Zig 在 26.04 是 0.14；改官方 0.16 见 [toolchains.md](toolchains.md)）。

WSL 必须先打开 systemd，并且仓库在 `~/leet-judge` 而不是 `/mnt/c`，见 [host.md](host.md)。

```bash
git clone https://github.com/ZhiqiangBao/leet-judge.git
cd leet-judge
chmod +x scripts/setup-ubuntu.sh scripts/run-ubuntu.sh scripts/update-from-github.sh scripts/serve-window.sh
./scripts/setup-ubuntu.sh
```

`setup-ubuntu.sh` **只用于第一次**（装依赖、写 systemd、开机自启）。以后服务停了用上一节的 `start`，不要重跑它：它会 `apt install zig`，把你装的 0.16 盖回 0.14。已经装过再跑，脚本会直接 `start` 然后退出（要硬重装才加 `--reinstall`）。

查询局域网 IP：`hostname -I` 或 `ip -4 addr`（**WSL 这个地址通常不是家里局域网 IP**，本机请用 `http://127.0.0.1:8080`，给其它设备访问见 [host.md](host.md)）。若启用 ufw：

```bash
sudo ufw allow 8080/tcp
```

不使用 systemd、当前终端前台运行（关闭终端即停止）：

```bash
./scripts/run-ubuntu.sh
```

弹出独立日志窗口（关闭该窗口即停止整个服务；若 `local-leet` 正在后台跑会先停掉）：

```bash
chmod +x scripts/serve-window.sh
./scripts/serve-window.sh
```

## 从 GitHub 更新

在克隆目录中：

```bash
cd ~/leet-judge
./scripts/update-from-github.sh
```

脚本执行 `git pull`；`backend/requirements.txt` 或 `frontend/` 有变更时会重装依赖或重建前端，然后 `systemctl restart local-leet`。

仅更新了 `problems/` 时也可：

```bash
git pull
sudo systemctl restart local-leet
```

管理员网页怎么点，见 [admin.md](admin.md)。仅更新了 `problems/` 时不必重启进程；同步后若页面提示代码也有变更，再 `sudo systemctl restart local-leet`。

## 管理员

账号存在本机 `data/` 的 SQLite 中。**登录**可以在任意设备上走 **8080**；**注册管理员**只走评测机本机的另一个端口，不和登录、普通用户注册共用 8080。

1. 在评测机本机浏览器打开 `http://127.0.0.1:8081`（只监听回环，局域网打不开；可用 `curl -d 'username=admin&password=....' http://127.0.0.1:8081/register`）。
2. 填用户名和密码，提交。这是管理员账号。
3. 到 `http://<局域网IP>:8080` 用同一账号**登录**（手机、Windows 都可以）。顶栏变为「题目 / 数据 / 题库 / 手册」。

`:8080` 上的「注册」永远是普通用户，即使是全站第一个账号也不是管理员。端口可用环境变量 `LOCAL_LEET_ADMIN_PORT` 改（默认 8081），主机地址写死 `127.0.0.1`。

补救：已有普通账号要升管理员时，设环境变量后重启，再用该用户名**在任意设备登录一次**：

```bash
sudo systemctl edit local-leet
```

写入（升管理员和改槽位可以写在同一个文件里）：

```ini
[Service]
Environment=LOCAL_LEET_ADMINS=你的用户名
Environment=LOCAL_LEET_JUDGE_SLOTS=2
```

这会落到 `/etc/systemd/system/local-leet.service.d/override.conf`，`git pull` 不会覆盖。槽位怎么改见「评测并发」。

```bash
sudo systemctl restart local-leet
```

多个用户名用逗号分隔。不要用 `LOCAL_LEET_ADMINS` 代替 8081 日常开户。

## 接口文档

FastAPI 自动文档（需服务已启动）：

```text
http://127.0.0.1:8080/docs
```

这不是做题界面，只列出 HTTP API。

## 数据备份

SQLite、评测临时文件、Zig 运行时生成的 `data/zig-harness/` 都在本机 `data/`，**不要 git add**（`.gitignore` 已忽略整目录）。备份或迁移时复制该目录。用户和提交记录不在 GitHub 上。

## 角色（服务端视角）

| 事项 | 位置 |
| --- | --- |
| 网站进程 | systemd `local-leet`（`:8080` 做题/登录/普通注册；`127.0.0.1:8081` 只注册管理员） |
| 用户与提交 | `data/local-leet.db` |
| 当前题库 | 本机 `problems/`（由 git 拉取或管理员写盘）；`reload` 只读 meta/题面/签名/starter，隐藏测例留在磁盘，判该题时再按行流进 stdin |
| 判题编译器 | 系统 `python3`、`gcc`、`g++`、`node`、`tsc`、`go`、`rustc`、`zig` |
| 类型能否提交 | [`rules/types.yaml`](../rules/types.yaml) 的 wrap 表 ∩ 题 `signature` ∩ 可选 `meta.languages` ∩ 本机 `detect()` |

向 GitHub 推送题目在仓库维护端完成，服务端负责 `git pull` 后加载。题目文件约定见 [problems.md](problems.md)。

## 评测并发

提交和题目页「测试」共用 `LOCAL_LEET_JUDGE_SLOTS`（默认 2，范围 1～8）。槽满时提交保持排队，测试的 HTTP 会等。改这个值：不要改仓库里的 [`backend/app/config.py`](../backend/app/config.py) 或 [`scripts/local-leet.service`](../scripts/local-leet.service)（一拉仓库或重装模板就丢）。在评测机上：

```bash
sudo systemctl edit local-leet
```

写入 `Environment=LOCAL_LEET_JUDGE_SLOTS=2`，与 `LOCAL_LEET_ADMINS` 可写在同一段 `[Service]`，然后 `sudo systemctl restart local-leet`。机器偏热用 `1`；人多再提到 `3` 或 `4`。

## 管理页如何写 `problems/`

代码：[`backend/app/services/problems.py`](../backend/app/services/problems.py)。按钮怎么点见 [admin.md](admin.md)。评测进程不 import `.qwen/`。

zip **只在服务端解开**，上传的人不用先解压。

| 入口 | 成功时 `problems/<slug>/` | 失败时 | 中途目录（点号开头，`reload` 会跳过） |
| --- | --- | --- | --- |
| 本机导入 | 整道题拷进去；已有 `starter/` 就带上，**不**在这一步生成 | 正式目录不变 | `.import-<slug>/` → 改名 |
| 按文件上传 · 新题 | 四个必需文件齐全才出现这个目录 | **不建**正式目录 | `.patch-<slug>/` → `Problem()` 能加载再改名 |
| 按文件上传 · 已有题 | 只覆盖这次选的文件；没传的（含 `starter/`）保留 | 正式目录保持上传前 | 同上 |
| 生成 starter | 按 `signature.yaml` 写 `starter/`，不读 `tests.jsonl` | 四个源文件不动 | 无 |

改名中途进程被杀掉：磁盘上可能留下 `.import-*` / `.patch-*`，删掉即可。

## 判题、请求与内存

网站和判题在**同一个** FastAPI 进程里。不要为每次提交再拉起一个 Python 评测进程。

### 进程里留什么

| 时机 | 读 | 不读 |
| --- | --- | --- |
| 启动 / 重新加载磁盘 | 每题 `meta.yaml`、`statement.md`、`signature.yaml`、`starter/` | `tests.jsonl` |
| 打开题目、「测试」 | jsonl **从头**读到第一条 `hidden: true` | 其后隐藏行 |
| 正式提交 | 先编译；成功后再把**该题** jsonl 按行写入 harness stdin | 编译前把测例 parse 成对象；其它题的 jsonl |

公开样例必须写在文件前部。stdin 用原行，不要 `json.loads` 整份隐藏测例，也不要先拼成一个大 `str` 再编译。只在这些地方按行 parse：公开样例、WA 失败那一行、管理端写入的新测例。题目页侧栏用 `meta` 的 tags / `scale_max` / `bounds`，不打开 jsonl。

题面 + starter 很小，可以留在进程的 `bank` 里。隐藏 jsonl 不要整库缓存（原文约百 MB，parse 后可到 1G）。点题不是从磁盘 `new` 一个 `Problem`，只是 HTTP 拉这一题，避免把整库题面塞进浏览器。

### 浏览器拉什么

| 请求 | 内容 |
| --- | --- |
| `GET /api/problems` | 全库 meta。没有题面、没有测例 |
| `GET /api/problems/{slug}` | 这一题：题面、签名、starter、开头公开样例 |
| `GET .../draft`、`.../ranking` | 草稿；点开「排行」才拉榜 |

### 提交与测试如何排队

槽位数见「评测并发」。

| | 入口 | 行为 |
| --- | --- | --- |
| 提交 | `POST /api/problems/{slug}/submit` | 写入 SQLite 后进队列；空闲槽位上的 worker 判题。槽满则保持排队 |
| 测试 | `POST /api/problems/{slug}/run` | 跑公开测例，先抢同一批槽位；槽满则这个请求等 |

判一题：`wrap` → `compile` → 按行喂该题 `tests.jsonl`。驱动读一行、判一行、丢掉。WA/RE 时驱动里的 `total` 可以只是当前下标，父进程用 jsonl 行数写成真正的 N。

## 接入其他语言（服务端要做什么）

语言分两截，缺一不可：

| | 在评测主机上做 | 在 Git 仓库里做 |
| --- | --- | --- |
| 内容 | 安装运行时：`node`、`go`、`rustc`、`zig` 等 | 实现适配器 `wrap` / `compile` / `run`，补 starter 与前端高亮 |
| 不做则 | `/api/languages` 里 `runtime_detected` 为 false | `implemented` 为 false，提交得 `NA` |
| 如何同步到主机 | 本机 `apt` / 官方安装包，与 GitHub 无关 | 推送到仓库后，主机 `./scripts/update-from-github.sh` |

只在 Ubuntu 上 `apt install golang-go` **不会**让 Go 可以交题。只改仓库、主机没有 `go`，同样不可用。某题签名若某语言还不能 wrap，下拉里根本没有该语言（不是 `NA`）。适配器写法见 [adapters.md](adapters.md)。

可在评测主机上直接改 `backend/` 并重启 `local-leet` 做试验。要给家里其他开发者用、或避免被下次 `git pull` 覆盖，仍须把改动推回 GitHub。

## 协同开发

协作面是 GitHub 仓库 https://github.com/ZhiqiangBao/leet-hub，不是评测主机上的网页账号。

- 把协作者加为该仓库的 Collaborator（或使用 Pull Request）。每人克隆、改 `problems/` 或 `backend/`、推送。
- 评测主机只部署：定期 `git pull`（或 `./scripts/update-from-github.sh`）并重启服务。不要把评测机当成唯一的 git 工作副本；多人同时在主机上改同一目录会互相覆盖。
- 网站管理员只能改主机磁盘上的题库，不能改适配器代码，也不能代替 GitHub 写权限。
- 用户提交记录在主机 `data/` 里，不进入 Git，互不影响协同。

更新顺序：仓库合并 → 评测主机拉取 → 若新增语言则在主机安装对应编译器 → `systemctl restart local-leet`。
