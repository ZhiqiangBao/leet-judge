# 接入语言

编写适配器（接口、`wrap` 协议、登记清单、JS / TS / Go / Rust / Zig 要点）见 **[adapters.md](adapters.md)**。

类型能否被某语言 wrap，以 [`rules/types.yaml`](../rules/types.yaml) 为准（生成表 [`rules/types.md`](../rules/types.md)）。当前八种语言都能 wrap 词表里的叶子和两层 `List`。题目页只列出「本题签名能 wrap ∩ 可选 `meta.languages` ∩ 主机 `detect()`」；包不住的语言不展示。

主机编译器版本见 [toolchains.md](toolchains.md)。还没有 Linux 评测机见 [host.md](host.md)。排期见 [roadmap.md](roadmap.md)。评测主机安装编译器、题库如何加载、提交队列见 [server.md](server.md)。
