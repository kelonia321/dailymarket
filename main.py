"""매일 실행되는 진입점: 수집 → 점수 → 국면 → 요약 → HTML 저장."""
import datetime as dt
import json
import pathlib
import sys

import numpy as np
import pandas as pd

from src.fetch import fetch_indicator, DEFAULT_FETCHERS, _one
from src.score import indicator_score, composite
from src.regime import classify, curve_shape
from src.summary import build_summary
from src.render import render

KST = dt.timezone(dt.timedelta(hours=9))


def _score_all(cfg, fetchers, today):
    out = []
    for ind in cfg["indicators"]:
        series, label, fb = fetch_indicator(ind, fetchers)
        r = None
        if series is not None:
            anchor = cfg["bei_anchor"] if ind["direction"] == "anchor" else None
            r = indicator_score(series, ind["direction"], ind["transform"], cfg, anchor=anchor)
        row = {**ind, "source": label, "fallback": fb, "score": None, "value": None,
               "change_1d": None, "change_20d": None, "asof": None, "stale": False}
        if r:
            row.update(r)
            row["stale"] = int(np.busday_count(r["asof"], today)) >= cfg["stale_bdays"]
        out.append(row)
    return out


def _bp(rows, iid):
    r = rows.get(iid)
    return None if r is None or r["change_20d"] is None else r["change_20d"] * 100


def _curve_bp(cfg, fetchers):
    try:
        s, _ = _one(cfg["aux"]["curve"], fetchers)
        s = s.dropna()
        return float((s.iloc[-1] - s.iloc[-1 - cfg["change_window"]]) * 100)
    except Exception:  # noqa: BLE001
        return None


def build(cfg, fetchers, root, today=None):
    root = pathlib.Path(root)
    today = today or dt.datetime.now(KST).date()
    inds = _score_all(cfg, fetchers, today)
    scores = {i["id"]: i["score"] for i in inds}
    comp = composite(scores, cfg["indicators"], cfg["groups"], cfg["min_valid_indicators"])
    if comp["total"] is None:
        print(f"유효 지표 {comp['valid']}개로 종합 점수 산출 불가. 기존 대시보드를 유지합니다.")
        return False

    rows = {i["id"]: i for i in inds}
    data_date = max(i["asof"] for i in inds if i["asof"])

    # 이력
    hist_path = root / "data" / "history.csv"
    hist_path.parent.mkdir(parents=True, exist_ok=True)
    hist = pd.read_csv(hist_path, parse_dates=["date"]) if hist_path.exists() else pd.DataFrame()
    prev = {}
    if not hist.empty:
        hist["date"] = pd.to_datetime(hist["date"]).dt.date
        older = hist[hist["date"] < data_date]
        if not older.empty:
            last = older.iloc[-1]
            prev = {k: (None if pd.isna(last.get(k)) else int(last[k])) for k in scores}
        hist = hist[hist["date"] != data_date]
    new = {"date": data_date, "total": comp["total"], **scores}
    hist = pd.concat([hist, pd.DataFrame([new])], ignore_index=True).sort_values("date")
    hist.to_csv(hist_path, index=False)

    # 국면·요약
    y10, real, bei = rows["dgs10"], _bp(rows, "real10"), _bp(rows, "bei10")
    regime_label, curve_label = None, None
    if y10["value"] is not None and real is not None and bei is not None:
        deltas = {"real_bp": real, "bei_bp": bei, "tp_bp": _bp(rows, "tp10") or 0.0,
                  "y10_bp": _bp(rows, "dgs10") or 0.0,
                  "spx_ret": (rows["spx"]["change_20d"] or 0.0) if rows["spx"]["score"] is not None else 0.0,
                  "hy_bp": _bp(rows, "hy") or 0.0}
        regime = classify(deltas, cfg["regime_eps_bp"])
        cb = _curve_bp(cfg, fetchers)
        curve_label = curve_shape(deltas["y10_bp"], cb) if cb is not None else "데이터 없음"
        movers = [(i["name"], i["score"], prev.get(i["id"])) for i in inds if i["score"] is not None]
        summary = build_summary({
            "y10": {"value": y10["value"], "prev": y10["prev"], "chg_20d_bp": deltas["y10_bp"]},
            "deltas": deltas, "regime": regime, "curve": curve_label, "movers": movers})
        regime_label = regime["label"]
    else:
        summary = ["금리 구성 지표(명목·실질금리, BEI) 일부를 불러오지 못해 국면 판정을 생략했습니다.",
                   "지표별 점수와 종합 점수는 수집된 데이터만으로 산출했습니다.",
                   "다음 실행 시 데이터가 복구되면 자동으로 정상 요약이 표시됩니다."]

    model = {
        "date": data_date,
        "generated": dt.datetime.now(KST).strftime("%Y-%m-%d %H:%M KST"),
        "total": comp["total"], "regime": regime_label, "curve": curve_label, "summary": summary,
        "groups": [{"id": g, "name": v["name"], "weight": v["weight"], "score": comp["groups"][g]}
                   for g, v in cfg["groups"].items()],
        "indicators": inds,
        "history": [(d, None if pd.isna(t) else int(t)) for d, t in zip(hist["date"], hist["total"])],
    }
    html = render(model)
    docs = root / "docs"
    (docs / "archive").mkdir(parents=True, exist_ok=True)
    (docs / ".nojekyll").touch()
    (docs / "index.html").write_text(html, encoding="utf-8")
    (docs / "archive" / f"{data_date.isoformat()}.html").write_text(html, encoding="utf-8")
    print(f"{data_date} 종합 점수 {comp['total']} (유효 지표 {comp['valid']}개)")
    return True


if __name__ == "__main__":
    here = pathlib.Path(__file__).resolve().parent
    config = json.loads((here / "config.json").read_text(encoding="utf-8"))
    sys.exit(0 if build(config, DEFAULT_FETCHERS, here) else 1)
