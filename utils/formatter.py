import pytz
from datetime import datetime
from config import Config

# ASSET NAME MAPPING: Convert symbols/codes to clear descriptive names (Name + Symbol)
ASSET_NAMES = {
    # Forex
    "EURUSD=X": "Euro / US Dollar (EUR/USD)", "GBPUSD=X": "British Pound / US Dollar (GBP/USD)",
    "USDJPY=X": "US Dollar / Japanese Yen (USD/JPY)", "AUDUSD=X": "Australian Dollar / US Dollar (AUD/USD)",
    "USDCAD=X": "US Dollar / Canadian Dollar (USD/CAD)", "USDCHF=X": "US Dollar / Swiss Franc (USD/CHF)",
    "NZDUSD=X": "NZ Dollar / US Dollar (NZD/USD)", "EURGBP=X": "Euro / British Pound (EUR/GBP)",
    "EURJPY=X": "Euro / Japanese Yen (EUR/JPY)", "GBPJPY=X": "Pound / Japanese Yen (GBP/JPY)",
    "AUDJPY=X": "Australian / Japanese Yen (AUD/JPY)", "EURAUD=X": "Euro / Australian Dollar (EUR/AUD)",
    "GBPCHF=X": "Pound / Swiss Franc (GBP/CHF)", "EURCHF=X": "Euro / Swiss Franc (EUR/CHF)",
    "CADJPY=X": "Canadian / Japanese Yen (CAD/JPY)", "USDMXN=X": "US Dollar / Mexican Peso (USD/MXN)",
    "USDBRL=X": "US Dollar / Brazilian Real (USD/BRL)", "USDTRY=X": "US Dollar / Turkish Lira (USD/TRY)",
    "USDNGN=X": "US Dollar / Nigerian Naira (USD/NGN)", "USDZAR=X": "US Dollar / SA Rand (USD/ZAR)",
    # Crypto
    "BTC/USDT": "Bitcoin (BTC/USDT)", "ETH/USDT": "Ethereum (ETH/USDT)",
    "SOL/USDT": "Solana (SOL/USDT)", "ADA/USDT": "Cardano (ADA/USDT)",
    "BNB/USDT": "Binance Coin (BNB/USDT)", "XRP/USDT": "Ripple (XRP/USDT)",
    "DOT/USDT": "Polkadot (DOT/USDT)", "MATIC/USDT": "Polygon (MATIC/USDT)",
    "LINK/USDT": "Chainlink (LINK/USDT)", "DOGE/USDT": "Dogecoin (DOGE/USDT)",
    "SHIB/USDT": "Shiba Inu (SHIB/USDT)", "LTC/USDT": "Litecoin (LTC/USDT)",
    "UNI/USDT": "Uniswap (UNI/USDT)", "AVAX/USDT": "Avalanche (AVAX/USDT)",
    # Commodities & Indices
    "GC=F": "Gold (XAU/USD)", "SI=F": "Silver (XAG/USD)", "CL=F": "Crude Oil WTI (US Oil)",
    "BZ=F": "Crude Oil Brent (Brent Oil)", "NG=F": "Natural Gas (NATGAS)",
    "HG=F": "Copper (COPPER)", "PL=F": "Platinum (PLAT)",
    "^IXIC": "NASDAQ Composite", "^NDX": "NASDAQ 100 (USTEC)", "^GSPC": "S&P 500 Index (US500)", "^DJI": "Dow Jones 30 (US30)",
    "^FTSE": "FTSE 100 Index (UK100)", "^GDAXI": "DAX 40 Index (GER40)",
    "^FCHI": "CAC 40 Index (FRA40)", "^N225": "Nikkei 225 (JPN225)",
    "AAPL": "Apple Inc. (AAPL)", "GOOGL": "Alphabet Inc. (GOOGL)",
    "TSLA": "Tesla Inc. (TSLA)", "MSFT": "Microsoft Corp. (MSFT)",
    "AMZN": "Amazon.com (AMZN)", "META": "Meta Platforms (META)",
    "NVDA": "NVIDIA Corp. (NVDA)", "NFLX": "Netflix Inc. (NFLX)",
    # Synthetic
    "R_10": "Volatility 10 Index (V10)", "R_25": "Volatility 25 Index (V25)",
    "R_50": "Volatility 50 Index (V50)", "R_75": "Volatility 75 Index (V75)",
    "R_100": "Volatility 100 Index (V100)", "C1000": "Crash 1000 Index",
    "C500": "Crash 500 Index", "C300": "Crash 300 Index", "B1000": "Boom 1000 Index",
    "B500": "Boom 500 Index", "B300": "Boom 300 Index", "J10": "Jump 10 Index",
    "J50": "Jump 50 Index", "STEP": "Step Index",
    "1HZ10V": "Volatility 10 (1s) Index", "1HZ100V": "Volatility 100 (1s) Index"
}

