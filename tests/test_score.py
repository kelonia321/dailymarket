import numpy as np
import pandas as pd
import pytest
from src.score import percentile_rank, indicator_score, grade, composite

CFG = {"lookback_days": 1260, "change_window": 20, "level_weight": 0.4,
       "change_weight": 0.6, "min_history": 260}

def _series(values):
    idx = pd.bdate_range("2020-01-01", periods=len(values))
    return pd.Series(values, index=idx, dtype=float)

def test_percentile_rank_extremes():
    w = np.arange(1, 101, dtype=float)
    assert percentile_rank(w, 100.0) == pytest.approx(99.5)
    assert percentile_rank(w, 1.0) == pytest.approx(0.5)

def test_higher_direction_rising_series_scores_high():
    s = _series(np.linspace(100, 200, 600))
    s.iloc[-1] = 260
    r = indicator_score(s, direction="higher", transform="log", cfg=CFG)
    assert r["score"] >= 80

def test_lower_direction_same_series_scores_low():
    s = _series(np.linspace(1, 5, 600))
    s.iloc[-1] = 7
    r = indicator_score(s, direction="lower", transform="diff", cfg=CFG)
    assert r["score"] <= 20

def test_anchor_direction_rewards_value_near_anchor():
    rng = np.random.default_rng(0)
    vals = 2.25 + rng.choice([-1, 1], 600) * rng.uniform(0.3, 0.8, 600)
    vals[-1] = 2.25
    r = indicator_score(_series(vals), direction="anchor", transform="diff", cfg=CFG, anchor=2.25)
    assert r["level"] >= 95

def test_result_fields():
    s = _series(np.linspace(1, 2, 400))
    r = indicator_score(s, direction="higher", transform="diff", cfg=CFG)
    assert r["value"] == pytest.approx(2.0)
    assert r["prev"] == pytest.approx(s.iloc[-2])
    assert r["change_20d"] == pytest.approx(s.iloc[-1] - s.iloc[-21])
    assert r["asof"] == s.index[-1].date()

def test_insufficient_history_returns_none():
    s = _series(np.linspace(1, 2, 100))
    assert indicator_score(s, direction="higher", transform="diff", cfg=CFG) is None

@pytest.mark.parametrize("score,label", [
    (100, "매우안정"), (80, "매우안정"), (79, "안정"), (60, "안정"), (59, "중립"),
    (40, "중립"), (39, "불안"), (20, "불안"), (19, "매우불안"), (0, "매우불안"),
    (None, "데이터 없음")])
def test_grade_boundaries(score, label):
    assert grade(score)[0] == label

GROUPS = {"rates": {"weight": 35}, "credit": {"weight": 25},
          "risk": {"weight": 25}, "commod": {"weight": 15}}
INDS = [{"id": "a", "group": "rates"}, {"id": "b", "group": "rates"},
        {"id": "c", "group": "rates"}, {"id": "d", "group": "credit"},
        {"id": "e", "group": "credit"}, {"id": "f", "group": "risk"},
        {"id": "g", "group": "commod"}]

def test_composite_renormalizes_missing_groups():
    scores = {"a": 50, "b": 50, "c": 50, "d": 100, "e": 100, "f": None, "g": None}
    out = composite(scores, INDS, GROUPS, min_valid=5)
    assert out["groups"]["risk"] is None
    assert out["total"] == round((35 * 50 + 25 * 100) / 60)

def test_composite_below_min_valid_is_none():
    scores = {"a": 50, "b": 50, "c": None, "d": None, "e": None, "f": None, "g": 70}
    assert composite(scores, INDS, GROUPS, min_valid=5)["total"] is None
