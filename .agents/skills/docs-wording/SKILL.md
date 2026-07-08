---
name: docs-wording
description: "swbt-python の README、docs、release notes、公開 API 説明の日本語文言整理で、プロジェクト固有の訳語、残す英語表記、トレース出力やペアリング情報などの用語をそろえる skill。ユーザが docs 文言整理、用語辞書、訳語統一、release notes の表現確認を依頼したときに使う。"
---

# Docs Wording

swbt-python の公開ドキュメントを直すときは、一般的な日本語化ではなく、利用者が API と実機条件を誤読しない語を選ぶ。
コード上の class、method、引数名、status 値は原則として変更せず、本文中の説明語をそろえる。

## 使い方

- README、`docs/`、release notes、公開 API 説明を編集するときに参照する。
- 既存の API 名、import 名、CLI option、status 値はそのまま残す。
- 実機未検証、OS、ドライバー、アダプタ、対象機器に依存する観測は断定しない。
- `japanese-tech-writing` を併用する場合でも、この skill の用語辞書を swbt-python 固有の判断として優先する。

## 用語辞書

| 対象 | 推奨表記 | 残す表記 / 避ける揺れ | 方針 |
|---|---|---|---|
| USB Bluetooth 機器 | 専用 USB Bluetooth ドングル | `USB Bluetooth dongle`, `Bluetooth dongle`, `Bluetoothドングル` | 利用者が物理機器として読む箇所では日本語寄りにする。PC 内蔵 Bluetooth と区別する文脈では `専用` を付ける。 |
| OS 側の準備 | ドライバー | `driver` | Windows 手順や Zadig の説明では日本語表記へ寄せる。 |
| firmware | ファームウェア / FW バージョン | `firmware` | 公開 docs の本文では `ファームウェア` を基本にする。バージョン表記を短く示す箇所では `FW バージョン` も使える。 |
| adapter | アダプタ | `adapter` | 利用者手順では `アダプタ`。コード引数 `adapter`、Bumble の adapter string はそのまま残す。 |
| adapter name | アダプタ名 / アダプタの名称 | `adapter 名`, `adapter moniker` | 利用者が `adapter=...` に渡す値として読む箇所では `アダプタ名` を使う。 |
| pairing | ペアリング | `pairing` | API 名、`allow_pairing`、`pair()` はそのまま。説明文では `ペアリング` を使う。 |
| reconnect | 再接続 | `reconnect` | メソッド名 `reconnect()` はそのまま。説明文では `再接続` を使う。 |
| HID advertising | HID 接続待ち受け | `advertising`, `HID advertising` | 対象機器から見える接続待機動作として説明する場合に使う。 |
| periodic report loop | レポートループ | `periodic report loop`, `report loop` | 入力レポート送信の周期処理を説明する語。 |
| input report | 入力レポート / レポート | `input report`, `report` | HID 文脈では `入力レポート` が明確。直前の文脈で HID 入力が明らかな場合だけ `レポート` でもよい。 |
| diagnostics | トレース出力 | `diagnostics`, `診断`, `ロギング` | API 名 `DiagnosticsConfig` や引数名 `diagnostics` は残す。本文では、原因を自動判定する機能ではなく JSON Lines の実行記録を出す機能として `トレース出力` を使う。 |
| trace | トレースログ / トレース | `trace`, `JSON Lines trace` | ファイルに残る実行記録は `トレースログ`。引数名、変数名、ファイル名では `trace` を残す。実機ログや根拠監査とは分ける。 |
| key store | key store / 接続情報ファイル | `JSON key store path`, `接続情報ファイル` | API 詳細では `key store` を残す。利用者手順でファイルとして説明する場合は `接続情報ファイル` を使える。 |
| bond | 保存済みペアリング情報 / ペアリング情報 | `bond`, `保存済み接続情報` | ペアリング後に保存される鍵と相手機器情報を指す。利用者向け説明では `保存済みペアリング情報` を第一候補にする。短い箇所では `ペアリング情報` を使う。 |
| button | ボタン | `button` | enum 名や型名はそのまま。説明文では `ボタン` を使う。 |
| stick | スティック | `stick` | 型名 `Stick` はそのまま。説明文では `スティック入力` を使う。 |
| D-pad | 十字キー | `D-pad` | Joy-Con や入力説明では `十字キー` を使う。 |
| neutral | ニュートラル | `neutral` | `neutral()` は API 名として残す。入力状態の説明では `ニュートラル入力` を使う。 |
| timeout | タイムアウト | `timeout` | 例外名や status 値はそのまま。説明文では `タイムアウト` を使う。 |
| error thrown | 送出されます | `投げます`, `返します` | 例外説明では `送出されます` に寄せる。 |
| concrete controller | 具象クラス | `concrete controller` | 型説明では `具象クラス` を使う。class 名そのものは残す。 |
| public API | 公開 API | `public API`, `公開API` | 日本語本文では `公開 API` に統一する。 |
| transport | transport | `トランスポート` | API 境界語として英語のまま残す。利用者向けに説明を補う場合は「下位の通信実装」と言い換える。 |
| profile | profile / プロファイル | `profile`, `プロファイル` | controller profile は `profile` を残してよい。色や説明上の属性は `プロファイル` としてもよい。文書内で揺らさない。 |
| IMU frame | IMU frame / IMU 入力単位 | `frame`, `入力単位` | API 詳細では `IMU frame` を使う。利用者向けには `IMU 入力単位` を併記できる。 |
| accelerometer / gyroscope | 加速度 / ジャイロ | `accelerometer`, `gyroscope`, `gyro` | `gyro` は API 名として残す。説明では日本語補足を付ける。 |
| troubleshooting | トラブルシューティング | `troubleshooting` | docs 導線や本文では日本語化する。 |

## Release Notes

- Breaking changes は「前バージョンの利用者のコードがどう壊れるか」を箇条書きで書く。
- 新規追加 API は breaking changes ではなく migration または feature 説明に置く。
- 過去バージョンに存在しない API を Old API として書かない。
- 「利用者向け生成 API」のような上位語だけでまとめず、影響を受ける constructor や呼び出し形を直接書く。
- README と release notes では、実機検証の protocol ID、trace 条件、artifact 名まで書かない。通常利用者に必要な対応状況だけを書き、詳細は `docs/hardware.md` と `spec/hardware-test-log.md` に任せる。
- 実際の差分に基づく記述を行う。`SwitchGamepad` を直接生成できない、`SwitchGamepadConfig` と transport 注入が公開 API から外れた、トップレベル export が消えた、など。
