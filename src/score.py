"""지표별 점수(수준 분위 + 변화 분위)와 종합 점수 산출."""
import numpy as np
import pandas as pd

GRADES = [
    (80, "매우안정", "#1B7F3B"),
    (60, "안정", "#6BBF59"),
    (40, "중립", "#E5B700"),
    (20, "불안", "#E8762B"),
    (0, "매우불안", "#C62828"),
]
NO_DATA = ("데이터 없음", "#9E9E9E")


def percentile_rank(window, value):
    """window 내에서 value의 분위(0~100). 동률은 절반으로 계산."""
    w = np.asarray(window, dtype=float)
    w = w[~np.isnan(w)]
    if len(w) == 0 or value is None or np.isnan(value):
        return None
    less = np.sum(w < value)
    equal = np.sum(w == value)
    return float((less + 0.5 * equal) / len(w) * 100)


def _change(series, transform, n):
    if transform == "log":
        return np.log(series / series.shift(n))
    return series - series.shift(n)


def indicator_score(series, direction, transform, cfg, anchor=None):
    """direction: higher | lower | anchor. 데이터 부족 시 None."""
    s = series.dropna()
    if len(s) < cfg.get("min_history", 260):
        return None
    n = cfg["change_window"]
    s = s.iloc[-(cfg["lookback_days"] + n):]

    work = (s - anchor).abs() if direction == "anchor" else s
    flip = direction in ("lower", "anchor")

    level_win = work.iloc[-cfg["lookback_days"]:]
    level = percentile_rank(level_win.values, work.iloc[-1])

    work_t = "diff" if direction == "anchor" else transform
    chg = _change(work, work_t, n).dropna()
    change = percentile_rank(chg.iloc[-cfg["lookback_days"]:].values, chg.iloc[-1])

    if flip:
        level, change = 100 - level, 100 - change
    score = int(round(cfg["level_weight"] * level + cfg["change_weight"] * change))

    raw_chg = _change(s, transform, n).iloc[-1]
    return {
        "value": float(s.iloc[-1]),
        "prev": float(s.iloc[-2]),
        "change_1d": float(s.iloc[-1] - s.iloc[-2]),
        "change_20d": float(raw_chg),
        "level": round(level, 1),
        "change": round(change, 1),
        "score": max(0, min(100, score)),
        "asof": s.index[-1].date(),
    }


def grade(score):
    if score is None:
        return NO_DATA
    for floor, label, color in GRADES:
        if score >= floor:
            return (label, color)
    return GRADES[-1][1:]


def composite(scores, indicators, groups, min_valid):
    """지표군 단순평균 → 지표군 가중평균. 결측은 제외 후 재정규화."""
    group_scores = {}
    for gid in groups:
        vals = [scores.get(i["id"]) for i in indicators if i["group"] == gid]
        vals = [v for v in vals if v is not None]
        group_scores[gid] = round(sum(vals) / len(vals)) if vals else None

    valid = sum(1 for v in scores.values() if v is not None)
    total = None
    if valid >= min_valid:
        num = sum(groups[g]["weight"] * v for g, v in group_scores.items() if v is not None)
        den = sum(groups[g]["weight"] for g, v in group_scores.items() if v is not None)
        total = round(num / den) if den else None
    return {"groups": group_scores, "total": total, "valid": valid}
