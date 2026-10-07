"""FRED(키 없는 CSV)와 Yahoo Finance(yfinance)에서 시계열 수집. 소스 실패 시 다음 소스로 전환."""
import io
import time
import pandas as pd

FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={id}&cosd={start}"
HISTORY_YEARS = 6


def _start():
    return (pd.Timestamp.today() - pd.DateOffset(years=HISTORY_YEARS)).strftime("%Y-%m-%d")


def parse_fred_csv(text):
    df = pd.read_csv(io.StringIO(text))
    s = pd.Series(pd.to_numeric(df.iloc[:, 1], errors="coerce").values,
                  index=pd.to_datetime(df.iloc[:, 0]))
    return s.dropna().astype(float)


def fred(series_id, retries=3):
    import requests
    last = None
    for i in range(retries):
        try:
            r = requests.get(FRED_URL.format(id=series_id, start=_start()), timeout=30,
                             headers={"User-Agent": "dailymarket-dashboard"})
            r.raise_for_status()
            return parse_fred_csv(r.text)
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(2 * (i + 1))
    raise RuntimeError(f"FRED {series_id} 실패: {last}")


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
    return close.dropna().astype(float)


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
        try:
            s, label = _one(src, fetchers)
            if s is not None and len(s) > 0:
                return s, label, k > 0
        except Exception:  # noqa: BLE001
            continue
    return None, None, False
