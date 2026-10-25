"""Reference suite (not given to sessions): validates the module and the frozen check."""
from datetime import date

import pytest

from recur import Frequency, Rule, RuleError, between, describe, next_after, occurrences, parse_rule, to_string


def take(rule, start, n=None):
    return list(occurrences(rule, start, limit=n))


def test_daily_interval_count():
    r = parse_rule("FREQ=DAILY;INTERVAL=3;COUNT=3")
    assert take(r, date(2024, 2, 27)) == [date(2024, 2, 27), date(2024, 3, 1), date(2024, 3, 4)]


def test_weekly_byday_skips_start_when_not_listed():
    r = parse_rule("FREQ=WEEKLY;BYDAY=MO,WE;COUNT=4")
    assert take(r, date(2024, 1, 2)) == [date(2024, 1, 3), date(2024, 1, 8), date(2024, 1, 10), date(2024, 1, 15)]


def test_weekly_interval_two():
    r = parse_rule("freq=weekly;interval=2;byday=fr")
    assert take(r, date(2024, 1, 5), 3) == [date(2024, 1, 5), date(2024, 1, 19), date(2024, 2, 2)]


def test_monthly_31st_skip_and_clamp():
    skip = parse_rule("FREQ=MONTHLY;COUNT=3")
    assert take(skip, date(2024, 1, 31)) == [date(2024, 1, 31), date(2024, 3, 31), date(2024, 5, 31)]
    clamp = parse_rule("FREQ=MONTHLY;COUNT=3;ONINVALID=CLAMP")
    assert take(clamp, date(2024, 1, 31)) == [date(2024, 1, 31), date(2024, 2, 29), date(2024, 3, 31)]


def test_monthly_last_day_and_dedup():
    r = parse_rule("FREQ=MONTHLY;BYMONTHDAY=-1,31;COUNT=3;ONINVALID=CLAMP")
    assert take(r, date(2023, 1, 1)) == [date(2023, 1, 31), date(2023, 2, 28), date(2023, 3, 31)]
    neg = parse_rule("FREQ=MONTHLY;BYMONTHDAY=-31")
    assert take(neg, date(2023, 1, 1), 2) == [date(2023, 1, 1), date(2023, 3, 1)]
    assert take(parse_rule("FREQ=MONTHLY;BYMONTHDAY=-31;ONINVALID=CLAMP"), date(2023, 2, 1), 1) == [date(2023, 2, 1)]


def test_yearly_leap_day():
    assert take(parse_rule("FREQ=YEARLY;COUNT=2"), date(2024, 2, 29)) == [date(2024, 2, 29), date(2028, 2, 29)]
    assert take(parse_rule("FREQ=YEARLY;COUNT=2;ONINVALID=CLAMP"), date(2024, 2, 29)) == [date(2024, 2, 29), date(2025, 2, 28)]


def test_until_inclusive_and_before_start():
    r = parse_rule("FREQ=DAILY;UNTIL=20240103")
    assert take(r, date(2024, 1, 1)) == [date(2024, 1, 1), date(2024, 1, 2), date(2024, 1, 3)]
    assert take(r, date(2024, 2, 1)) == []


def test_never_matching_rule_stops(monkeypatch):
    import recur.rules as m
    monkeypatch.setattr(m, "MAX_SCAN_PERIODS", 5)
    assert take(Rule(Frequency.MONTHLY, interval=12, by_month_day=(30,)), date(2023, 2, 1)) == []


@pytest.mark.parametrize("text,msg", [
    ("", "empty"), ("FREQ=DAILY;COUNT=2;UNTIL=20240101", "both"), ("INTERVAL=2", "FREQ is required"),
    ("FREQ=HOURLY", "unknown FREQ"), ("FREQ=DAILY;FREQ=DAILY", "duplicate"), ("FREQ=DAILY;X=1", "unknown key"),
    ("FREQ=DAILY;COUNT=x", "integer"), ("FREQ=DAILY;UNTIL=2024-01-01", "YYYYMMDD"), ("FREQ=DAILY;UNTIL=20240230", "valid date"),
    ("FREQ=DAILY;BYDAY=MO", "only supported"), ("FREQ=WEEKLY;BYDAY=XX", "unknown weekday"), ("FREQ=MONTHLY;BYMONTHDAY=0", "out of range"),
    ("FREQ=DAILY;INTERVAL=0", "at least 1"), ("FREQ=DAILY;COUNT=0", "at least 1"), ("FREQ=DAILY;ONINVALID=X", "SKIP or CLAMP"),
    ("FREQ", "KEY=VALUE"), ("FREQ=", "no value"), ("FREQ=WEEKLY;BYMONTHDAY=1", "only supported"),
])
def test_errors(text, msg):
    with pytest.raises(RuleError, match=msg):
        parse_rule(text)


def test_rule_validation_direct():
    with pytest.raises(RuleError):
        Rule(Frequency.WEEKLY, by_weekday=(7,))
    with pytest.raises(RuleError):
        Rule(Frequency.MONTHLY, by_month_day=(32,))


def test_roundtrip():
    for text in ["FREQ=WEEKLY;INTERVAL=2;COUNT=6;BYDAY=MO,WE", "FREQ=MONTHLY;UNTIL=20250101;BYMONTHDAY=1,-1;ONINVALID=CLAMP", "FREQ=YEARLY"]:
        r = parse_rule(text)
        assert parse_rule(to_string(r)) == r
        assert to_string(r) == text


def test_next_after_and_between():
    r = parse_rule("FREQ=WEEKLY;BYDAY=TU")
    assert next_after(r, date(2024, 1, 2), date(2024, 1, 2)) == date(2024, 1, 9)
    assert next_after(parse_rule("FREQ=DAILY;COUNT=1"), date(2024, 1, 1), date(2024, 1, 1)) is None
    d = parse_rule("FREQ=DAILY")
    assert between(d, date(2024, 1, 1), date(2024, 1, 3), date(2024, 1, 5)) == [date(2024, 1, 3), date(2024, 1, 4), date(2024, 1, 5)]
    assert between(d, date(2024, 1, 1), date(2024, 1, 3), date(2024, 1, 5), inclusive=False) == [date(2024, 1, 4)]
    with pytest.raises(RuleError):
        between(d, date(2024, 1, 1), date(2024, 1, 5), date(2024, 1, 3))


def test_describe():
    assert describe(parse_rule("FREQ=WEEKLY;INTERVAL=2;BYDAY=MO,WE;COUNT=6")) == "every 2 weeks on Monday and Wednesday, 6 times"
    assert describe(parse_rule("FREQ=MONTHLY;BYMONTHDAY=1,2,-1,-2")) == "every month on the 1st, 2nd, last day and 2nd to last day"
    assert describe(parse_rule("FREQ=DAILY;COUNT=1")) == "every day, once"
    assert describe(parse_rule("FREQ=YEARLY;UNTIL=20300101")) == "every year, until 2030-01-01"
    assert describe(parse_rule("FREQ=MONTHLY;BYMONTHDAY=11,12,13,23")) == "every month on the 11th, 12th, 13th and 23rd"
