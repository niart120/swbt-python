# Linux / macOS Adapter Experimental 仕様書

## 1. 概要

### 1.1 目的

Linux / macOS の USB Bluetooth adapter 対応を、確認済み対応ではなく experimental target として扱う。USB Bluetooth dongle、OS の Bluetooth stack 設定、Nintendo Switch 実機での検証はこの unit の完了条件に含めない。repo 側で行うのは、Bumble の USB transport 前提に沿った準備手順の文書化、no-open diagnostics の整備、macOS CI の no-hardware gate、未確認範囲の明示までとする。

この unit は `spec/dev-journal.md` の 2026-07-04 entry から昇格した。ただし昇格時点で方針を変更し、journal にあった「adapter open / smoke test まで確認する」完了条件は採用しない。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| user request | Linux / macOS adapter 対応を experimental として spec 化し、実機・実OSでの adapter 検証は行わない | conversation |
| user follow-up | 実ハードなしの CI 経路で macOS 側も一定の保証を持つ。現行 CI は `ubuntu-latest` のみ | conversation |
| dev journal | Linux / macOS adapter 準備の観測と後続化候補 | `spec/dev-journal.md` |
| CI workflow | 現行 CI は Python 3.12 / 3.13 を `ubuntu-latest` で実行する | `.github/workflows/ci.yml` |
| transport design | OS 別 adapter 注意点と Bumble transport 境界 | `spec/initial/transport-bumble.md` |
| testing design | Bumble adapter tests と hardware tests の分類 | `spec/initial/testing.md` |
| risks | OS / driver 差分、未確認構成、release gate の確認済み範囲 | `spec/initial/risks.md` |
| public hardware docs | Windows 確認済み構成、Linux / macOS の現行 unsupported / untrusted 表現 | `docs/hardware.md` |
| Bumble USB docs | `usb:` moniker、`libusb-1.0` requirement、`usb_probe` / `lsusb` guidance | https://github.com/google/bumble/blob/main/docs/mkdocs/src/transports/usb.md |
| local dependency lock | Bumble 0.0.230、`libusb1`、`libusb-package` dependency | `uv.lock` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| Linux user | hardware guide を読む | experimental であり、実機接続確認済みではないことが分かる | Linux 上の command 実行結果を書かない |
| macOS user | hardware guide を読む | 準備候補と未確認リスクが分かる | NVRAM など OS 設定を保証済み手順として扱わない |
| developer | `swbt-probe adapters --json` | adapter を開かず、platform / Python / Bumble version と no-open 境界を確認できる | Linux/macOS の実USB列挙を完了条件にしない |
| CI | macOS runner | import、unit tests、fake transport integration、package build が macOS 上で通る | USB adapter open と Switch-facing 動作は含めない |
| maintainer | release docs を確認する | Windows 確認済み構成と Linux/macOS experimental が分かれている | package metadata で Linux/macOS supported と主張しない |

## 2. 対象範囲

- Linux / macOS を `unsupported / untrusted` ではなく `experimental` として扱う文書方針。
- Linux / macOS の準備手順を、Bumble USB transport 前提と OS 設定候補に分けて書く。
- Linux/macOS 上の adapter listing、adapter open、HID advertising、Switch pairing、report loop、入力反映を完了条件から外す。
- `swbt-probe adapters --json` の no-open 境界を Linux/macOS experimental の診断入口として明示する。
- public docs と README で、Windows 確認済み構成と Linux/macOS experimental を混ぜない。
- GitHub Actions の macOS runner で、実ハードなしの automated gate を通す。
- docs drift を防ぐ unit test の更新。
- `spec/initial/risks.md` の未確認範囲を、保証外のまま experimental target として読める表現に直す。

## 3. 対象外

- Linux 上での command 実行。
- macOS 上での adapter listing、adapter open、OS Bluetooth stack 設定変更。
- USB Bluetooth dongle を Bumble から開くこと。
- `@pytest.mark.bumble` / `@pytest.mark.hardware` の実行。
- Linux / macOS での pairing、reconnect、input reflection の確認。
- Linux / macOS を package classifier や README で supported と主張すること。
- CI 上で USB Bluetooth dongle を要求すること。
- CI 上で macOS の Bluetooth stack、NVRAM、USB permission を変更または検証すること。
- macOS NVRAM 設定、Linux udev rule、BlueZ 競合解消の正しさをこの unit で証明すること。
- CSR8510 A10 以外の dongle 対応保証。

## 4. 関連 docs

