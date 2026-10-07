"""실질금리·BEI·기간 프리미엄 20영업일 변화로 국면을 판정."""

REGIMES = {
    "reflation": ("리플레이션", "성장을 동반한 물가 상승(리플레이션)"),
    "stagflation": ("스태그플레이션 우려", "성장 없는 물가 상승(스태그플레이션) 우려"),
    "tightening": ("긴축·실질금리 주도", "연준 긴축 기대에 따른 실질금리 주도의 금리 상승"),
    "real_growth": ("실질 성장 기대", "실질 성장 기대 개선에 따른 금리 상승"),
    "term_premium": ("기간 프리미엄 주도", "재정·국채 수급 부담에 따른 기간 프리미엄 확대"),
    "slowdown": ("성장 둔화·디스인플레이션", "성장 둔화와 디스인플레이션 기대"),
    "mixed": ("혼조", "뚜렷한 방향성이 없는 혼조"),
}


def classify(x, eps=5):
    real, bei, tp, y10 = x["real_bp"], x["bei_bp"], x["tp_bp"], x["y10_bp"]
    spx, hy = x["spx_ret"], x["hy_bp"]
    if real > eps and bei > eps and spx >= 0:
        key = "reflation"
    elif bei > eps and real <= eps and (spx < 0 or hy > 0):
        key = "stagflation"
    elif real > eps and bei <= eps and spx < 0:
        key = "tightening"
    elif real > eps and bei <= eps:
        key = "real_growth"
    elif abs(real) <= eps and abs(bei) <= eps and y10 > eps and tp > eps:
        key = "term_premium"
    elif real < -eps and bei < -eps:
        key = "slowdown"
    else:
        key = "mixed"
    label, desc = REGIMES[key]
    return {"key": key, "label": label, "desc": desc}


def curve_shape(y10_bp, curve_bp, eps=2):
    if abs(curve_bp) < eps and abs(y10_bp) < eps:
        return "커브 변화 미미"
    if y10_bp >= 0:
        return "베어 스티프닝" if curve_bp > 0 else "베어 플래트닝"
    return "불 스티프닝" if curve_bp > 0 else "불 플래트닝"
