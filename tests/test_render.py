import datetime as dt
from src.render import render

def _model(total=63, missing=False):
    ind = {"id": "dgs10", "name": "10년물 명목금리", "group": "rates", "fmt": "rate",
           "value": 4.62, "change_1d": 0.03, "level": 70.0, "change": 30.0,
           "score": None if missing else 42, "asof": dt.date(2026, 10, 6),
           "source": "FRED DGS10", "fallback": False, "stale": missing}
    return {
        "date": dt.date(2026, 10, 6), "generated": "2026-10-07 07:05 KST",
        "total": total, "regime": "긴축·실질금리 주도", "curve": "베어 스티프닝",
        "summary": ["첫째 줄 요약", "둘째 줄 요약", "셋째 줄 요약"],
        "groups": [{"id": "rates", "name": "금리 구성", "weight": 35, "score": 42}],
        "indicators": [ind],
        "history": [(dt.date(2026, 10, 1), 55), (dt.date(2026, 10, 2), 60), (dt.date(2026, 10, 6), total)],
    }

def test_render_contains_core_elements():
    html = render(_model())
    assert "<!DOCTYPE html>" in html
    assert "안정" in html and "63" in html
    for line in ["첫째 줄 요약", "둘째 줄 요약", "셋째 줄 요약"]:
        assert line in html
    assert "투자 권유가 아닙니다" in html
    assert "10년물 명목금리" in html and "4.62%" in html

def test_render_missing_indicator_shows_no_data_and_stale():
    html = render(_model(missing=True))
    assert "데이터 없음" in html and "지연" in html

def test_render_total_none():
    html = render(_model(total=None))
    assert "산출 불가" in html

def test_no_external_scripts():
    html = render(_model())
    assert "<script src" not in html

def test_small_ratio_keeps_precision():
    from src.render import _fmt_value
    assert _fmt_value(0.0018234, "ratio") == "0.001823"
