import yfinance as yf
import pandas as pd
import ccxt
import os
import time
import logging
import asyncio
import requests

# Global session for yfinance to mitigate fc.yahoo.com issues
yf_session = requests.Session()
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0',
    'Mozilla/5.0 (Apple) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
]
yf_session = requests.Session()
def renew_yf_session():
    global yf_session
    yf_session = requests.Session()
    import random
    yf_session.headers.update({'User-Agent': random.choice(USER_AGENTS)})

renew_yf_session()

# Global semaphore to prevent rate limiting
data_semaphore = asyncio.Semaphore(5)

# Global Data Cache: symbol -> {'data': df, 'timestamp': time}
_data_cache = {}
CACHE_TTL = 60 # 60 seconds cache for market data
MAX_CACHE_SIZE = 20 # Reduced for 512MB RAM stability

class DataCollector:
    # Mapping from Yahoo Symbols/Logic to Deriv Symbols
    DERIV_MAP = {
        "^NDX": "OTC_NDX", "^GSPC": "OTC_SPC", "^DJI": "OTC_DJI",
        "^IXIC": "OTC_NDX", "^GDAXI": "OTC_GDAXI", "^FTSE": "OTC_FTSE",
        "^FCHI": "OTC_FCHI", "^N225": "OTC_N225", "GC=F": "frxXAUUSD",
        "SI=F": "frxXAGUSD", "CL=F": "frxWTI",
        "EURUSD=X": "frxEURUSD", "GBPUSD=X": "frxGBPUSD", "USDJPY=X": "frxUSDJPY",
        "AUDUSD=X": "frxAUDUSD", "EURJPY=X": "frxEURJPY", "GBPJPY=X": "frxGBPJPY",
        "EURGBP=X": "frxEURGBP", "USDCAD=X": "frxUSDCAD", "USDCHF=X": "frxUSDCHF",
        "USDIDR=X": "frxUSDIDR", "USDINR=X": "frxUSDINR", "USDBRL=X": "frxUSDBRL",
        "EURIDR=X": "frxEURIDR", "USDMXN=X": "frxUSDMXN",
    }

    @staticmethod
    async def get_forex_data(symbol: str, interval: str = "15m", retries: int = 2):
        """Fetches data from Yahoo Finance (Primary), with yf.download fallback."""
        def fetch_yf_strategy1():
            # Strategy 1: Ticker History (Reduced period for RAM)
            ticker = yf.Ticker(symbol, session=yf_session)
            return ticker.history(period="2d", interval=interval, timeout=10)

        def fetch_yf_strategy2():
            # Strategy 2: Bulk Download (Reduced period for RAM)
            return yf.download(symbol, period="2d", interval=interval, session=yf_session, timeout=10, progress=False)

        for i in range(2):
            try:
                if i > 0: renew_yf_session()
                
                # Try Strategy 1
                df = await asyncio.to_thread(fetch_yf_strategy1)
                if df.empty:
                    # Try Strategy 2
                    df = await asyncio.to_thread(fetch_yf_strategy2)
                
                if not df.empty:
                    df.columns = [c.lower() for c in df.columns]
                    # Standardize columns
                    if isinstance(df.columns, pd.MultiIndex):
                        df.columns = df.columns.get_level_values(0)
                        df.columns = [c.lower() for c in df.columns]
                    
                    for col in ['open', 'high', 'low', 'close', 'volume']:
                        if col not in df.columns: df[col] = 0
                    return df
                
                logging.warning(f"Yahoo Strategy Failed for {symbol} (Attempt {i+1})")
                await asyncio.sleep(0.5)
            except Exception as e:
                logging.error(f"Yahoo Exception for {symbol}: {e}")
                await asyncio.sleep(0.2)
        
        return pd.DataFrame()

    @staticmethod
    async def get_synthetic_data(symbol: str, is_real_market: bool = False):
        """Fetches candles via Deriv WS. Uses AUTHORIZE for real market assets."""
        app_id = os.getenv("DERIV_APP_ID") or "121681"
        token = os.getenv("DERIV_API_TOKEN")
        
        try:
            import websockets
            import json
            uri = f"wss://ws.binaryws.com/websockets/v3?app_id={app_id}"
            
            async with websockets.connect(uri, close_timeout=5) as ws:
                # MANDATORY: Authorize if we have a token (Required for Forex/Indices)
                if token:
                    auth_req = {"authorize": token}
                    await ws.send(json.dumps(auth_req))
                    await ws.recv() # Wait for auth confirmation
                
                request = {
                    "ticks_history": symbol, 
                    "count": 200, # Reduced from 500 for RAM
                    "end": "latest", 
                    "style": "candles", 
                    "granularity": 300 # 5 min
                }
                await asyncio.wait_for(ws.send(json.dumps(request)), timeout=5)
                resp = await asyncio.wait_for(ws.recv(), timeout=10)
                data = json.loads(resp)
                
                if 'candles' in data:
                    df = pd.DataFrame(data['candles'])
                    df.columns = [c.lower() for c in df.columns]
                    # Mapping Deriv epoch to datetime index
                    df['epoch'] = pd.to_datetime(df['epoch'], unit='s')
                    df.set_index('epoch', inplace=True)
                    for c in ['open', 'high', 'low', 'close']:
                        df[c] = pd.to_numeric(df[c], errors='coerce')
                    return df
                elif 'error' in data:
                    msg = data['error'].get('message', 'Unknown')
                    logging.warning(f"Deriv API Error for {symbol}: {msg}")
                    # Special handling for "Too many requests" or "Market closed"
        except Exception as e:
            logging.error(f"Deriv WS Failure for {symbol}: {e}")
        return pd.DataFrame()

    @staticmethod
    async def fetch_data(symbol: str, asset_type: str = None):
        """Unified entry point with Deriv-first priority for blocked assets."""
        global _data_cache
        
        if symbol in _data_cache:
            entry = _data_cache[symbol]
            if time.time() - entry['timestamp'] < CACHE_TTL:
                return entry['data']
        
        # Cleanup old cache pre-emptively
        if len(_data_cache) > MAX_CACHE_SIZE:
            oldest = min(_data_cache.keys(), key=lambda k: _data_cache[k]['timestamp'])
            del _data_cache[oldest]

        async with data_semaphore:
            if not asset_type:
                if "/" in symbol or "USDT" in symbol: asset_type = "crypto"
                elif any(c in symbol for c in ["HZ", "R_", "C10", "BOOM", "CRASH"]): asset_type = "synthetic"
                else: asset_type = "forex"

            df = pd.DataFrame()
            try:
                # MAPPING: Convert Yahoo symbols to Deriv if applicable
                deriv_symbol = DataCollector.DERIV_MAP.get(symbol)
                
                if asset_type == "forex":
                    # Try Deriv FIRST for Indices/Common Forex if we have a mapping
                    if deriv_symbol:
                        logging.info(f"Prioritizing Deriv for {symbol} -> {deriv_symbol}")
                        df = await DataCollector.get_synthetic_data(deriv_symbol, is_real_market=True)
                    
                    if df.empty:
                        # Normalize for Yahoo
                        yf_sym = symbol
                        if yf_sym.upper() == "GOLD": yf_sym = "GC=F"
                        elif yf_sym.upper() == "USOIL": yf_sym = "CL=F"
                        elif "USD" in yf_sym and "=" not in yf_sym and "/" not in yf_sym: yf_sym += "=X"
                        
                        df = await DataCollector.get_forex_data(yf_sym)
                
                elif asset_type == "synthetic":
                    df = await DataCollector.get_synthetic_data(symbol)
                
                elif asset_type == "crypto":
                    # Handle CCXT with YF fallback
                    from bot.handlers import ai_gen # Lazy import
                    df = await DataCollector.get_crypto_data(symbol)

                if not df.empty:
                    _data_cache[symbol] = {'data': df, 'timestamp': time.time()}
                return df

            except Exception as e:
                logging.error(f"Global fetch error for {symbol}: {e}")
                return pd.DataFrame()

    @staticmethod
    async def get_crypto_data(symbol: str, interval: str = "15m"):
        """CCXT-based crypto fetcher"""
        import ccxt.async_support as ccxt_async
        exchanges = [ccxt_async.binance(), ccxt_async.kucoin()]
        if "/" not in symbol:
            symbol = f"{symbol.replace('USDT', '')}/USDT"

        for ex in exchanges:
            try:
                # Reduced limit from 100 to 50 for RAM
                ohlcv = await asyncio.wait_for(ex.fetch_ohlcv(symbol, timeframe=interval, limit=50), timeout=10)
                if ohlcv:
                    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                    await ex.close()
                    return df
            except: pass
            finally: await ex.close()
        
        # YF fallback for crypto
        yf_sym = symbol.replace("/", "-").replace("USDT", "USD")
        return await DataCollector.get_forex_data(yf_sym, interval=interval)

    @staticmethod
    def get_alphavantage_data(symbol: str):
        # Kept as legacy fallback but rarely used due to credits
        return pd.DataFrame()
