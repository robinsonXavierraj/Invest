from indices_sources import (
    get_all_as_single_array,
    get_all_indices,
    get_ftse100_yahoo,
    get_nifty50_yahoo,
    get_sp500_yahoo,
)


if __name__ == "__main__":
    spx = get_sp500_yahoo()
    ftse = get_ftse100_yahoo()
    nifty = get_nifty50_yahoo()

    print("S&P 500:", len(spx), spx[:10])
    print("FTSE 100:", len(ftse), ftse[:10])
    print("NIFTY 50:", len(nifty), nifty[:10])

    all_syms = get_all_as_single_array()
    print("Combined:", len(all_syms))
