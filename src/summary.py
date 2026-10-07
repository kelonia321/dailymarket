"""규칙 기반 3줄 요약."""

LEVELS = [4.0, 4.5, 5.0, 5.5]


def _bp(v):
    return f"{v:+.0f}bp"


def rate_line(value, prev, chg_20d_bp):
    d1 = (value - prev) * 100
    for lv in LEVELS:
        if prev < lv <= value:
            return (f"미국 10년물 금리가 {value:.2f}%로 {_bp(d1)} 상승하며 {lv:.1f}%선을 돌파했습니다"
                    f"(20영업일 {_bp(chg_20d_bp)}).")
        if prev >= lv > value:
            return (f"미국 10년물 금리가 {value:.2f}%로 {_bp(d1)} 하락하며 {lv:.1f}%선을 하회했습니다"
                    f"(20영업일 {_bp(chg_20d_bp)}).")
    return f"미국 10년물 금리는 {value:.2f}%로 전일 대비 {_bp(d1)}, 20영업일 기준 {_bp(chg_20d_bp)} 변동했습니다."


def _mover_text(movers):
    with_prev = [m for m in movers if m[2] is not None]
    if with_prev:
        name, s, p = max(with_prev, key=lambda m: abs(m[1] - m[2]))
        verb = "개선" if s > p else "악화"
        return f"전일 대비 점수 변화가 가장 큰 지표는 {name}({p} → {s}, {verb})이며"
    name, s, _ = max(movers, key=lambda m: abs(m[1] - 50))
    return f"현재 가장 극단적인 지표는 {name}(점수 {s})이며"


def _cross_text(hy_bp, mover_is_hy=False):
    if mover_is_hy:
        word = "확대" if hy_bp > 0 else "축소"
        return f"20영업일간 {_bp(hy_bp)} {word}되어 신용시장의 {'위험회피 신호가 강해지고' if hy_bp > 0 else '안정이 이어지고'} 있습니다."
    if hy_bp > 0:
        return f"하이일드 스프레드가 20영업일간 {_bp(hy_bp)} 확대되어 신용시장의 위험회피 신호를 동반하고 있습니다."
    return f"하이일드 스프레드는 20영업일간 {_bp(hy_bp)}로 신용시장은 아직 안정적인 모습입니다."


def build_summary(ctx):
    y, x = ctx["y10"], ctx["deltas"]
    line1 = rate_line(y["value"], y["prev"], y["chg_20d_bp"])
    line2 = (f"실질금리 {_bp(x['real_bp'])}, BEI {_bp(x['bei_bp'])}, 기간 프리미엄 {_bp(x['tp_bp'])}"
             f"(20영업일) 변화를 감안하면 현재 시장은 {ctx['regime']['desc']} 국면으로 판단됩니다"
             f"(커브: {ctx['curve']}).")
    mover = _mover_text(ctx["movers"])
    line3 = f"{mover}, {_cross_text(x['hy_bp'], '하이일드' in mover)}"
    return [line1, line2, line3]
