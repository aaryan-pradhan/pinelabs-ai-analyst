import pytest

from decomposition import decompose


def test_rate_change_carries_its_95_percent_interval():
    d = decompose({"upi": (10_000, 0.90)}, {"upi": (10_000, 0.92), "wallet": (500, 0.80)})
    upi, wallet = d["segments"][0], d["segments"][1]
    # 1.96 * sqrt(0.9 * 0.1 / 10000 + 0.92 * 0.08 / 10000): a two-proportion normal interval
    assert upi["ci"] == pytest.approx(0.007928, abs=1e-6)
    assert wallet["ci"] is None  # no Attempts in the base Week: no change to put an interval on
