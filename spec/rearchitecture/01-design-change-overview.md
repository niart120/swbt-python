# 01. 設計変更概要

## Summary

現行 Joy-Con 対応では、profile-aware な report / subcommand / transport への道筋はできている。一方で、public API は `JoyCon` が具象 `SwitchGamepad` を継承し、`SwitchGamepadConfig` で profile 注入でき、テスト用 transport も constructor に渡せる形になっている。

この形は短期的には便利だが、controller identity、runtime lifecycle、public config、test seam が同じ場所に集まりすぎている。リアーキテクチャでは、identity selection を public concrete class に閉じ、runtime 機構を private implementation に移す。

```text
Target public inheritance

SwitchGamepad                # abstract public interface。受け取る型
  ↑
_RuntimeBackedGamepad        # private delegation base。export しない
  ↑
  ├─ ProController           # public concrete controller
  ├─ JoyConL                 # public concrete controller
  └─ JoyConR                 # public concrete controller
```

中心ルールは次である。

> Public class が controller identity を選ぶ。Public constructor は resource と利用者向け option だけを受け取る。

## 確定判断

以下は、maintainer が明示的に再検討しない限り、このリアーキテクチャの前提とする。

1. `SwitchGamepad` は具象 controller ではなく、直接生成できない public abstract interface にする。
2. public concrete controller は `ProController`、`JoyConL`、`JoyConR` の 3 つにする。
3. `JoyCon(side="left" | "right")` は削除する。互換 wrapper として残さない。
4. `SwitchGamepadConfig(profile=...)` は public API から削除する。
5. public constructor では `profile`、`kind`、`device_name`、`device_type`、HID descriptor、SDP policy、button map、`transport` を受け取らない。
6. `ControllerProfile` と具象 profile class は内部実装詳細にする。`ControllerColors` は public のまま残す。
7. test transport injection は内部 factory または test helper に隠す。public constructor には出さない。
8. この変更は breaking change とする。`JoyCon = JoyConL` や `SwitchGamepad = ProController` のような root-level alias は残さない。
9. `JoyConPair` は本設計の範囲外にする。将来、`JoyConL` / `JoyConR` を束ねる上位 orchestration layer として扱う。

## Problem statement

現状の public API は、Pro Controller 中心の初期 API に Joy-Con support を追加した形である。

```python
from swbt import SwitchGamepad, JoyCon, SwitchGamepadConfig

pad = SwitchGamepad(adapter="usb:0")
left = JoyCon("left", adapter="usb:0")
right = JoyCon("right", adapter="usb:0")
```

`SwitchGamepadConfig` は `profile` を持つため、controller identity を public config 経由で差し替えられる。

```python
config = SwitchGamepadConfig(profile=JoyConLeftProfile())
pad = SwitchGamepad.from_config(config, transport=FakeHidTransport())
```

この構造の問題は、次の 4 つの責務が public class 周辺に集まりすぎている点にある。

1. 利用者向け public API。
2. controller identity / profile selection。
3. runtime lifecycle と connection state。
4. test / transport injection seam。

## 目標 public usage

Controller 作成は concrete class で行う。

```python
import asyncio

from swbt import Button, JoyConL, JoyConR, ProController, SwitchGamepad


async def run_script(pad: SwitchGamepad) -> None:
    await pad.connect(timeout=30.0, allow_pairing=True)
    await pad.tap(Button.A)
    await pad.neutral()


async def main() -> None:
    async with ProController(
        adapter="usb:0",
        key_store_path="keys/pro-controller.json",
    ) as pad:
        await run_script(pad)

    async with JoyConL(
        adapter="usb:0",
        key_store_path="keys/joycon-l.json",
    ) as left:
        await left.connect(timeout=30.0, allow_pairing=True)
        await left.tap(Button.SR, Button.SL)

    async with JoyConR(
        adapter="usb:0",
        key_store_path="keys/joycon-r.json",
    ) as right:
        await right.connect(timeout=30.0, allow_pairing=True)
        await right.tap(Button.SR, Button.SL)


asyncio.run(main())
```

`SwitchGamepad` は直接作成しない。任意 controller を受け取る型として使う。

```python
async def accept_any_controller(pad: SwitchGamepad) -> None:
    await pad.connect(timeout=30.0, allow_pairing=True)
    await pad.tap(Button.A)
```

## 採用しない代替案

### Alternative A: `JoyCon(side=.)` を残す

却下。side selection が runtime value として残り、invalid side の public error path も残る。型補完・docs・テストも `JoyConL` / `JoyConR` より曖昧になる。

### Alternative B: `SwitchGamepad` を concrete のまま残し `ProController` を alias にする

却下。`ProController`、`JoyConL`、`JoyConR` が存在するなら、concrete `SwitchGamepad` の identity が曖昧になる。`SwitchGamepad` は interface にするべきである。

### Alternative C: `SwitchGamepadConfig(profile=.)` を advanced API として残す

却下。Profile injection は内部では必要だが、public に残すと concrete class の identity guarantee を壊す。

### Alternative D: test / power user 用に `transport=` を残す

却下。Public constructor からは消す。内部 `_TransportFactory` と test helper で十分である。Backend extensibility は別設計にする。

## Success criteria

1. `SwitchGamepad` は abstract で direct instantiate できない。
2. `ProController`、`JoyConL`、`JoyConR` だけが public concrete controller class である。
3. Public constructor に `profile`、`device_name`、`transport` がない。
4. Controller identity は concrete controller class の内部で一度だけ選ばれる。
5. Runtime lifecycle は `ControllerRuntime` が持ち、`SwitchGamepad` は持たない。
6. Bluetooth hardware なしでも内部 test helper で unit test できる。
7. Root public API と docs から `JoyCon(side=...)` と `SwitchGamepadConfig(profile=...)` が消えている。
8. `ControllerKind` 分岐が runtime / transport に漏れていない。
9. 未検証 Joy-Con behavior が、docs 上で検証済みのように書かれていない。

## Scope note

これは既存 convenience API を温存する互換方針ではない。pre-alpha のうちに public surface を小さくし、controller identity の所有者を明確化する cleanup 方針である。短期的な破壊的変更を受け入れる代わりに、長期の説明負荷と誤用可能性を減らす。
