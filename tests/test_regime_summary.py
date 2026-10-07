import pytest
from src.regime import classify, curve_shape
from src.summary import rate_line, build_summary

def d(real=0, bei=0, tp=0, y10=0, spx=0.0, hy=0):
    return {"real_bp": real, "bei_bp": bei, "tp_bp": tp, "y10_bp": y10,
            "spx_ret": spx, "hy_bp": hy}

@pytest.mark.parametrize("inp,key", [
    (d(real=10, bei=10, spx=0.02), "reflation"),
    (d(real=0, bei=10, spx=-0.03), "stagflation"),
    (d(real=2, bei=10, spx=0.01, hy=20), "stagflation"),
    (d(real=12, bei=0, spx=-0.02), "tightening"),
    (d(real=12, bei=0, spx=0.02), "real_growth"),
    (d(real=2, bei=-2, y10=15, tp=12), "term_premium"),
    (d(real=-10, bei=-10), "slowdown"),
    (d(real=1, bei=1), "mixed"),
])
def test_classify_branches(inp, key):
    assert classify(inp, eps=5)["key"] == key

@pytest.mark.parametrize("y10,curve,label", [
    (10, 5, "베어 스티프닝"), (10, -5, "베어 플래트닝"),
    (-10, 5, "불 스티프닝"), (-10, -5, "불 플래트닝"), (0, 0, "커브 변화 미미")])
def test_curve_shape(y10, curve, label):
    assert curve_shape(y10, curve) == label

def test_rate_line_breakout():
    s = rate_line(value=5.03, prev=4.97, chg_20d_bp=35)
    assert "5.0%선을 돌파" in s and "5.03%" in s

def test_rate_line_breakdown():
    assert "4.5%선을 하회" in rate_line(value=4.48, prev=4.52, chg_20d_bp=-10)

def test_rate_line_plain():
    s = rate_line(value=4.21, prev=4.18, chg_20d_bp=-12)
    assert "4.21%" in s and "+3bp" in s and "-12bp" in s and "돌파" not in s

def test_build_summary_three_lines():
    ctx = {
        "y10": {"value": 4.6, "prev": 4.55, "chg_20d_bp": 25},
        "deltas": d(real=12, bei=3, tp=8, y10=25, spx=-0.03, hy=30),
        "regime": classify(d(real=12, bei=3, tp=8, y10=25, spx=-0.03, hy=30), eps=5),
        "curve": "베어 스티프닝",
        "movers": [("VIX", 30, 55), ("S&P 500", 40, 45)],
    }
    lines = build_summary(ctx)
    assert len(lines) == 3
    assert "긴축" in lines[1] and "베어 스티프닝" in lines[1]
    assert "VIX" in lines[2] and "55 → 30" in lines[2]
    assert "하이일드" in lines[2]

def test_line2_grammar_no_particle_artifacts():
    ctx = {"y10": {"value": 4.2, "prev": 4.2, "chg_20d_bp": 0},
           "deltas": d(), "regime": classify(d(), eps=5), "curve": "커브 변화 미미",
           "movers": [("VIX", 50, None)]}
    line2 = build_summary(ctx)[1]
    assert "을(를)" not in line2 and "국면 국면" not in line2 and "국면으로 판단됩니다" in line2

def test_line3_no_duplicate_when_mover_is_hy():
    ctx = {"y10": {"value": 4.2, "prev": 4.2, "chg_20d_bp": 0},
           "deltas": d(hy=20), "regime": classify(d(hy=20), eps=5), "curve": "커브 변화 미미",
           "movers": [("하이일드 스프레드", 10, 83)]}
    line3 = build_summary(ctx)[2]
    assert line3.count("하이일드") == 1 and "+20bp" in line3
