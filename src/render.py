"""대시보드 단일 HTML 생성 (외부 스크립트 없음, 차트는 인라인 SVG)."""
from html import escape
from src.score import grade, GRADES

NAVY = "#0E2A47"


def _fmt_value(v, fmt):
    if v is None:
        return "–"
    return {"rate": f"{v:.2f}%", "spread": f"{v:.2f}%p", "index": f"{v:.2f}",
            "price": f"{v:,.0f}", "ratio": f"{v:.4g}", "usd": f"${v:.2f}"}.get(fmt, f"{v:.2f}")


def _fmt_change(v, prev_v, fmt):
    if v is None or prev_v is None:
        return "–"
    if fmt in ("rate", "spread"):
        return f"{v * 100:+.0f}bp"
    if fmt == "index":
        return f"{v:+.2f}"
    base = prev_v
    return f"{v / base * 100:+.2f}%" if base else "–"


def _chip(score):
    label, color = grade(score)
    txt = "–" if score is None else str(score)
    return (f'<span class="chip" style="--c:{color}"><b>{txt}</b>{escape(label)}</span>')


def _bar(score):
    if score is None:
        return '<div class="bar empty"></div>'
    color = grade(score)[1]
    return f'<div class="bar"><i style="width:{score}%;background:{color}"></i></div>'


def _scale(total):
    segs = "".join(
        f'<div class="seg" style="background:{c}"><span>{escape(l)}</span></div>'
        for _, l, c in reversed(GRADES))
    marker = "" if total is None else f'<div class="marker" style="left:{total}%"><b>{total}</b></div>'
    return f'<div class="scale">{segs}{marker}</div>'


def _trend(history):
    pts = [(d, s) for d, s in history if s is not None][-60:]
    if len(pts) < 2:
        return '<p class="muted">추이 차트는 이틀 이상 데이터가 쌓이면 표시됩니다.</p>'
    W, H, P = 720, 200, 28
    bands = "".join(
        f'<rect x="{P}" y="{P + (100 - lo - 20) * (H - 2 * P) / 100:.1f}" width="{W - 2 * P}" '
        f'height="{20 * (H - 2 * P) / 100:.1f}" fill="{c}" opacity=".13"/>'
        for lo, _, c in GRADES)
    n = len(pts)
    xy = [(P + i * (W - 2 * P) / (n - 1), P + (100 - s) * (H - 2 * P) / 100) for i, (_, s) in enumerate(pts)]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in xy)
    lx, ly = xy[-1]
    ticks = "".join(
        f'<text x="{P - 6}" y="{P + (100 - v) * (H - 2 * P) / 100 + 4:.1f}" text-anchor="end">{v}</text>'
        for v in (0, 20, 40, 60, 80, 100))
    first, last = pts[0][0].strftime("%m/%d"), pts[-1][0].strftime("%m/%d")
    return (f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="종합 점수 추이">{bands}{ticks}'
            f'<polyline points="{line}" fill="none" stroke="var(--ink)" stroke-width="2.2"/>'
            f'<circle cx="{lx:.1f}" cy="{ly:.1f}" r="4.5" fill="var(--ink)"/>'
            f'<text x="{P}" y="{H - 6}">{first}</text>'
            f'<text x="{W - P}" y="{H - 6}" text-anchor="end">{last}</text></svg>')


def _indicator_rows(m):
    names = {g["id"]: g["name"] for g in m["groups"]}
    rows, current = [], None
    for ind in m["indicators"]:
        if ind["group"] != current:
            current = ind["group"]
            rows.append(f'<tr class="grp"><th colspan="5">{escape(names.get(current, current))}</th></tr>')
        notes = []
        if ind.get("fallback"):
            notes.append("대체 소스")
        if ind.get("stale"):
            notes.append('<em class="warn">지연</em>')
        prev_v = None if ind.get("value") is None or ind.get("change_1d") is None else ind["value"] - ind["change_1d"]
        asof = ind["asof"].strftime("%m/%d") if ind.get("asof") else "–"
        src = escape(ind.get("source") or "조회 실패")
        rows.append(
            f'<tr><td class="nm">{escape(ind["name"])}<small>{src}, {asof} 기준 {" ".join(notes)}</small></td>'
            f'<td class="num">{_fmt_value(ind.get("value"), ind["fmt"])}</td>'
            f'<td class="num chg">{_fmt_change(ind.get("change_1d"), prev_v, ind["fmt"])}</td>'
            f'<td class="sc">{_bar(ind.get("score"))}</td>'
            f'<td>{_chip(ind.get("score"))}</td></tr>')
    return "".join(rows)


def render(m):
    total = m["total"]
    t_label, t_color = grade(total)
    total_txt = "산출 불가" if total is None else str(total)
    summary = "".join(f"<li>{escape(s)}</li>" for s in m["summary"])
    groups = "".join(
        f'<div class="g"><div class="gh"><span>{escape(g["name"])}</span><small>가중치 {g["weight"]}%</small></div>'
        f'{_bar(g["score"])}{_chip(g["score"])}</div>' for g in m["groups"])
    return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>미국 금리·시장 안정도 {m['date'].isoformat()}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700;900&display=swap" rel="stylesheet">
