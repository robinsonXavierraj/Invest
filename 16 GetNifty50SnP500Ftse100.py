import re
import requests
import pandas as pd
from io import StringIO

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

def _dedupe(seq):
    seen, out = set(), []
    for x in seq:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out

def get_sp500_yahoo():
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    html = requests.get(url, headers=HEADERS, timeout=20).text
    # Use StringIO to avoid FutureWarning
    tables = pd.read_html(StringIO(html))
    df = tables[0]
    symbols = df['Symbol'].astype(str).str.strip()
    # Yahoo maps class shares with '-' (e.g., BRK.B -> BRK-B)
    tickers = symbols.str.replace('.', '-', regex=False).tolist()
    return _dedupe(tickers)

def get_ftse100_yahoo():
    url = "https://en.wikipedia.org/wiki/FTSE_100_Index"
    html = requests.get(url, headers=HEADERS, timeout=20).text
    tables = pd.read_html(StringIO(html))

    candidate_cols = ("epic", "ticker", "ticker symbol", "epic code")
    for t in tables:
        norm_cols = [str(c).strip().lower() for c in t.columns]
        # find first plausible ticker column
        match_idx = next((i for i, c in enumerate(norm_cols) if any(k in c for k in candidate_cols)), None)
        if match_idx is None:
            continue
        col = t.iloc[:, match_idx].astype(str)
        # strip footnote junk and whitespace
        col = col.apply(lambda s: re.sub(r'[^A-Za-z0-9]', '', s)).str.strip()
        tickers = [f"{x}.L" for x in col if x]
        if tickers:
            return _dedupe(tickers)

    raise RuntimeError("Couldn't locate FTSE 100 tickers table on Wikipedia.")

def get_nifty50_yahoo():
    nse_api = "https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%2050"
    nse_home = "https://www.nseindia.com/"
    sess = requests.Session()
    sess.get(nse_home, headers=HEADERS, timeout=15)  # set cookies
    r = sess.get(nse_api, headers=HEADERS, timeout=20)
    r.raise_for_status()
    data = r.json()
    rows = data.get("data", [])
    # Drop the index header row (e.g., 'NIFTY 50') and anything with spaces (NSE equity symbols do not contain spaces)
    symbols = []
    for row in rows:
        sym = (row.get("symbol") or "").strip()
        if not sym or sym.upper() in {"NIFTY 50", "NIFTY50"} or " " in sym:
            continue
        symbols.append(sym)
    tickers = [f"{s}.NS" for s in symbols]
    return _dedupe(tickers)

def get_all_indices():
    return {
        "SP500": get_sp500_yahoo(),    # often 503 because of dual-class names (e.g., GOOG/GOOGL)
        "FTSE100": get_ftse100_yahoo(),# should be 100
        "NIFTY50": get_nifty50_yahoo() # should be 50
    }

def get_all_as_single_array():
    d = get_all_indices()
    return _dedupe(d["SP500"] + d["FTSE100"] + d["NIFTY50"])

if __name__ == "__main__":
    spx = get_sp500_yahoo()
    ftse = get_ftse100_yahoo()
    nifty = get_nifty50_yahoo()

    print("S&P 500:", len(spx), spx[:10])
    print("FTSE 100:", len(ftse), ftse[:10])
    print("NIFTY 50:", len(nifty), nifty[:10])

    all_syms = get_all_as_single_array()
    print("Combined:", len(all_syms))
