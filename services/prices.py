import yfinance as yf
from pycoingecko import CoinGeckoAPI


def get_stock_prices(tickers: list[str]) -> dict[str, float]:
    """Batch-fetch current prices for stocks/ETFs via yfinance."""
    if not tickers:
        return {}
    prices = {}
    try:
        data = yf.download(tickers, period="1d", progress=False)
        if data.empty:
            return prices
        close = data["Close"]
        if len(tickers) == 1:
            # yfinance returns a Series for a single ticker
            price = close.iloc[-1]
            if price == price:  # not NaN
                prices[tickers[0]] = round(float(price), 2)
        else:
            for ticker in tickers:
                if ticker in close.columns:
                    price = close[ticker].iloc[-1]
                    if price == price:  # not NaN
                        prices[ticker] = round(float(price), 2)
    except Exception as e:
        print(f"Error fetching stock prices: {e}")
    return prices


def get_crypto_prices(ids: list[str]) -> dict[str, float]:
    """Fetch current USD prices for crypto assets via CoinGecko."""
    if not ids:
        return {}
    prices = {}
    try:
        cg = CoinGeckoAPI()
        data = cg.get_price(ids=ids, vs_currencies="usd")
        for coin_id, price_data in data.items():
            if "usd" in price_data:
                prices[coin_id] = round(float(price_data["usd"]), 2)
    except Exception as e:
        print(f"Error fetching crypto prices: {e}")
    return prices
