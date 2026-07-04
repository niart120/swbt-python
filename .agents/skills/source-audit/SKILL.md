---
name: source-audit
description: "swbt-python の Switch HID、Bumble HID Device、既存 swbt 実装、Linux hid-nintendo、joycontrol、実機ログを監査し、report bytes、subcommand、SPI address、HID descriptor、SDP、report timing、WinUSB/libusb 仮定の根拠を分類して記録する skill。protocol 定数、magic number、driver や adapter の仮定を実装または仕様化するときに使う。"
---

# 根拠監査

Switch HID、Bumble、Bluetooth adapter、driver、実機観測に関する値を安定した事実として扱う前に使う。

## 根拠の分類

| 分類 | 意味 |
|---|---|
| `source fact` | upstream source、文書、固定済み commit で直接確認した事実。 |
| `implementation fact` | 既存 `swbt` 系実装またはローカル test で確認した事実。 |
| `hardware observation` | Nintendo Switch 実機または Bluetooth dongle で観測した値。 |
| `inference` | 複数の事実から推論したが直接検証していない内容。 |
| `unverified hypothesis` | もっともらしいが契約として実装してはいけない未検証仮説。 |

分類を混ぜない。実機観測は OS、driver、dongle、Switch firmware、Bumble version の差分を一緒に記録する。

## 優先する参照元

- `spec/initial/*.md`。
- 既存 `swbt` C 実装と protocol spec。
- 既存 `swbt` の実機検証ログ。
- Bumble documentation と HID Device example。
- Linux `hid-nintendo.c`。
- `joycontrol` の実装。
- dekuNukem の Nintendo Switch reverse engineering notes。
- ローカル characterization test。

## 監査が必要な変更

- HID descriptor bytes。
- input report ID、output report ID、report packing。
- button bit、stick packing、IMU frame。
- subcommand ID と response payload。
- SPI flash address と返却 data。
- rumble packet layout。
- report period の default と fallback。
- SDP record、L2CAP channel、Bumble HID Device helper の仮定。
- WinUSB / libusb / OS driver の仮定。
- Bluetooth dongle や Switch firmware に依存する挙動。

## 記録ルール

監査した値ごとに次を記録する。

- 値と意味。
- 根拠分類。
- source path、URL、commit、version。行番号は取得できる場合だけでよい。
- stable、configurable、hardware-observed only の区別。
- まだ不足している確認。

大きな判断は関連する `spec/wip/unit_XXX` または `spec/initial` に残す。小さい観測は `spec/dev-journal.md`、実機測定値は `spec/hardware-test-log.md` に残す。

## Safety

- source または characterization test がない Switch protocol constant を確定値として扱わない。
- hardware observation を別 OS、別 driver、別 dongle、別 firmware の一般事実にしない。
- adapter open や Switch-facing 動作が必要な確認は `hardware-harness` の承認境界を通す。
- 未検証仮説を public API や安定 spec の前提にしない。

## Output

```markdown
### 根拠監査

| 項目 | 値 | 根拠分類 | source | status |
|---|---:|---|---|---|

### 未解決事項

- ...
```