- `spec/initial/README.md`
- `spec/initial/transport-bumble.md`
- `spec/initial/testing.md`
- `spec/initial/risks.md`
- `spec/complete/unit_008/M7_PACKAGING_EXAMPLES_CLI.md`
- `spec/complete/unit_011/HARDWARE_TEST_LOG_MATRIX.md`
- `spec/complete/unit_012/INITIAL_RELEASE_GATE.md`
- `spec/complete/unit_022/PUBLIC_API_USAGE_HARDWARE_DOCS.md`
- `docs/hardware.md`
- `README.md`
- `.github/workflows/ci.yml`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | not applicable | not applicable | この unit は Switch-facing bytes、subcommand、report loop を変更しない |
| Bumble / transport | required | source-fact-for-usb-docs | Bumble USB docs は `usb:` moniker、default USB transport が `libusb1` ベースであること、`libusb-1.0` requirement、`usb_probe` / `lsusb` による列挙を示す |
| Bumble / transport | required | implementation-fact | `uv.lock` は Bumble 0.0.230 と `libusb1` / `libusb-package` dependency を含む |
| OS / driver / adapter | required | existing-docs-and-not-run | `docs/hardware.md` は Linux の権限・BlueZ 競合、macOS の外付け HCI 設定候補を書いている。ただしこの turn ではその OS 手順の実行確認をしていない |
| OS / driver / adapter | required | not-run-by-policy | Linux/macOS 上の adapter listing、adapter open、pairing、input reflection はこの unit では実行しない。macOS CI は no-hardware gate に限定する |

### 未解決事項

- Linux の具体的 udev rule と BlueZ 解放手順は、現時点では準備候補であり、repo の確認済み手順ではない。
- macOS の外付け HCI を OS Bluetooth stack に掴ませない設定は、現時点では準備候補であり、repo の確認済み手順ではない。
- Bumble 0.0.230 で Linux/macOS の `usb:` transport が `swbt-python` の HID Device 初期化まで進むかは未確認。

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| docs classification | Linux / macOS sections | `experimental` として表示する | Windows confirmed と分ける |
| no-adapter policy | unit completion | Linux/macOS 上で adapter command を実行しなくても完了できる | macOS CI は no-hardware command に限定する |
| preparation guidance | Linux / macOS setup text | Bumble source fact、既存 docs 由来の準備候補、未検証事項を分ける | 保証文にしない |
| no-open diagnostics | `swbt-probe adapters --json` | `opens_adapter=false`、platform、Python、Bumble version を返す | 実USB列挙の成功を要求しない |
| macOS CI smoke | GitHub Actions `macos-latest` | `uv sync --locked --dev`、unit tests、fake integration、package build が通る | `bumble` / `hardware` marker は実行しない |
| CI scope control | workflow matrix | macOS job は no-hardware gate であり、adapter open を含む command を入れない | 実OSでの adapter 動作保証ではない |
| package metadata | `pyproject.toml` classifiers | Linux/macOS supported classifier を追加しない | experimental target は supported claim ではない |
| README summary | hardware section | 確認済み Windows と Linux/macOS experimental が読める | `unsupported` 固定表現は緩めるが保証はしない |
| hardware matrix | docs / risks | Linux/macOS の未検証状態が残る | 実機 log を捏造しない |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| todo | `docs/hardware.md` が Linux / macOS を `experimental` として扱い、supported と書かない | docs regression | unit | no | 現行の `unsupported / untrusted` 表現を置き換える |
| todo | `docs/hardware.md` が Linux / macOS の準備手順を source fact、準備候補、未確認事項に分ける | docs regression | unit | no | NVRAM や BlueZ 解放を確認済み手順として書かない |
| todo | README が Windows confirmed と Linux/macOS experimental を分けて要約する | docs regression | unit | no | PyPI rendering 用の https docs link は維持する |
| todo | public docs tests が `unsupported` 固定ではなく experimental 境界を確認する | regression | unit | no | `tests/unit/test_public_docs.py` と `tests/unit/test_readme_docs.py` |
| todo | `swbt-probe adapters --json` の no-open contract が Linux/macOS experimental の入口として test される | regression | unit | no | 実USB列挙や adapter open はしない |
| todo | CI が `macos-latest` で no-hardware gate を実行する | regression | unit / integration | no | unit、fake integration、build。`pytest -m bumble` / `pytest -m hardware` は含めない |
| todo | CI workflow の OS matrix が ubuntu と macOS の両方を含むことを unit test で固定する | regression | unit | no | workflow drift 防止。必要なら `tests/unit/test_ci_workflow.py` を追加する |
| todo | `pyproject.toml` に Linux/macOS supported classifier を追加しないことを docs または test で確認する | regression | unit | no | supported claim の混入防止 |
| todo | `spec/initial/risks.md` が Linux/macOS を未確認のまま experimental target として扱う | docs regression | unit | no | release gate の Windows confirmed は維持する |
| deferred | Linux/macOS で `swbt-probe adapters --json` を実行する | characterization | bumble | yes | この unit では実行しない。方針変更があった場合だけ別 unit |
| deferred | Linux/macOS で adapter open / HID Device init を行う | characterization | bumble | yes | この unit では実行しない。明示承認と別 unit が必要 |
| deferred | Linux/macOS で pairing / reconnect / input reflection を確認する | characterization | hardware | yes | この unit では実行しない。supported claim の前提になる |

## 8. 設計メモ

