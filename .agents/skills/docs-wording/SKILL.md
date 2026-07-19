---
name: docs-wording
description: "swbt-python の README、docs、release notes、公開 API 説明の日本語文言整理で、プロジェクト固有の訳語、残す英語表記、トレース出力やペアリング情報などの用語をそろえる skill。ユーザが docs 文言整理、用語辞書、訳語統一、release notes の表現確認を依頼したときに使う。"
---

# Docs Wording

swbt-python の公開ドキュメントでは、利用者が API と実機条件を誤読しない語を選ぶ。
コード上のクラス名、メソッド名、引数名、状態値は変更せず、本文中の説明語をそろえる。

## 使い方

- README、`docs/`、release notes、公開 API 説明を編集する前に、[用語辞書](references/terminology.md)を全文読む。
- 既存の API 名、インポート名、CLI オプション、状態値はそのまま残す。
- 実機未検証、OS、ドライバー、アダプタ、対象機器に依存する観測は断定しない。
- `japanese-tech-writing` を併用する場合でも、用語辞書を swbt-python 固有の判断として優先する。
- 地の文に残る英単語を確認し、公開識別子、規格名、単位、固有名詞以外は用語辞書に従って日本語化する。
- 英語の分類名を残す必要がある場合は、裸の接頭語ではなく完全な公開クラス名を記載する。
- 文言変更後は、対象文書のテスト、`git diff --check`、関連するドキュメント生成を実行する。

## Release Notes

- Breaking changes は「前バージョンの利用者のコードがどう壊れるか」を箇条書きで書く。
- 新規追加 API は breaking changes ではなく migration または feature 説明に置く。
- 過去バージョンに存在しない API を Old API として書かない。
- 「利用者向け生成 API」のような上位語だけでまとめず、影響を受ける constructor や呼び出し形を直接書く。
- README と release notes では、実機検証の protocol ID、trace 条件、artifact 名まで書かない。通常利用者に必要な対応状況だけを書き、詳細は `docs/hardware.md` と `spec/hardware-test-log.md` に任せる。
- 実際の差分に基づく記述を行う。`SwitchGamepad` を直接生成できない、`SwitchGamepadConfig` と transport 注入が公開 API から外れた、トップレベル export が消えた、など。
