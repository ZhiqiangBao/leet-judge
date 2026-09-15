# 评测机从哪来

判题只发生在 **Linux 上的本仓库进程**里：系统里的 `python3` / `gcc` / `g++` / `node` 等编译用户代码。Windows 浏览器、手机只打开网页，不装编译器。

三种常见形态：

| | 独立 Ubuntu / **Windows+Ubuntu 双系统** | **WSL2** 里的 Ubuntu | Windows 原生 |
| --- | --- | --- | --- |
| 家里局域网做题 | **首选**。`hostname -I` 就是局域网 IP | 本机浏览器可以；手机/其它电脑要额外做端口转发 | 不要当评测机 |
| systemd `local-leet` | 正常 | 需打开 systemd，见下文 | 无 |
| 沙箱 `unshare --net` | 一般可用 | 常常失败，评测仍能跑，只是少一层断网 | — |
| 给谁用 | 家人、多台设备 | 开发者本机自测、一个人刷题 | — |

装完 Linux 之后的 `git clone`、`./scripts/setup-ubuntu.sh` 见 [server.md](server.md)。工具链版本见 [toolchains.md](toolchains.md)。本文只写：**怎么在已有 Windows 的电脑上弄出那台 Ubuntu**。

评测机按 **Ubuntu 26.04 LTS Desktop amd64** 来（与 [toolchains.md](toolchains.md) 一致）。官网 ISO 文件名以下载页为准，下文写成 `ubuntu-26.04-desktop-amd64.iso`。

---

## 安装前（三种做法都要）

1. **备份**重要文件。改分区、写引导都可能让 Windows 暂时进不去。
2. **关掉 BitLocker**（或先挂起）：设置 → 隐私和安全性 → 设备加密 / BitLocker。加密盘未解锁时 Linux 安装器看不见 Windows。
3. **关掉 Windows 快速启动**：控制面板 → 电源选项 → 选择电源按钮的功能 → 取消「启用快速启动」。
4. 笔记本若开了 **Intel RST / RAID**，Ubuntu 安装器可能看不到磁盘，需在 BIOS 改成 AHCI（改之前先搜该机型的做法）。
5. Windows 盘上留够**可用空间**（建议 ≥40 GB，能 80 GB 更好）。安装器会问从 Windows 划走多少，**不必**事先在 DiskGenius 里划出一大块未分配。免 U 盘只另外要一块 **128 MB FAT32** 放 GRUB 的三个 EFI。

镜像只从 Ubuntu 官网下，不要用网盘里来路不明的 ISO：

- Desktop：<https://ubuntu.com/download/desktop>
- 中文跳转：<https://cn.ubuntu.com/download>

选 **Ubuntu Desktop**、**64-bit PC (AMD64)**。不要 Server（没有桌面也能当评测机，但首次装双系统用 Desktop 更省事）。不要 WSL 专用的 rootfs 包（那个给 WSL 用，见文末）。

---

## 免 U 盘：DiskGenius 的 grubfile + 硬盘上的 ISO

这条是本仓库作者在 Windows 上实际用过的装法：只要 **DiskGenius** 和官网 ISO，不要 U 盘，也不要 Grub2Win。ISO 可以就放在「下载」文件夹。

需要的软件：

