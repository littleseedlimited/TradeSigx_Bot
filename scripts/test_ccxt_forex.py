import asyncio
import ccxt.async_support as ccxt
import pandas as pd
import time

async def test_ccxt_forex():
    exchange = ccxt.binance()
    symbols = ["EUR/USDT", "GBP/USDT", "BTC/USDT"]
    print(f"Testing CCXT (Binance) for: {symbols}")
    
    try:
        for symbol in symbols:
            print(f"Fetching {symbol}...")
            ohlcv = await exchange.fetch_ohlcv(symbol, timeframe='15m', limit=100)
            if ohlcv:
                print(f"SUCCESS: Retrieved {len(ohlcv)} candles for {symbol}")
            else:
                print(f"FAILURE: Empty data for {symbol}")
    except Exception as e:
        print(f"ERROR: {e}")
    finally:
        await exchange.close()

if __name__ == "__main__":
    asyncio.run(test_ccxt_forex())
