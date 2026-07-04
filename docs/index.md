# swbt-python ドキュメント

`swbt-python` は、Python から NX 向けの仮想 Bluetooth HID 入力デバイスを扱うためのライブラリです。

このサイトは、README に置くには長い API 仕様、利用例、実機条件、AI エージェント向けの短縮仕様をまとめます。README は導入と最小例の入口に留め、詳細はここから各文書へ辿る構成にします。

## 文書一覧

- [docs/api.md](api.md): 公開 API、import、接続 API、入力 API、例外の仕様。
- [docs/usage.md](usage.md): 初回 pairing、reconnect、button、stick、neutral など目的別の利用例。
- [docs/hardware.md](hardware.md): 実機、Bluetooth adapter、driver、pairing / reconnect、troubleshooting。
- [docs/agent-brief.md](agent-brief.md): AI エージェントが未実装 API を作らないための短い仕様。

実機や Bluetooth adapter に依存する情報は [docs/hardware.md](hardware.md) を参照してください。実機観測の正本は [docs/hardware-test-log.md](hardware-test-log.md) です。
