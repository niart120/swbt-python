import pytest

from swbt.transport._exp_local_address import ExpLocalAddress


def test_exp_local_address_accepts_individual_locally_administered_value() -> None:
    address = ExpLocalAddress.parse("02:12:34:56:78:9a")

    assert str(address) == "02:12:34:56:78:9A"
    assert address.bytes == bytes.fromhex("02 12 34 56 78 9A")


@pytest.mark.parametrize(
    ("value", "message"),
    [
        ("02:12:34:56:78", "6 octets"),
        ("03:12:34:56:78:9A", "individual"),
        ("00:12:34:56:78:9A", "locally administered"),
        ("02:12:34:9E:8B:00", "reserved inquiry LAP"),
        ("02:12:34:9E:8B:33", "reserved inquiry LAP"),
        ("02:12:34:9E:8B:3F", "reserved inquiry LAP"),
    ],
)
def test_exp_local_address_rejects_values_outside_profile_contract(
    value: str,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        ExpLocalAddress.parse(value)


def test_exp_local_address_allows_values_adjacent_to_reserved_lap() -> None:
    assert str(ExpLocalAddress.parse("02:12:34:9E:8A:FF")) == "02:12:34:9E:8A:FF"
    assert str(ExpLocalAddress.parse("02:12:34:9E:8B:40")) == "02:12:34:9E:8B:40"