<style>
:root{{--ink:{NAVY};--bg:#F6F8FA;--panel:#FFFFFF;--text:#1C2733;--muted:#5D6B7A;--line:#DCE2E8}}
@media (prefers-color-scheme:dark){{:root{{--ink:#9CC2EA;--bg:#0F1720;--panel:#16212C;--text:#E4EAF0;--muted:#93A3B3;--line:#2A3846}}}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--text);font-family:"Noto Sans KR","Malgun Gothic","Apple SD Gothic Neo",sans-serif;font-variant-numeric:tabular-nums;line-height:1.55}}
.wrap{{max-width:980px;margin:0 auto;padding:0 20px}}
header{{background:{NAVY};color:#fff;padding:28px 0 32px}}
.top{{display:flex;justify-content:space-between;align-items:baseline;gap:12px;flex-wrap:wrap}}
h1{{font-size:1.25rem;font-weight:700;margin:0;letter-spacing:-.01em}}
.meta{{font-size:.85rem;opacity:.75}}
.hero{{display:grid;grid-template-columns:auto 1fr;gap:28px;align-items:center;margin-top:22px}}
.big{{font-size:4.6rem;font-weight:900;line-height:1;letter-spacing:-.03em}}
.big small{{display:block;font-size:1.05rem;font-weight:700;letter-spacing:0;margin-top:8px;color:{t_color};filter:brightness(1.25)}}
.regime{{font-size:.95rem;opacity:.9;margin-bottom:34px}}
.regime b{{font-weight:700}}
.scale{{position:relative;display:flex;height:34px;border-radius:4px;overflow:visible;margin:6px 0 26px}}
.seg{{flex:1;position:relative}}
.seg span{{position:absolute;top:40px;left:0;right:0;text-align:center;font-size:.75rem;opacity:.8}}
.marker{{position:absolute;top:-8px;bottom:-8px;width:4px;margin-left:-2px;background:#fff;border-radius:2px;box-shadow:0 0 0 2px {NAVY}}}
.marker b{{position:absolute;top:-24px;left:50%;transform:translateX(-50%);font-size:.85rem}}
ol.sum{{margin:22px 0 0;padding:16px 20px 16px 40px;background:rgba(255,255,255,.07);border-left:3px solid #fff;font-size:1rem}}
ol.sum li{{margin:4px 0}}
section{{margin:28px 0}}
h2{{font-size:1.05rem;margin:0 0 12px;font-weight:700}}
.groups{{display:grid;grid-template-columns:repeat(4,1fr);gap:18px}}
.g .gh{{display:flex;justify-content:space-between;font-weight:500;margin-bottom:6px}}
.g small,.nm small{{color:var(--muted);font-size:.75rem;font-weight:400}}
.bar{{height:8px;background:var(--line);border-radius:4px;overflow:hidden;margin:4px 0 8px}}
.bar i{{display:block;height:100%}}
.bar.empty{{background:repeating-linear-gradient(45deg,var(--line) 0 6px,transparent 6px 12px)}}
.chip{{display:inline-flex;gap:6px;align-items:baseline;font-size:.82rem;color:var(--c)}}
.chip b{{font-size:1rem}}
.tbl{{overflow-x:auto;background:var(--panel);border:1px solid var(--line);border-radius:6px}}
table{{width:100%;border-collapse:collapse;min-width:620px}}
td,th{{padding:10px 14px;border-bottom:1px solid var(--line);text-align:left;vertical-align:middle}}
tr.grp th{{background:var(--bg);font-size:.82rem;color:var(--muted);font-weight:500;padding:6px 14px}}
.nm{{font-weight:500}} .nm small{{display:block}}
.num{{text-align:right;white-space:nowrap}} .chg{{color:var(--muted)}}
.sc{{width:22%}}
em.warn{{color:#E8762B;font-style:normal;font-weight:700}}
.chart{{background:var(--panel);border:1px solid var(--line);border-radius:6px;padding:12px}}
svg{{width:100%;height:auto;display:block}} svg text{{fill:var(--muted);font-size:11px}}
footer{{color:var(--muted);font-size:.8rem;padding:8px 0 40px;border-top:1px solid var(--line)}}
.muted{{color:var(--muted)}}
@media (max-width:720px){{.hero{{grid-template-columns:1fr}}.big{{font-size:3.6rem}}.groups{{grid-template-columns:1fr 1fr}}}}
</style></head><body>
<header><div class="wrap">
<div class="top"><h1>미국 금리·시장 안정도</h1><span class="meta">{m['date'].strftime('%Y년 %m월 %d일')} 미국 데이터 기준, {escape(m['generated'])} 생성</span></div>
<div class="hero"><div class="big">{total_txt}<small>{escape(t_label)}</small></div>
<div><div class="regime">국면 판정 <b>{escape(m['regime'] or '판정 불가')}</b>, 커브 <b>{escape(m['curve'] or '–')}</b></div>{_scale(total)}</div></div>
<ol class="sum">{summary}</ol>
</div></header>
<main class="wrap">
<section><h2>지표군 점수</h2><div class="groups">{groups}</div></section>
<section><h2>지표별 점수</h2><div class="tbl"><table>
<thead><tr><th>지표</th><th class="num">현재</th><th class="num">전일 대비</th><th>점수</th><th>등급</th></tr></thead>
<tbody>{_indicator_rows(m)}</tbody></table></div></section>
<section><h2>종합 점수 추이 (최근 60영업일)</h2><div class="chart">{_trend(m['history'])}</div></section>
</main>
<footer><div class="wrap">
<p>점수 산정: 지표별로 현재 수준의 5년 분위(40%)와 20영업일 변화폭의 5년 분위(60%)를 안정 방향으로 환산했습니다. BEI는 2.25%와의 괴리로 평가합니다. 종합 점수는 금리 구성 35%, 신용·변동성 25%, 위험자산 25%, 원자재 15% 가중평균이며 결측 지표는 제외 후 재정규화합니다. 데이터 출처는 FRED와 Yahoo Finance입니다.</p>
<p>본 대시보드는 분석 보조 목적이며 투자 권유가 아닙니다.</p>
</div></footer>
</body></html>"""
