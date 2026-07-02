# Hardware Test Recording

`tests/hardware/` に置くテストは、実行前に会話上の明示承認を必要とする。

## Marker

- USB Bluetooth dongle と Bumble adapter を開くテストには `@pytest.mark.bumble` を付ける。
- 対象機器との pairing、HID channel、report loop、入力反映を扱うテストには `@pytest.mark.hardware` を付ける。

## Log

実行した場合は、結果を `docs/hardware-test-log.md` に記録する。記録には少なくとも command、approval、adapter、dongle、driver、result、artifact、cleanup を含める。

未実行の marker test を成功扱いにしない。承認がない場合は、実行せず `not run` として扱う。

reconnect、input reflection、close 後 UI 確認のように Switch 画面状態で解釈が変わる test は、実行前の Switch UI 起動条件を trace または hardware log に記録する。起動条件が未記録の run は、artifact が残っていても該当シナリオの成功 / 失敗根拠として扱わない。
