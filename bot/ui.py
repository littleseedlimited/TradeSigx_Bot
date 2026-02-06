from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from config import Config

def get_welcome_menu_keyboard():
    """Welcome menu for new/unregistered users"""
    keyboard = [
        [InlineKeyboardButton("📝 Sign Up", callback_data="cmd_signup")],
        [InlineKeyboardButton("💎 View Plans", callback_data="cmd_plans"), 
         InlineKeyboardButton("📖 Help", callback_data="cmd_help")],
        [InlineKeyboardButton("👤 My Profile", callback_data="cmd_profile"),
         InlineKeyboardButton("ℹ️ About", callback_data="cmd_about")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_registered_menu_keyboard():
    """Full menu for registered users - inline buttons"""
    keyboard = [
        [InlineKeyboardButton("📈 Generate Signal", callback_data="menu_generate"),
         InlineKeyboardButton("⚡ Quick Scan", callback_data="menu_quick_scan")],
        [InlineKeyboardButton("💼 Wallet", callback_data="menu_wallet"),
         InlineKeyboardButton("🔌 Brokers", callback_data="menu_brokers")],
        [InlineKeyboardButton("👤 Profile", callback_data="cmd_profile"),
         InlineKeyboardButton("💎 Upgrade", callback_data="cmd_plans")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="menu_settings"),
         InlineKeyboardButton("🤖 Autotrading", callback_data="settings_autotrade")],
        [InlineKeyboardButton("📖 Help", callback_data="cmd_help"),
         InlineKeyboardButton("ℹ️ About", callback_data="cmd_about")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_main_menu_keyboard():
    keyboard = [
        [KeyboardButton("📈 Generate Signal"), KeyboardButton("⚡ Quick Analysis")],
        [KeyboardButton("💼 Wallet"), KeyboardButton("🔌 Brokers")],
        [KeyboardButton("⚙️ Settings"), KeyboardButton("📖 Help")],
        [KeyboardButton("ℹ️ About")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_analysis_keyboard():
    keyboard = [
        [InlineKeyboardButton("🌍 Forex OTC", callback_data="cat_forex"), InlineKeyboardButton("₿ Crypto", callback_data="cat_crypto")],
        [InlineKeyboardButton("⚡ Synthetic OTC", callback_data="cat_synthetic"), InlineKeyboardButton("📦 Commodities", callback_data="cat_commodities")],
        [InlineKeyboardButton("📊 Indices", callback_data="cat_indices"), InlineKeyboardButton("🏢 Stocks", callback_data="cat_stocks")],
        [InlineKeyboardButton("🛰 Multi-Asset Scanner", callback_data="menu_bulk_scan")],
        [InlineKeyboardButton("📈 Visual Chart", web_app=WebAppInfo(url=Config.BASE_URL))],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_forex_keyboard():
    keyboard = [
        [InlineKeyboardButton("EUR/USD", callback_data="analyze_forex_EURUSD=X"), InlineKeyboardButton("GBP/USD", callback_data="analyze_forex_GBPUSD=X")],
        [InlineKeyboardButton("USD/JPY", callback_data="analyze_forex_USDJPY=X"), InlineKeyboardButton("AUD/USD", callback_data="analyze_forex_AUDUSD=X")],
        [InlineKeyboardButton("NZD/USD", callback_data="analyze_forex_NZDUSD=X"), InlineKeyboardButton("USD/CAD", callback_data="analyze_forex_USDCAD=X")],
        [InlineKeyboardButton("USD/CHF", callback_data="analyze_forex_USDCHF=X"), InlineKeyboardButton("EUR/GBP", callback_data="analyze_forex_EURGBP=X")],
        [InlineKeyboardButton("EUR/JPY", callback_data="analyze_forex_EURJPY=X"), InlineKeyboardButton("GBP/JPY", callback_data="analyze_forex_GBPJPY=X")],
        [InlineKeyboardButton("AUD/JPY", callback_data="analyze_forex_AUDJPY=X"), InlineKeyboardButton("EUR/AUD", callback_data="analyze_forex_EURAUD=X")],
        [InlineKeyboardButton("GBP/CHF", callback_data="analyze_forex_GBPCHF=X"), InlineKeyboardButton("EUR/CHF", callback_data="analyze_forex_EURCHF=X")],
        [InlineKeyboardButton("CAD/JPY", callback_data="analyze_forex_CADJPY=X"), InlineKeyboardButton("USD/MXN", callback_data="analyze_forex_USDMXN=X")],
        [InlineKeyboardButton("USD/BRL (Brazil)", callback_data="analyze_forex_USDBRL=X"), InlineKeyboardButton("USD/TRY (Turkey)", callback_data="analyze_forex_USDTRY=X")],
        [InlineKeyboardButton("USD/NGN (Nigeria)", callback_data="analyze_forex_USDNGN=X"), InlineKeyboardButton("USD/ZAR (SA)", callback_data="analyze_forex_USDZAR=X")],
        [InlineKeyboardButton("🔙 Back to Analysis", callback_data="analyze_back")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_crypto_keyboard():
    keyboard = [
        [InlineKeyboardButton("Bitcoin", callback_data="analyze_crypto_BTC/USDT"), InlineKeyboardButton("Ethereum", callback_data="analyze_crypto_ETH/USDT")],
        [InlineKeyboardButton("Solana", callback_data="analyze_crypto_SOL/USDT"), InlineKeyboardButton("BNB", callback_data="analyze_crypto_BNB/USDT")],
        [InlineKeyboardButton("Cardano", callback_data="analyze_crypto_ADA/USDT"), InlineKeyboardButton("Polkadot", callback_data="analyze_crypto_DOT/USDT")],
        [InlineKeyboardButton("Polygon", callback_data="analyze_crypto_MATIC/USDT"), InlineKeyboardButton("Chainlink", callback_data="analyze_crypto_LINK/USDT")],
        [InlineKeyboardButton("Uniswap", callback_data="analyze_crypto_UNI/USDT"), InlineKeyboardButton("Avalanche", callback_data="analyze_crypto_AVAX/USDT")],
        [InlineKeyboardButton("Dogecoin", callback_data="analyze_crypto_DOGE/USDT"), InlineKeyboardButton("Shiba Inu", callback_data="analyze_crypto_SHIB/USDT")],
        [InlineKeyboardButton("Litecoin", callback_data="analyze_crypto_LTC/USDT"), InlineKeyboardButton("XRP", callback_data="analyze_crypto_XRP/USDT")],
        [InlineKeyboardButton("Pepe", callback_data="analyze_crypto_PEPE/USDT"), InlineKeyboardButton("Near", callback_data="analyze_crypto_NEAR/USDT")],
        [InlineKeyboardButton("Optimism", callback_data="analyze_crypto_OP/USDT"), InlineKeyboardButton("Atom", callback_data="analyze_crypto_ATOM/USDT")],
        [InlineKeyboardButton("⬅️ Back to Analysis", callback_data="analyze_back")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_synthetic_keyboard():
    keyboard = [
        [InlineKeyboardButton("Volatility 10", callback_data="analyze_synthetic_R_10"), InlineKeyboardButton("Volatility 25", callback_data="analyze_synthetic_R_25")],
        [InlineKeyboardButton("Volatility 50", callback_data="analyze_synthetic_R_50"), InlineKeyboardButton("Volatility 75", callback_data="analyze_synthetic_R_75")],
        [InlineKeyboardButton("Volatility 100", callback_data="analyze_synthetic_R_100"), InlineKeyboardButton("Crash 300", callback_data="analyze_synthetic_C300")],
        [InlineKeyboardButton("Crash 500", callback_data="analyze_synthetic_C500"), InlineKeyboardButton("Crash 1000", callback_data="analyze_synthetic_C1000")],
        [InlineKeyboardButton("Boom 300", callback_data="analyze_synthetic_B300"), InlineKeyboardButton("Boom 500", callback_data="analyze_synthetic_B500")],
        [InlineKeyboardButton("Boom 1000", callback_data="analyze_synthetic_B1000"), InlineKeyboardButton("Jump 10", callback_data="analyze_synthetic_J10")],
        [InlineKeyboardButton("Jump 50", callback_data="analyze_synthetic_J50"), InlineKeyboardButton("Step Index", callback_data="analyze_synthetic_STEP")],
        [InlineKeyboardButton("🔙 Back to Analysis", callback_data="analyze_back")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_commodities_keyboard():
    keyboard = [
        [InlineKeyboardButton("Gold (XAU/USD)", callback_data="analyze_forex_GC=F"), InlineKeyboardButton("Silver (XAG/USD)", callback_data="analyze_forex_SI=F")],
        [InlineKeyboardButton("Oil WTI", callback_data="analyze_forex_CL=F"), InlineKeyboardButton("Oil Brent", callback_data="analyze_forex_BZ=F")],
        [InlineKeyboardButton("Natural Gas", callback_data="analyze_forex_NG=F"), InlineKeyboardButton("Copper", callback_data="analyze_forex_HG=F")],
        [InlineKeyboardButton("Platinum", callback_data="analyze_forex_PL=F"), InlineKeyboardButton("🔙 Back to Analysis", callback_data="analyze_back")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_indices_keyboard():
    keyboard = [
        [InlineKeyboardButton("US30 (Dow Jones)", callback_data="analyze_forex_^DJI"), InlineKeyboardButton("US500 (S&P 500)", callback_data="analyze_forex_^GSPC")],
        [InlineKeyboardButton("NASDAQ 100", callback_data="analyze_forex_^NDX"), InlineKeyboardButton("DAX", callback_data="analyze_forex_^GDAXI")],
        [InlineKeyboardButton("FTSE 100", callback_data="analyze_forex_^FTSE"), InlineKeyboardButton("CAC 40", callback_data="analyze_forex_^FCHI")],
        [InlineKeyboardButton("Nikkei 225", callback_data="analyze_forex_^N225"), InlineKeyboardButton("🔙 Back to Analysis", callback_data="analyze_back")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_stocks_keyboard():
    keyboard = [
        [InlineKeyboardButton("Apple", callback_data="analyze_forex_AAPL"), InlineKeyboardButton("Google", callback_data="analyze_forex_GOOGL")],
        [InlineKeyboardButton("Tesla", callback_data="analyze_forex_TSLA"), InlineKeyboardButton("Microsoft", callback_data="analyze_forex_MSFT")],
        [InlineKeyboardButton("Amazon", callback_data="analyze_forex_AMZN"), InlineKeyboardButton("Meta", callback_data="analyze_forex_META")],
        [InlineKeyboardButton("NVIDIA", callback_data="analyze_forex_NVDA"), InlineKeyboardButton("Netflix", callback_data="analyze_forex_NFLX")],
        [InlineKeyboardButton("🔙 Back to Analysis", callback_data="analyze_back")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_broker_selector_keyboard():
    keyboard = [
        [InlineKeyboardButton("Deriv", callback_data="connect_deriv")],
        [InlineKeyboardButton("Binance (Crypto)", callback_data="connect_binance")],
        [InlineKeyboardButton("Pocket Option (Web)", callback_data="connect_pocket")],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_settings_keyboard():
    keyboard = [
        [InlineKeyboardButton("🎓 Strategy Education", callback_data="settings_strategies")],
        [InlineKeyboardButton("⚖️ Risk Management", callback_data="settings_risk")],
        [InlineKeyboardButton("🌍 Change Timezone", callback_data="settings_timezone")],
        [InlineKeyboardButton("🔔 Signal Detector", callback_data="settings_notify")],
        [InlineKeyboardButton("🤖 Autotrading", callback_data="settings_autotrade")],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_risk_management_keyboard(user):
    keyboard = [
        [InlineKeyboardButton(f"Default Lot: {user.default_lot}", callback_data="risk_edit_lot")],
        [InlineKeyboardButton(f"Risk Per Trade: {user.risk_per_trade}%", callback_data="risk_edit_perc")],
        [InlineKeyboardButton(f"Max Daily Loss: {user.max_daily_loss}%", callback_data="risk_edit_loss")],
        [InlineKeyboardButton("⬅️ Back to Settings", callback_data="back_to_settings")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_autotrade_settings_keyboard(user):
    status = "ON ✅" if user.autotrade_enabled else "OFF ❌"
    keyboard = [
        [InlineKeyboardButton(f"Status: {status}", callback_data="autotrade_toggle")],
        [InlineKeyboardButton(f"Min Confidence: {user.autotrade_min_confidence}%", callback_data="autotrade_edit_conf")],
        [InlineKeyboardButton(f"Max Trades/Day: {user.autotrade_max_trades}", callback_data="autotrade_edit_limit")],
        [InlineKeyboardButton(f"Risk Per Trade: {user.risk_per_trade}%", callback_data="autotrade_edit_risk")],
        [InlineKeyboardButton("📈 Selected Assets", callback_data="autotrade_edit_assets")],
        [InlineKeyboardButton("⬅️ Back to Settings", callback_data="back_to_settings")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_strategy_education_keyboard():
    keyboard = [
        [InlineKeyboardButton("📈 Trend Follower", callback_data="info_strategy_trend")],
        [InlineKeyboardButton("🔄 Mean Reversion", callback_data="info_strategy_reversion")],
        [InlineKeyboardButton("🚀 Momentum Breakout", callback_data="info_strategy_momentum")],
        [InlineKeyboardButton("🧠 Smart Money (SMC)", callback_data="info_strategy_smc")],
        [InlineKeyboardButton("⚡ Scalping Pulse", callback_data="info_strategy_scalp")],
        [InlineKeyboardButton("⬅️ Back to Settings", callback_data="back_to_settings")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_wallet_keyboard():
    keyboard = [
        [InlineKeyboardButton("➕ Deposit Funds", callback_data="wallet_deposit"), InlineKeyboardButton("➖ Withdraw", callback_data="wallet_withdraw")],
        [InlineKeyboardButton("📜 Trade History", callback_data="wallet_history")],
        [InlineKeyboardButton("🌐 Link External Wallets", callback_data="menu_external_wallets")],
        [InlineKeyboardButton("🔌 Connect Broker", callback_data="connect_deriv")],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_trade_execution_keyboard(symbol, direction, entry_price):
    keyboard = [
        [
            InlineKeyboardButton(f"🚀 EXECUTE {direction} NOW", callback_data=f"sel|broker|{symbol}|{direction}|{entry_price}")
        ],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel_trade")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_broker_selection_for_trade(symbol, direction, entry_price, active_brokers):
    """
    Keyboard for selecting which broker to use for a specific trade.
    """
    keyboard = []
    # Always option for Paper Trading
    keyboard.append([InlineKeyboardButton("🛡 Bot Wallet (Paper Trading)", callback_data=f"exec|trade|paper|{symbol}|{direction}|{entry_price}")])
    
    for broker in active_brokers:
        b_name = broker.broker_name.capitalize()
        if broker.broker_name == 'pocket':
            label = f"📱 Pocket Option (UID: {broker.api_key})"
        elif broker.broker_name == 'deriv':
            label = "📉 Deriv Account (Live)"
        else:
            label = f"🏦 {b_name} Account"
            
        keyboard.append([InlineKeyboardButton(label, callback_data=f"exec|trade|{broker.broker_name}|{symbol}|{direction}|{entry_price}")])
    
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel_trade")])
    return InlineKeyboardMarkup(keyboard)

def get_timezone_keyboard():
    zones = [
        [("UTC (GMT)", "UTC"), ("London (GMT+0)", "Europe/London")],
        [("Lagos/CET (GMT+1)", "Africa/Lagos"), ("Johannesburg (GMT+2)", "Africa/Johannesburg")],
        [("Dubai (GMT+4)", "Asia/Dubai"), ("Singapore (GMT+8)", "Asia/Singapore")],
        [("New York (GMT-5)", "America/New_York"), ("Los Angeles (GMT-8)", "America/Los_Angeles")],
        [("⬅️ Back to Settings", "back_to_settings")]
    ]
    keyboard = []
    for row in zones:
        kb_row = []
        for label, code in row:
            if label == "⬅️ Back to Settings":
                kb_row.append(InlineKeyboardButton(label, callback_data=code))
            else:
                kb_row.append(InlineKeyboardButton(label, callback_data=f"set_tz_{code}"))
        keyboard.append(kb_row)
    return InlineKeyboardMarkup(keyboard)

def get_duration_selection_keyboard(asset_type, symbol):
    durations = [
        [("5 Seconds", "5s"), ("10 Seconds", "10s")],
        [("15 Seconds", "15s"), ("30 Seconds", "30s")],
        [("1 Minute", "1m"), ("5 Minutes", "5m")],
        [("15 Minutes", "15m"), ("1 Hour", "1h")],
        [("4 Hours", "4h"), ("📊 Dynamic (AI)", "ai")]
    ]
    keyboard = []
    for row in durations:
        kb_row = []
        for label, code in row:
            # Format: exec_analyze|asset_type|symbol|duration
            callback = f"exec_analyze|{asset_type}|{symbol}|{code}"
            kb_row.append(InlineKeyboardButton(label, callback_data=callback))
        keyboard.append(kb_row)
    
    keyboard.append([InlineKeyboardButton("🔙 Back to Assets", callback_data=f"cat_{asset_type}")])
    return InlineKeyboardMarkup(keyboard)

def get_bulk_scanner_keyboard(selected_assets: list):
    """
    Toggle-based keyboard for selecting multiple assets.
    selected_assets: List of symbols currently selected.
    """
    # Define a set of popular assets for the scanner
    available_assets = [
        {"name": "BTC", "symbol": "BTC/USDT"}, {"name": "ETH", "symbol": "ETH/USDT"},
        {"name": "SOL", "symbol": "SOL/USDT"}, {"name": "Gold", "symbol": "GC=F"},
        {"name": "EUR/USD", "symbol": "EURUSD=X"}, {"name": "GBP/USD", "symbol": "GBPUSD=X"},
        {"name": "NASDAQ", "symbol": "^IXIC"}, {"name": "US Oil", "symbol": "CL=F"},
        {"name": "Volat 10", "symbol": "R_10"}, {"name": "Volat 100", "symbol": "R_100"}
    ]
    
    keyboard = []
    row = []
    for asset in available_assets:
        status = "✅" if asset['symbol'] in selected_assets else "⭕"
        label = f"{status} {asset['name']}"
        row.append(InlineKeyboardButton(label, callback_data=f"toggle_bulk|{asset['symbol']}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    
    if row: keyboard.append(row)
    
    # Action buttons
    keyboard.append([InlineKeyboardButton("🚀 START BULK SCAN", callback_data="exec_bulk_scan")])
    keyboard.append([InlineKeyboardButton("🔙 Back to Analysis", callback_data="analyze_back")])
    
    return InlineKeyboardMarkup(keyboard)
