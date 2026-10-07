import datetime as dt
import json
import pathlib
import numpy as np
import pandas as pd
from main import build

CFG = json.loads(pathlib.Path(__file__).resolve().parents[1].joinpath("config.json").read_text(encoding="utf-8"))

def _fake_fetchers(end, seed=1, fail=()):
    idx = pd.bdate_range(end=end, periods=1500)
    rng = np.random.default_rng(seed)
    def walk(start, vol):
        return pd.Series(start + np.cumsum(rng.normal(0, vol, len(idx))), index=idx).abs() + 0.1
    base = {"DGS10": walk(4, .03), "DFII10": walk(1.8, .03), "T10YIE": walk(2.3, .02),
            "THREEFYTP10": walk(.5, .02), "BAMLH0A0HYM2": walk(3.2, .03), "T10Y2Y": walk(.3, .02),
            "VIXCLS": walk(16, .5), "SP500": walk(5000, 30), "DCOILWTICO": walk(70, 1)}
    yb = {"^VIX": walk(16, .5), "^GSPC": walk(5000, 30), "XLY": walk(200, 2), "XLP": walk(80, .5),
          "HG=F": walk(4.5, .05), "GC=F": walk(2500, 15), "CL=F": walk(70, 1)}
    def fred(i):
        if i in fail: raise RuntimeError
        return base[i]
    def yahoo(t):
        if t in fail: raise RuntimeError
        return yb[t]
    return {"fred": fred, "yahoo": yahoo}

def test_build_writes_outputs_and_history(tmp_path):
    ok = build(CFG, _fake_fetchers("2026-10-06"), tmp_path, today=dt.date(2026, 10, 7))
    assert ok
    html = (tmp_path / "docs" / "index.html").read_text(encoding="utf-8")
    assert "투자 권유가 아닙니다" in html
    assert (tmp_path / "docs" / "archive" / "2026-10-06.html").exists()
    hist = pd.read_csv(tmp_path / "data" / "history.csv")
    assert len(hist) == 1 and hist["total"].notna().all()

def test_second_day_uses_previous_scores(tmp_path):
    build(CFG, _fake_fetchers("2026-10-05", seed=1), tmp_path, today=dt.date(2026, 10, 6))
    build(CFG, _fake_fetchers("2026-10-06", seed=2), tmp_path, today=dt.date(2026, 10, 7))
    html = (tmp_path / "docs" / "index.html").read_text(encoding="utf-8")
    assert "전일 대비 점수 변화가 가장 큰 지표" in html
    assert len(pd.read_csv(tmp_path / "data" / "history.csv")) == 2

def test_same_day_rerun_replaces_history_row(tmp_path):
    f = _fake_fetchers("2026-10-06")
    build(CFG, f, tmp_path, today=dt.date(2026, 10, 7))
    build(CFG, f, tmp_path, today=dt.date(2026, 10, 7))
    assert len(pd.read_csv(tmp_path / "data" / "history.csv")) == 1

def test_yahoo_blocked_uses_fred_fallback(tmp_path):
    fail = ("^VIX", "^GSPC", "CL=F", "XLY", "HG=F")
    assert build(CFG, _fake_fetchers("2026-10-06", fail=fail), tmp_path, today=dt.date(2026, 10, 7))
    html = (tmp_path / "docs" / "index.html").read_text(encoding="utf-8")
    assert "대체 소스" in html and "데이터 없음" in html

def test_too_few_indicators_keeps_previous_dashboard(tmp_path):
    build(CFG, _fake_fetchers("2026-10-05"), tmp_path, today=dt.date(2026, 10, 6))
    before = (tmp_path / "docs" / "index.html").read_text(encoding="utf-8")
    fail = ("DGS10", "DFII10", "T10YIE", "THREEFYTP10", "BAMLH0A0HYM2", "^VIX", "VIXCLS")
    assert build(CFG, _fake_fetchers("2026-10-06", fail=fail), tmp_path, today=dt.date(2026, 10, 7)) is False
    assert (tmp_path / "docs" / "index.html").read_text(encoding="utf-8") == before

def test_stale_flag(tmp_path):
    build(CFG, _fake_fetchers("2026-09-25"), tmp_path, today=dt.date(2026, 10, 7))
    assert "지연" in (tmp_path / "docs" / "index.html").read_text(encoding="utf-8")
