---
name: hardware-harness
description: "swbt-python で Nintendo Switch、Bluetooth Classic HID、専用 USB Bluetooth dongle、Bumble adapter、WinUSB/libusb、pairing、HID advertising、report loop、hardware pytest marker を扱う検証の安全境界と記録項目を確認する skill。Bumble adapter open、Switch-facing command、実機テスト、manual bring-up を実行、設計、報告する前に使う。"
---

# 実機検証

Nintendo Switch または専用 USB Bluetooth dongle と通信し得る作業の前に使う。

## 承認境界

ユーザが範囲を明示承認していない限り、次を実行しない。

- Bumble から USB Bluetooth dongle を開く。
- Bluetooth Classic HID Device として初期化する。
- discoverable / connectable / HID advertising に入る。
- Switch pairing。
- HID control / interrupt channel を開く。
- periodic input report loop。
- `@pytest.mark.bumble` または `@pytest.mark.hardware` のテスト。

環境変数による実行遮断は採用しない。承認は、会話上の明示承認、対象 adapter、実行 command、Switch-facing 動作の範囲、cleanup plan が揃っているかで判断する。

## 実行前チェック

- 専用 USB Bluetooth dongle を使っている。
- 内蔵 Bluetooth や常用 adapter を使っていない。
- adapter string が具体的である。例: `usb:0`。
- OS と driver state を記録する。Windows では WinUSB assignment を確認する。
- Python version と Bumble version を記録する。
- branch、commit、未コミット変更の有無を確認する。
- Switch model と firmware が分かる場合は記録する。
- cleanup behavior が分かる。
- neutral fail-safe が必要な操作では、送信停止と neutral 復帰の扱いを確認する。

## Stop Conditions

- adapter が曖昧である。
- 常用 Bluetooth adapter の可能性がある。
- 承認が adapter open、advertising、pairing、report loop、test scope のどれを対象にするか示していない。
- cleanup behavior が不明である。
- button pressed が残り得るのに neutral fail-safe がない。

## 記録先

実機観測は `docs/hardware-test-log.md` に記録する。ファイルがなければ作る。

```markdown
## YYYY-MM-DD: <短い題名>

- OS:
- environment:
- adapter:
- dongle:
- driver:
- Python:
- Bumble:
- swbt-python:
- Switch model:
- Switch firmware:
- report period:
- command / test:
- approval:
- result:
- artifact:
- cleanup:
- notes:
```

## pytest marker

- `@pytest.mark.bumble`: Switch 実機なしでも USB Bluetooth dongle と Bumble adapter が必要。
- `@pytest.mark.hardware`: Switch 実機、pairing、HID channel、input reflection が必要。

CI ではどちらも必須 gate にしない。

## 報告

実機または dongle を使っていない場合も理由を明示する。使った場合は、承認範囲、command、adapter identity、結果、artifact、cleanup result を報告する。