def format_signal(signal, user_tz="UTC"):
    """
    Formats a signal dictionary into a beautiful Telegram message.
    Optimized for high-confidence entries and clear execution details.
    """
    if not signal:
        return "❌ Failed to generate signal. Please try again later.", None

    # Define emoji based on direction
    emoji = "🟢" if signal['direction'] == "BUY" else ("🔴" if signal['direction'] == "SELL" else "⚪️")
    
    # Get current time in UTC
    now_utc = datetime.now(pytz.UTC)
    now_ts = int(now_utc.timestamp())
    
    # Get User TZ
    try:
        tz = pytz.timezone(user_tz)
    except Exception:
        tz = pytz.UTC
        
    # Convert entry timestamp (UTC) to User's target timezone (UTC)
    entry_ts = signal.get('entry_timestamp', now_ts)
    entry_dt_utc = datetime.fromtimestamp(entry_ts, tz=pytz.UTC)
    
    # NEW: Also show WAT (UTC+1) for Lagos/London context to prevent "stale" confusion
    wat_tz = pytz.timezone("Africa/Lagos")
    entry_dt_wat = entry_dt_utc.astimezone(wat_tz)
    
    entry_utc_str = entry_dt_utc.strftime("%H:%M:%S")
    entry_wat_str = entry_dt_wat.strftime("%H:%M:%S")
    
    # Calculate difference
    countdown_seconds = entry_ts - now_ts
    countdown_minutes = countdown_seconds // 60
    countdown_secs = countdown_seconds % 60
    
    if countdown_seconds > 0:
        countdown_text = f"in {countdown_minutes}m {countdown_secs}s"
    elif countdown_seconds > -60:
        countdown_text = "NOW"
    else:
        countdown_text = "EXPIRED"

    # Asset Name Mapping
    asset_display = ASSET_NAMES.get(signal['asset'], signal['asset'])

    # Price precision based on asset (5 for forex, 2 for crypto/synthetic)
    price_fmt = ".5f" if signal['asset'].endswith("=X") else ".2f"
    if "BTC" in signal['asset'] or "ETH" in signal['asset']: price_fmt = ".2f"
    
    # Market Alignment Disclaimer
    market_type = signal.get('market_type', 'Global Spot')
    alignment_note = ""
    if market_type == "Real Global Market":
        alignment_note = "\n\n⚠️ **BROKER ALIGNMENT CHECK**: This is a **REAL MARKET** signal. Avoid using 'OTC' versions on your broker (e.g., Pocket Option OTC) as trends will NOT match."
    elif market_type == "OTC Proprietary":
        alignment_note = "\n\n⚠️ **OTC NOTICE**: Prices are broker-specific and may differ from global market trackers."

    msg = (
        f"💎 **TradeSigx Premium Signal**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🕒 **Entry (UTC)**: `{entry_utc_str}`\n"
        f"🇳🇬 **Entry (WAT)**: `{entry_wat_str}`\n"
        f"⏳ **Status**: `{countdown_text}`\n"
        f"📍 **Timezone**: `UTC / WAT (+1)`\n"
        f"⏳ **Expiry**: `{signal['expiry']}`\n"
        f"🔔 **Notice**: `ORDER READY`\n\n"
        f"Asset: **{asset_display}**\n"
        f"Action: {emoji} **{signal['direction']}**\n"
        f"Confidence: `{signal['confidence']}%`\n"
        f"🌍 Market: 💠 **{market_type.upper()}**\n"
        f"🛠 Type: `{signal.get('trade_type', 'Execution Only')}`\n"
        f"🎯 **Strategy**: `{signal.get('strategy', 'AI Confluence')}`\n\n"
        f"💰 Entry: `{signal['entry']:{price_fmt}}`\n"
        f"🎯 TP: `{signal['tp']:{price_fmt}}`\n"
        f"🛡 SL: `{signal['sl']:{price_fmt}}`\n\n"
        f"📈 Trend: `{signal['trend']}`\n"
        f"⛰ Resistance: `{signal['resistance']:{price_fmt}}`\n"
        f"🕳 Support: `{signal['support']:{price_fmt}}`\n"
        f"📝 Rationale: _{signal['rationale']}_{alignment_note}\n\n"
        f"🔗 [Open Visual Chart]({Config.BASE_URL})\n"
        f"⚠️ *Trade at your own risk.*"
    )
    
    # Trading Buttons
    from bot.ui import get_trade_execution_keyboard
    kb = get_trade_execution_keyboard(signal['asset'], signal['direction'], signal['entry'])
    
    return msg, kb
