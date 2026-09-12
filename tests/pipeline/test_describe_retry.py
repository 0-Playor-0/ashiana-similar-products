from pipeline.describe import _parse_retry_after


def test_parse_retry_after_minutes_and_seconds():
    msg = "Rate limit reached ... Please try again in 4m33.888s. Need more tokens?"
    assert _parse_retry_after(msg) == 4 * 60 + 33.888


def test_parse_retry_after_seconds_only():
    msg = "Please try again in 12.5s."
    assert _parse_retry_after(msg) == 12.5


def test_parse_retry_after_no_match_returns_none():
    assert _parse_retry_after("Internal server error") is None
