"""Shared helpers for retrieving major index constituents.

This module centralizes the logic for downloading ticker lists for
NIFTY 50, FTSE 100 and S&P 500 from their respective public sources.
It is imported both by ``16 GetNifty50SnP500Ftse100.py`` (a standalone
script for manual inspection) and programmatic consumers such as
``00a_HD_All_TimeFrames_Options_IB.py``.
"""

from __future__ import annotations

import re
from io import StringIO
from typing import Dict, List

import pandas as pd
import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def _dedupe(seq: List[str]) -> List[str]:
    """Return ``seq`` with duplicates removed while preserving order."""

    seen, out = set(), []
    for item in seq:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def get_sp500_yahoo() -> List[str]:
    """Return tickers for the S&P 500 mapped to Yahoo Finance symbols."""

    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    html = requests.get(url, headers=HEADERS, timeout=20).text
    tables = pd.read_html(StringIO(html))
    df = tables[0]
    symbols = df["Symbol"].astype(str).str.strip()
    # Yahoo maps class shares with '-' (e.g., BRK.B -> BRK-B)
    tickers = symbols.str.replace(".", "-", regex=False).tolist()
    return _dedupe(tickers)


def get_ftse100_yahoo() -> List[str]:
    """Return tickers for the FTSE 100 mapped to Yahoo Finance symbols."""

    url = "https://en.wikipedia.org/wiki/FTSE_100_Index"
    html = requests.get(url, headers=HEADERS, timeout=20).text
    tables = pd.read_html(StringIO(html))

    candidate_cols = ("epic", "ticker", "ticker symbol", "epic code")
    for table in tables:
        normalised_cols = [str(col).strip().lower() for col in table.columns]
        match_idx = next(
            (
                idx
                for idx, col in enumerate(normalised_cols)
                if any(keyword in col for keyword in candidate_cols)
            ),
            None,
        )
        if match_idx is None:
            continue

        col = table.iloc[:, match_idx].astype(str)
        # strip footnote junk and whitespace
        col = col.apply(lambda s: re.sub(r"[^A-Za-z0-9]", "", s)).str.strip()
        tickers = [f"{value}.L" for value in col if value]
        if tickers:
            return _dedupe(tickers)

    raise RuntimeError("Couldn't locate FTSE 100 tickers table on Wikipedia.")


def get_nifty50_yahoo() -> List[str]:
    """Return tickers for the NIFTY 50 mapped to Yahoo Finance symbols."""

    nse_api = "https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%2050"
    nse_home = "https://www.nseindia.com/"

    session = requests.Session()
    session.get(nse_home, headers=HEADERS, timeout=15)  # set cookies
    response = session.get(nse_api, headers=HEADERS, timeout=20)
    response.raise_for_status()
    data = response.json()
    rows = data.get("data", [])

    symbols: List[str] = []
    for row in rows:
        symbol = (row.get("symbol") or "").strip()
        if not symbol or symbol.upper() in {"NIFTY 50", "NIFTY50"} or " " in symbol:
            continue
        symbols.append(symbol)

    tickers = [f"{value}.NS" for value in symbols]
    return _dedupe(tickers)


def get_all_indices() -> Dict[str, List[str]]:
    """Return a mapping with constituents for all supported indices."""

    return {
        "SP500": get_sp500_yahoo(),
        "FTSE100": get_ftse100_yahoo(),
        "NIFTY50": get_nifty50_yahoo(),
    }


def get_all_as_single_array() -> List[str]:
    """Return a deduplicated list of all supported index constituents."""

    data = get_all_indices()
    return _dedupe(data["SP500"] + data["FTSE100"] + data["NIFTY50"])
