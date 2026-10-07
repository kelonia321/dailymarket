import pandas as pd
import pytest
from src.fetch import parse_fred_csv, fetch_indicator

def test_parse_fred_csv_new_header_and_missing():
    txt = "observation_date,DGS10\n2026-10-01,4.10\n2026-10-02,.\n2026-10-05,4.15\n"
    s = parse_fred_csv(txt)
    assert list(s.values) == [4.10, 4.15]
    assert s.index[0] == pd.Timestamp("2026-10-01")

def test_parse_fred_csv_old_header():
    s = parse_fred_csv("DATE,T10YIE\n2026-10-01,2.30\n")
    assert s.iloc[0] == 2.30

def _ser(v):
    return pd.Series(v, index=pd.bdate_range("2026-01-01", periods=len(v)), dtype=float)

def test_fallback_used_when_primary_fails():
    def yahoo(t): raise RuntimeError("blocked")
    def fred(i): return _ser([1, 2, 3])
    ind = {"sources": [{"type": "yahoo", "id": "^VIX"}, {"type": "fred", "id": "VIXCLS"}]}
    s, label, fb = fetch_indicator(ind, {"yahoo": yahoo, "fred": fred})
    assert list(s) == [1, 2, 3] and label == "FRED VIXCLS" and fb is True

def test_ratio_source():
    data = {"XLY": _ser([10, 20]), "XLP": _ser([5, 5])}
    ind = {"sources": [{"type": "yahoo_ratio", "num": "XLY", "den": "XLP"}]}
    s, label, fb = fetch_indicator(ind, {"yahoo": lambda t: data[t]})
    assert list(s) == [2.0, 4.0] and fb is False and label == "Yahoo XLY/XLP"

def test_all_sources_fail_returns_none():
    def bad(x): raise RuntimeError
    ind = {"sources": [{"type": "fred", "id": "X"}]}
    assert fetch_indicator(ind, {"fred": bad}) == (None, None, False)

def test_empty_series_counts_as_failure():
    ind = {"sources": [{"type": "fred", "id": "X"}, {"type": "fred", "id": "Y"}]}
    calls = {"X": _ser([]), "Y": _ser([7])}
    s, label, fb = fetch_indicator(ind, {"fred": lambda i: calls[i]})
    assert label == "FRED Y" and fb is True