- `experimental` は「試すための準備情報を出す」という意味に限定する。repo が Linux/macOS 動作を確認済み、または release gate として要求済みという意味ではない。
- `unsupported / untrusted` という語は、利用者には「対象外」と読める。今回の方針では、保証外のまま試験的対象として文書化する。
- `swbt-probe adapters` は adapter を開かない。Linux/macOS 向けにもこの境界を守る。実USB列挙を強める場合も、mock 可能な境界で unit test を先に書く。
- Linux/macOS の OS 設定は、repo が実行して確認した事実ではない。文書では「Bumble の USB transport を使うための準備候補」として扱う。
- macOS CI で得られる保証は「パッケージが macOS runner 上で依存解決、import、unit test、fake transport integration、build まで壊れていない」ことに限る。USB adapter open、HID advertising、pairing、input reflection の保証ではない。
- package metadata の OS classifier は確認済み対応範囲を示すため、Linux/macOS classifier はこの unit では追加しない。
- `docs/hardware-test-log.md` には実行していない Linux/macOS run entry を追加しない。matrix や notes の未確認表現だけを必要に応じて更新する。

## 9. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `spec/wip/unit_026/LINUX_MACOS_ADAPTER_EXPERIMENTAL.md` | new | この作業仕様 |
| `spec/dev-journal.md` | modify | 昇格済みの journal entry を削除する |
| `docs/hardware.md` | modify | Linux / macOS experimental 文書化 |
| `README.md` | modify | 確認済み Windows と Linux/macOS experimental の要約 |
| `tests/unit/test_public_docs.py` | modify | public docs の experimental 境界を固定 |
| `tests/unit/test_readme_docs.py` | modify | README の experimental 境界を固定 |
| `tests/unit/test_probe_cli.py` | modify | no-open adapter diagnostics の contract を必要に応じて補強 |
| `tests/unit/test_ci_workflow.py` | add / modify | CI の OS matrix と no-hardware 境界を固定 |
| `.github/workflows/ci.yml` | modify | macOS runner を no-hardware gate に追加 |
| `spec/initial/risks.md` | modify | Linux/macOS 未確認範囲を experimental target として整理 |
| `docs/hardware-test-log.md` | inspect / optional modify | 未実行 run を追加せず、matrix 文言だけ必要なら更新 |
| `pyproject.toml` | inspect | Linux/macOS supported classifier を追加しない |

## 10. 検証

| command | result | notes |
|---|---|---|
| `uv run pytest tests/unit/test_public_docs.py tests/unit/test_readme_docs.py tests/unit/test_probe_cli.py -q` | pending | docs / test 実装後に実行する |
| `uv run pytest tests/unit/test_ci_workflow.py -q` | pending | CI workflow 更新後に実行する |
| `uv run ruff format --check .` | pending | docs / test 実装後に実行する |
| `uv run ruff check .` | pending | docs / test 実装後に実行する |
| `uv run ty check --no-progress` | pending | Python 実装を変更した場合に実行する |
| `uv run pytest -m bumble` | not run | この unit では Linux/macOS も Windows も adapter open を行わない |
| `uv run pytest -m hardware` | not run | この unit では Switch-facing 動作を行わない |
| Linux 上の command | not run | この unit では Linux runner や Linux 実機環境での確認は行わない |
| macOS adapter command | not run | macOS CI は no-hardware gate に限定し、adapter listing / open / OS Bluetooth stack 設定変更は行わない |

## 11. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | not required |
| 承認範囲 | なし。この unit では adapter open、HID advertising、pairing、report loop、Switch-facing output report を実行しない |
| adapter | 未使用。文書例として `usb:0` を出す場合も固定値扱いしない |
| 実行遮断 | 環境変数による遮断は採用しない。実行しないことを unit scope として管理する |
| log / artifact | docs diff、unit test output |
| cleanup | 実機・dongle を使わないため不要 |

## 12. 先送り事項

- Linux/macOS 実OSでの adapter listing / open。
- Linux/macOS での adapter open / close。
- Linux/macOS での HID advertising、pairing、reconnect、input reflection。
- Linux/macOS supported classifier の追加。
- OS 別の udev rule、BlueZ 操作、macOS NVRAM 設定の確定手順化。
- macOS CI で no-hardware gate を越えて adapter を開く検証。

## 13. チェックリスト

- [x] dev-journal entry から作業仕様へ昇格した
- [x] 実機・adapter 検証を行わない方針を完了条件に反映した
- [x] 根拠監査で source fact、implementation fact、未検証事項を分けた
- [x] TDD Test List の初期案を作成した
- [x] 実機実行条件を `not required` として記録した
- [x] macOS CI で保証する範囲を no-hardware gate として記録した
- [ ] public docs と README の experimental 表現を更新した
- [ ] GitHub Actions に macOS no-hardware gate を追加した
- [ ] docs / CLI contract の unit tests を更新した
- [ ] 検証結果または未実行理由を実行結果で更新した
