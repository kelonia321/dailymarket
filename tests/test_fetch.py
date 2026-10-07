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

import datetime as dt
from src import fetch as F

class _Resp:
    def __init__(self, text, code=200):
        self.text, self.status_code = text, code
    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

def test_failure_reason_is_logged(capsys):
    def bad(i): raise RuntimeError("HTTP 403 차단")
    fetch_indicator({"sources": [{"type": "fred", "id": "DGS10"}]}, {"fred": bad})
    out = capsys.readouterr().out
    assert "FRED DGS10" in out and "HTTP 403 차단" in out

def test_fred_rejects_html_response(monkeypatch):
    import requests
    monkeypatch.setattr(requests, "get", lambda *a, **k: _Resp("<html>Access Denied</html>"))
    with pytest.raises(RuntimeError, match="CSV가 아닌 응답"):
        F.fred("DGS10", retries=1, wait=0)

def test_fred_sends_browser_user_agent(monkeypatch):
    import requests
    seen = {}
    def get(url, **k):
        seen.update(k.get("headers", {}))
        return _Resp("observation_date,DGS10\n2026-10-06,4.1\n")
    monkeypatch.setattr(requests, "get", get)
    F.fred("DGS10", retries=1, wait=0)
    assert "Mozilla" in seen["User-Agent"]

@pytest.mark.parametrize("now,last", [
    (dt.datetime(2026, 10, 7, 1, 44), dt.date(2026, 10, 6)),   # 장 시작 전 → 전일
    (dt.datetime(2026, 10, 6, 18, 0), dt.date(2026, 10, 6)),   # 장 마감 후 → 당일
    (dt.datetime(2026, 10, 5, 9, 0), dt.date(2026, 10, 2)),    # 월요일 장중 → 금요일
])
def test_last_completed_session(now, last):
    assert F.last_completed_session(now) == last

def test_trim_drops_incomplete_bar():
    s = pd.Series([1.0, 2.0, 3.0], index=pd.to_datetime(["2026-10-05", "2026-10-06", "2026-10-07"]))
    out = F.trim_to_session(s, dt.datetime(2026, 10, 7, 1, 44))
    assert list(out.index.date) == [dt.date(2026, 10, 5), dt.date(2026, 10, 6)]

def test_fred_empty_body_is_clear_error(monkeypatch):
    import requests
    monkeypatch.setattr(requests, "get", lambda *a, **k: _Resp(""))
    with pytest.raises(RuntimeError, match="CSV가 아닌 응답"):
        F.fred("DGS10", retries=1, wait=0)
