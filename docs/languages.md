# 接入语言

要给评测机加一种编程语言，写法见 **[adapters.md](adapters.md)**。

一道题的下拉框只列出：函数签名该语言接得上、题目没有禁用它、并且这台评测机已经装好对应编译器。接不上的语言不会出现。类型对照见 [`docs/types.yaml`](types.yaml)。当前八种语言都能接到整数、长整数、小数、真假值、字符串，以及一层、两层列表。

主机编译器版本见 [toolchains.md](toolchains.md)。还没有 Linux 评测机见 [host.md](host.md)。评测主机安装编译器、题库如何加载、提交队列见 [server.md](server.md)。