- [DiskGenius](https://www.diskgenius.cn/)（管理员打开）
- 上一步下好的 Ubuntu Desktop ISO（放着别动，装完再删）

### 1. 划 128 MB FAT，拷上三个 EFI

1. 以管理员打开 DiskGenius，选中 Windows 那块盘。从空闲里新建一个 **128 MB、FAT32** 分区（界面上写 FAT 也行）。不要动已有的 EFI、不要动 Windows 的 C:。
2. 把 DiskGenius 自带的 **grubfile** 目录里那 **三个 `.efi` 文件**拷进这个分区（三个都放上）。
3. 打开 **工具 → 设置 UEFI BIOS 启动项**（或等价的「添加启动项」），启动文件选这三份里的 **一份**：普通 64 位电脑选名字带 `x64` / `BOOTX64` 的；不要选 ia32（32 位）或 aa64（ARM），除非你那台就是那种机器。
4. **保存设置**。分区表和启动项都要存上。

进不去、黑屏：多半选错了那份 EFI，或主板 Secure Boot 拦了未签名的 GRUB——装这一次可先关 Secure Boot。

### 2. ISO 放哪

下好的 `ubuntu-….iso` **直接放在 Windows 的「下载」里即可**，不必拷到盘符根目录，也不必解压。重启后是在 GRUB 的文件浏览里点开它，路径深浅无所谓。

装系统过程中不要删这个 ISO，也不要把它所在的 Windows 分区格式化掉。

### 3. 重启，打开 ISO

重启。在启动菜单里选刚加的那项（grubfile 的那个 EFI）。出来的是 **文件浏览**（不是 Windows 桌面）：进 Windows 对应的那个盘 → 用户目录 → 下载 → 打开 `ubuntu-….iso`，即进入 Ubuntu Live。

找不到盘：换一块磁盘再看；笔记本有时 Windows 在第二块盘上。

### 4. 跟着安装向导（空间在这里划）

桌面上打开 **Install Ubuntu**，键盘、时区、用户名按提示走。

磁盘这一步选 **与 Windows 共存 / Install Ubuntu alongside Windows**。安装器会问 **要从 Windows 划走多少未划分（可用）空间**——把滑条拉到大约 40 GB 以上（评测机建议 80 GB）。**不要**选擦除整块磁盘（Erase disk）。**不要**把系统装进刚才那 128 MB FAT。

有独立 EFI 就让安装器写入**已有的 EFI 分区**，不要再新建一个、不要格式化 Windows 的 NTFS。

装完重启，应出现 Ubuntu 自己的 GRUB（Ubuntu / Windows）。日常评测进 Ubuntu。若直接进 Windows：开机 `F12` 把 **ubuntu** 调到最前，或回 Windows 用 DiskGenius 改 UEFI 顺序。

128 MB 那块只是这次用来点开 ISO 的。双系统都能进之后，可以再进 Windows 用 DiskGenius 删掉它，空间还回去。真正的引导已经是 Ubuntu 写进 EFI 的 GRUB。

然后在 Ubuntu 里按 [server.md](server.md) 部署本仓库。

---

## 常规：U 盘安装（简要）

有 4 GB 以上 U 盘时，这条最省事。

1. 同样关掉 BitLocker 和快速启动。Windows 盘留够可用空间即可，**不必**事先划未分配；安装器会问划走多少。
2. 官网下载 Desktop ISO。
3. 用 [Rufus](https://rufus.ie/) 写盘：分区类型 **GPT**，目标系统 **UEFI**，方案选 ISO。或用 [Ventoy](https://www.ventoy.net/) 把 ISO 拷进盘即可多系统启动盘。
4. 关机，从 U 盘启动（`F12` 等，选该 U 盘的 **UEFI** 项，不要 CSM/Legacy）。
5. 安装向导与上一节相同：与 Windows 共存，滑条划出 ≥40 GB，写入已有 EFI，不要擦盘。
6. 拔掉 U 盘再重启，进 GRUB。

U 盘只是安装介质。评测机是装上之后硬盘里的 Ubuntu，不是每次从 U 盘跑 Live。

---

## WSL2 当作评测机

适合：**同一台 Windows 上自己出题、自己交题、跑 `selftest.py`**。不适合当家里唯一的局域网 OJ（手机、另一台电脑默认连不上 WSL 的网卡）。

### 能做什么、不能做什么

- 能：在 Windows 浏览器打开 `http://127.0.0.1:8080` 做题；八种语言只要 WSL 里 apt 装了就能评。
- 不能替代双系统的部分：`unshare --net` 在 WSL 里经常失败，沙箱会退回「不断网、只用 prlimit」；cgroup 也不如真机完整。耗时榜不要拿 WSL 和家里那台双系统 Ubuntu 比。
- 仓库必须 clone 在 **Linux 文件系统**（`~/leet-hub`），不要放 `/mnt/c/...`。NTFS 上 `npm run build`、编译缓存会极慢，也容易把权限搞乱。

### 安装 Ubuntu 发行版

管理员 PowerShell：

```powershell
wsl --install
```

已有 WSL 时再装 Ubuntu（店里的 Ubuntu，选接近 24.04/26.04 的）：

```powershell
wsl --list --online
wsl --install -d Ubuntu
```

装完后 `wsl --shutdown`，再打开「Ubuntu」终端，创建 Linux 用户。

打开 systemd（`setup-ubuntu.sh` 要写 `/etc/systemd/system/local-leet.service`）：

```bash
sudo tee /etc/wsl.conf >/dev/null <<'EOF'
[boot]
systemd=true
EOF
```

回到 PowerShell 执行 `wsl --shutdown`，再进 Ubuntu，`systemctl --user status` 或 `ps -p 1` 应能看到 systemd。

Windows 11 可在 `%UserProfile%\.wslconfig` 给评测机多留内存，例如：

```ini
[wsl2]
memory=8GB
processors=6
```

改完同样 `wsl --shutdown`。

### 部署本仓库

在 **Ubuntu 终端**（不是 PowerShell）：

```bash
git clone https://github.com/ZhiqiangBao/leet-judge.git ~/leet-judge
cd ~/leet-judge
chmod +x scripts/setup-ubuntu.sh scripts/run-ubuntu.sh scripts/update-from-github.sh
./scripts/setup-ubuntu.sh
```

Windows 浏览器打开：

```text
http://127.0.0.1:8080
```

管理员在 **WSL 里的 Ubuntu 浏览器**或本机回环打开 `http://127.0.0.1:8081` 注册（不要把 8081 做 portproxy 到局域网）。

不要用 `hostname -I` 在局域网里发 WSL 的地址，那是虚拟网卡，家里其它设备通常到不了。

systemd 在 WSL 里偶发不起来时，不要反复纠结 unit，直接前台跑：

```bash
./scripts/run-ubuntu.sh
```

关这个终端服务就停。

### 局域网要访问 WSL 时（可选）

Windows 11 23H2 以后可在 `.wslconfig` 加：

```ini
[wsl2]
networkingMode=mirrored
```

`wsl --shutdown` 后，局域网访问 **Windows 的 IP**:8080 会进到 WSL 里的服务（防火墙放行 8080）。

没有镜像网络时，在 **管理员** PowerShell 做端口转发（WSL 的 IP 每次开机可能变，用 `wsl hostname -I` 看）：

```powershell
netsh interface portproxy add v4tov4 listenaddress=0.0.0.0 listenport=8080 connectaddress=<WSL的IP> connectport=8080
netsh advfirewall firewall add rule name="local-leet-8080" dir=in action=allow protocol=TCP localport=8080
```

家里长期给别人做题，还是装双系统或独立 Ubuntu，不要靠 portproxy。

### 和「开发机」的区别

README 里 Windows 上的 `.venv` + `uvicorn` 是 **改前端/后端用的开发服务**，评测只会调用你碰巧装在 PATH 里的编译器，没有 systemd，也没有 Ubuntu 那套 `unshare`。日常当 OJ 请用：**双系统 Ubuntu**，或本节的 **WSL 内 `setup-ubuntu.sh`**，不要用 PowerShell 里那套开发命令冒充评测机。
