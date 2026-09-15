# Leet Judge

[English](README.en.md)

自托管编程评测机。本仓库只有程序，**不含题目**。题目用题包 zip 导入后，管理员再点「发布」，考生才能看见并提交。

[安装](#安装) · [导入题包](#导入题包) · [考生怎么做](#考生怎么做) · [文档](#文档)

支持语言：Python 3、C、C++、JavaScript、TypeScript、Go、Rust、Zig。考生电脑不用装编译器。

## 安装

准备一台 Ubuntu（独立机、双系统或 [WSL](docs/host.md)），然后：

```bash
git clone https://github.com/ZhiqiangBao/leet-judge.git
cd leet-judge
chmod +x scripts/*.sh
./scripts/setup-ubuntu.sh
```

浏览器打开 `http://<主机IP>:8080`。管理员只在本机注册：`http://127.0.0.1:8081`。

服务停了用 `sudo systemctl start local-leet`。不要用重跑安装脚本的方式开机（会改掉已装的 Zig 版本）。

## 导入题包

1. 管理员登录 → **题库 → 本机导入**，上传 zip（不用先解压）。
2. **题库 → 发布**，把要给考生做的题点「发布」。导入后默认不公开。
3. 考生用 `:8080` 自行注册，只能看到已发布的题。

管理员顶栏「题目」能看见全部已导入题，也可自己做。

## 考生怎么做

打开题目，补全空函数。「测试」只跑题面示例、不计分。「提交」跑全部隐藏测例，失败只显示第几号。同一时段内可以重复提交，以最好一次通过为准。

## 文档

| 给谁 | 中文 | English |
| --- | --- | --- |
| 买完题包之后 | [docs/start.zh.md](docs/start.zh.md) | [docs/start.en.md](docs/start.en.md) |
| 考生页面 | [docs/client.md](docs/client.md) | [docs/client.en.md](docs/client.en.md) |
| 管理员按钮 | [docs/admin.md](docs/admin.md) | [docs/admin.en.md](docs/admin.en.md) |
| 装机、开机 | [docs/host.md](docs/host.md)、[docs/server.md](docs/server.md) | 目前仅中文 |
| 题包里有哪些文件 | [docs/problems.md](docs/problems.md) | 目前仅中文 |
| 加编译器 | [docs/toolchains.md](docs/toolchains.md) | 目前仅中文 |
