"""FRED(키 없는 CSV)와 Yahoo Finance(yfinance)에서 시계열 수집. 소스 실패 시 다음 소스로 전환."""
import datetime as dt
import io
import time
from zoneinfo import ZoneInfo

import pandas as pd

ET = ZoneInfo("America/New_York")

FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={id}"
HISTORY_YEARS = 6


def _start():
    return (pd.Timestamp.today() - pd.DateOffset(years=HISTORY_YEARS)).strftime("%Y-%m-%d")


def parse_fred_csv(text):
    df = pd.read_csv(io.StringIO(text))
    s = pd.Series(pd.to_numeric(df.iloc[:, 1], errors="coerce").values,
                  index=pd.to_datetime(df.iloc[:, 0]))
    return s.dropna().astype(float)


def last_completed_session(now_et):
    """미국 정규장(16:00 ET 마감) 기준으로 마지막으로 끝난 거래일."""
    d = now_et.date()
    if now_et.weekday() >= 5 or now_et.hour < 16:
        d -= dt.timedelta(days=1)
    while d.weekday() >= 5:
        d -= dt.timedelta(days=1)
    return d


def trim_to_session(series, now_et=None):
    """아직 끝나지 않은 거래일의 미완성 시세를 제거."""
    now_et = now_et or dt.datetime.now(ET).replace(tzinfo=None)
    cutoff = last_completed_session(now_et)
    return series[series.index.date <= cutoff]


def _curl_get(url, timeout):
    """GitHub 서버에서 성공이 확인된 방식 그대로: curl 기본 요청 (식별자 변경 없음)."""
    import subprocess
    r = subprocess.run(["curl", "-sS", "-f", "-L", "-m", str(timeout), url],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"curl 오류 {r.returncode}: {r.stderr.strip()}")
    return r.stdout


def fred(series_id, retries=2, wait=3, getter=None, timeout=30):
    getter = getter or _curl_get
    last = None
    for i in range(retries):
        try:
            text = getter(FRED_URL.format(id=series_id), timeout)
            head = text[:200]
            first_line = head.splitlines()[0] if head.strip() else ""
            if series_id not in first_line:
                raise RuntimeError(f"CSV가 아닌 응답: {head[:120]!r}")
            s = parse_fred_csv(text)
            return s[s.index >= pd.Timestamp(_start())]
        except Exception as e:  # noqa: BLE001
            last = e
            if i < retries - 1:
                time.sleep(wait * (i + 1))
    raise RuntimeError(f"{last}")


def yahoo(ticker):
    import yfinance as yf
    df = yf.download(ticker, period=f"{HISTORY_YEARS}y", auto_adjust=True,
                     progress=False, threads=False)
    if df is None or df.empty:
        raise RuntimeError(f"Yahoo {ticker} 빈 응답")
    close = df["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]
    close.index = pd.to_datetime(close.index).tz_localize(None)
    return trim_to_session(close.dropna().astype(float))


DEFAULT_FETCHERS = {"fred": fred, "yahoo": yahoo}


def _one(src, fetchers):
    t = src["type"]
    if t == "fred":
        return fetchers["fred"](src["id"]), f"FRED {src['id']}"
    if t == "yahoo":
        return fetchers["yahoo"](src["id"]), f"Yahoo {src['id']}"
    if t == "yahoo_ratio":
        num, den = fetchers["yahoo"](src["num"]), fetchers["yahoo"](src["den"])
        ratio = (num / den).dropna()
        return ratio, f"Yahoo {src['num']}/{src['den']}"
    raise ValueError(f"알 수 없는 소스 유형: {t}")


def fetch_indicator(ind, fetchers=None):
    """(series, 소스 라벨, 대체 소스 사용 여부). 전부 실패 시 (None, None, False)."""
    fetchers = fetchers or DEFAULT_FETCHERS
    for k, src in enumerate(ind["sources"]):
        name = src.get("id") or f"{src.get('num')}/{src.get('den')}"
        label = f"{'FRED' if src['type'] == 'fred' else 'Yahoo'} {name}"
        try:
            s, label = _one(src, fetchers)
            if s is not None and len(s) > 0:
                return s, label, k > 0
            print(f"[수집 실패] {label}: 빈 데이터")
        except Exception as e:  # noqa: BLE001
            print(f"[수집 실패] {label}: {e}")
    return None, None, False
