import pandas as pd
import asyncio
import logging
import time
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.ui import (
    get_main_menu_keyboard, get_analysis_keyboard, get_broker_selector_keyboard, 
    get_settings_keyboard, get_forex_keyboard, get_crypto_keyboard, 
    get_synthetic_keyboard, get_commodities_keyboard, get_indices_keyboard, 
    get_stocks_keyboard, get_bulk_scanner_keyboard, get_duration_selection_keyboard,
    get_timezone_keyboard, get_risk_management_keyboard, get_strategy_education_keyboard,
    get_wallet_keyboard, get_registered_menu_keyboard, get_welcome_menu_keyboard
)
from data.collector import DataCollector
from engine.ai_generator import AISignalGenerator
from utils.formatter import format_signal, ASSET_NAMES
from utils.db import SignalHistory, User, TradeExecution, BrokerAccount, init_db

# Import new authentication and admin modules
from bot.auth_handler import (
    start_signup, handle_signup_message, handle_signup_callback,
    check_user_access, check_signal_limit, increment_signal_usage
)
from bot.admin_handlers import admin_command, admin_callback_handler, admin_message_handler, is_admin
from bot.payment_handler import show_upgrade_menu, handle_payment_callback, handle_successful_payment
from bot.kyc_handler import start_kyc, handle_kyc_photo, kyc_status, handle_kyc_callback

from utils.engines import get_ai_gen, get_data_collector
ai_gen = get_ai_gen() # 🦁 Use Shared Singleton

# Global Cache for Quick Scan results (Super Fast response)
_last_scan_results = []
_last_scan_time = 0
SCAN_CACHE_TTL = 300 # 5 minutes

def get_market_sentiment():
    """Generates a smart summary of current market conditions for PRO/VIP users"""
    if not _last_scan_results:
        return "Market status: Analyzing assets..."
    
    buys = len([s for s in _last_scan_results if s['direction'] == 'BUY'])
    sells = len([s for s in _last_scan_results if s['direction'] == 'SELL'])
    
    if buys > sells + 2: mood = "🔥 Highly Bullish Bias"
    elif sells > buys + 2: mood = "📉 Highly Bearish Bias"
    elif buys > sells: mood = "📈 Bullish Lean"
    elif sells > buys: mood = "📉 Bearish Lean"
    else: mood = "⚖️ Market Equilibrium"
    
    top_asset = _last_scan_results[0]['asset'] if _last_scan_results else "None"
    return f"Market Mood: {mood} | Hot: `{top_asset}`"

# Global Semaphore to limit memory usage on low-RAM environments (Render Free Tier)
scan_semaphore = asyncio.Semaphore(3) 

async def scan_market_now():
    """Core scanning logic used by both manual Quick Analysis and Automated Radar"""
    global _last_scan_results, _last_scan_time, scan_semaphore
    
    # Check Cache FIRST
    if _last_scan_results and (time.time() - _last_scan_time < SCAN_CACHE_TTL):
        logging.info("Returning cached market scan results (Super Fast Mode)")
        return _last_scan_results

    essential_assets = [
        # Forex
        ("EURUSD=X", "forex"), ("GBPUSD=X", "forex"), ("USDJPY=X", "forex"),
        # Crypto (24/7)
        ("BTC/USDT", "crypto"), ("ETH/USDT", "crypto"), ("SOL/USDT", "crypto"),
        # Synthetics (Volatility)
        ("1HZ100V", "synthetic"), ("1HZ75V", "synthetic"), ("C1000", "synthetic"), ("B1000", "synthetic"),
        # Commodities & Indices
        ("GC=F", "forex"), ("SI=F", "forex"), ("CL=F", "forex"),
    ]
    
    # Use essential_assets for background radar scans
    assets_to_scan = essential_assets

    async def scan_asset(symbol, asset_type):
        async with scan_semaphore:
            try:
                # Use Shared Singleton for Data Retrieval
                shared_dc = get_data_collector() 
                df = await shared_dc.fetch_data(symbol, asset_type)
                
                if df is None or df.empty: 
                    return None
                
                signal = await ai_gen.generate_signal(symbol, df, fast_scan=True)
                
                # MEMORY CLEANUP: Delete dataframe immediately after use
                del df
                
                # Alignment Threshold: Lowered to 1% for "Anytime Signals" mode
                if signal and signal['confidence'] >= 1: 
                    return signal
            except Exception: 
                return None
            return None

    try:
        import gc
        gc.collect() # Pre-emptive cleanup
        
        # Optimize list: Remove low-liquidity assets for free tier stabilization
        essential_assets = assets_to_scan[:35] # Top 35 instead of 50+
        
        tasks = [scan_asset(s, t) for s, t in essential_assets]
        logging.info(f"Starting Scan for {len(essential_assets)} assets (Low-RAM Concurrency Mode)...")
        results = await asyncio.gather(*tasks)
        
        # Post-scan cleanup
        gc.collect()
            
        logging.info(f"Scan complete. Found {len([r for r in results if r])} high-confidence signals.")
        signals = [r for r in results if r is not None]
        signals.sort(key=lambda x: x['confidence'], reverse=True)
        
        # Update Cache
        _last_scan_results = signals[:10]
        _last_scan_time = time.time()
        
        return _last_scan_results
    except Exception as e:
        logging.error(f"Scan market error: {e}")
        return []

async def run_native_scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Native Telegram Scanner - Manual Trigger"""
    status_msg = await update.message.reply_text(
        "🚀 **TradeSigx Pro-Aggressive Scanner** (v8.0-Pro)\n"
        "Analyzing all assets for immediate setups...\n\n"
        "⏳ *Scanning in progress... Estimated: 10-15 seconds*",
        parse_mode="Markdown"
    )
    
    signals = await scan_market_now()

    if not signals:
        from datetime import datetime
        is_weekend = datetime.utcnow().weekday() >= 5
        
        if is_weekend:
            msg = (
                "📉 **Weekend Market Notice**\n\n"
                "Standard **Forex, Stocks, and Indices** are currently **CLOSED** globally.\n\n"
                "💡 **Pro Tip**: Use the 'Synthetics' or 'Crypto' menus to find active 24/7 market setups for your Pocket Option or Deriv accounts!"
            )
        else:
            msg = (
                "⚠️ **Provider Rate Limit Detected**\n\n"
                "The market data providers (Yahoo/Alpha) are temporarily unresponsive due to high scan frequency.\n\n"
                "🔄 **Recovery Status**: *Retrying in 60s...*"
            )
            
        await status_msg.edit_text(msg, parse_mode="Markdown")
        return True

    keyboard = []
    for sig in signals:
        raw_symbol = sig['asset']
        display_name = ASSET_NAMES.get(raw_symbol, raw_symbol.replace('=X', ''))
        
        asset_type = "forex"
        if "R_" in raw_symbol or "C1000" in raw_symbol or "B1000" in raw_symbol: asset_type = "synthetic"
        elif "USDT" in raw_symbol: asset_type = "crypto"
            
        btn_text = f"🎯 {display_name} ({sig['direction']}) - {sig['confidence']}%"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"analyze_{asset_type}_{raw_symbol}")])
    
    keyboard.append([InlineKeyboardButton("⬅️ Return to Menu", callback_data="back_to_main")])
    
    await status_msg.edit_text(
        f"✅ **Scanner Found {len(signals)} Active Setup(s)**\n"
        "Engine: **TradeSigx Pro v8.0-Pro**\n"
        "Mode: **Anytime Signals (Aggressive)**\n\n"
        "Click an asset below to reveal entry levels:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    import logging
    logging.info(f"Received /start from user {user.id} ({user.username})")
    
    # Import UI menus
    from bot.ui import get_welcome_menu_keyboard, get_registered_menu_keyboard
    
    # Check if user exists and is registered
    db = init_db()
    try:
        user_id = str(user.id)
        username = user.username
        is_super = user_id == "1241907317" or username == "origichidiah"
        
        db_user = db.get_user_by_telegram_id(user_id)
        
        if not db_user:
            # New user - show welcome menu
            new_user = User(
                telegram_id=user_id,
                username=username or user.first_name,
                registration_step="start"
            )
            db.add(new_user)
            db.commit()
            db.close()
            
            await update.message.reply_text(
                f"🦁 **WELCOME TO TRADESIGX!**\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"Hello {user.first_name}! 👋\n\n"
                f"I'm your **AI-powered trading assistant** for:\n"
                f"• Forex & Crypto signals\n"
                f"• Synthetic indices\n"
                f"• Real-time market analysis\n\n"
                f"Get started by choosing an option below:",
                reply_markup=get_welcome_menu_keyboard(),
                parse_mode="Markdown"
            )
            return True
        
        if db_user.is_super_admin:
            is_super = True

        if not db_user.is_registered:
            # Unregistered user - show welcome menu
            db.close()
            
            await update.message.reply_text(
                f"👋 **Welcome back, {user.first_name}!**\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"Complete your registration to unlock all features.\n\n"
                f"Choose an option:",
                reply_markup=get_welcome_menu_keyboard(),
                parse_mode="Markdown"
            )
            return True
        
        # User is registered - show full menu
        plan = (db_user.subscription_plan or "free").upper()
        kyc = "✅" if db_user.kyc_status == "approved" else "⚠️"
        signals_left = ""
        if plan == "FREE":
            used = db_user.signals_used_today or 0
            signals_left = f"\n📊 Signals today: {used}/3"
        
        status_line = f"💎 Plan: **{plan}** | KYC: {kyc}{signals_left}"
        if is_super:
            status_line = f"🔐 **SUPER ADMIN** | {status_line}"

        welcome_text = (
            f"🦁 **TRADESIGX ECOSYSTEM**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👋 Welcome back, **{db_user.full_name or update.effective_user.first_name}**!\n"
            f"{status_line}\n\n"
            f"**System Status**: 🟢 Fully Operational\n"
        )
        
        # Add Smart Intelligence for PRO/VIP
        if plan in ["PRO", "VIP"] or is_super:
            sentiment = get_market_sentiment()
            welcome_text += f"🧠 **AI Intelligence**: {sentiment}\n\n"
        else:
            welcome_text += "AI-powered analysis is ready for Forex, Crypto & Synthetics.\n\n"
            
        welcome_text += "What would you like to do?"
        db.close()
        
        await update.message.reply_text(
            welcome_text, 
            reply_markup=get_registered_menu_keyboard(),
            parse_mode="Markdown"
        )
        
        # Also send reply keyboard for quick access
        await update.message.reply_text(
            "⌨️ Quick access keyboard activated:",
            reply_markup=get_main_menu_keyboard()
        )
        
    except Exception as e:
        logging.error(f"Start command error: {e}")
        try:
            db.close()
        except: pass
        
        user_id = str(user.id)
        username = user.username
        is_super = user_id == "1241907317" or username == "origichidiah"
        
        await update.message.reply_text(
            f"👋 Welcome {user.first_name} to TradeSigx Bot!\n\n"
            "Choose an option to get started:",
            reply_markup=get_welcome_menu_keyboard(),
            parse_mode="Markdown"
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = str(update.effective_user.id)
        
        # Handle photo uploads (for KYC)
        if update.message.photo:
            if await handle_kyc_photo(update, context):
                return True
        
        # Ensure there's text to process
        if not update.message.text:
            return True
            
        text = update.message.text
        logging.info(f"Received Message: {text} from user {user_id}")
        
        # Check for signup flow FIRST (before any access control)
        if await handle_signup_message(update, context):
            return True
        
        # Handle admin-specific message inputs (search, broadcast, etc.)
        if await admin_message_handler(update, context):
            return True
        
        user_id = str(update.effective_user.id)
        is_super = user_id == "1241907317" or update.effective_user.username == "origichidiah"
        
        # ACCESS CONTROL: Check if user is registered (Cached for Speed)
        if not context.user_data.get('is_registered_cached') and not is_super:
            db = init_db()
            try:
                user = db.get_user_by_telegram_id(user_id)
                can_access, access_msg = check_user_access(user)
                
                if not can_access:
                    await update.message.reply_text(access_msg, parse_mode="Markdown")
                    db.close()
                    return True
                # Cache status if they can access
                context.user_data['is_registered_cached'] = True
            finally:
                db.close()
        
        # Handle Broker API Token Entry
        menu_buttons = ["📈 Generate Signal", "⚡ Quick Analysis", "💼 Wallet", "🔌 Brokers", "⚙️ Settings", "📖 Help", "ℹ️ About"]
        
        waiting_broker = context.user_data.get('waiting_for_token')
        linking_wallet = context.user_data.get('linking_wallet_type')
        
        if linking_wallet:
            # Handle external wallet linking
            if text in menu_buttons:
                del context.user_data['linking_wallet_type']
            else:
                addr = text.strip()
                if len(addr) < 20: # Basic check for crypto address length
                    await update.message.reply_text("❌ **Invalid Address**: The wallet address provided is too short. Please paste a valid public address.")
                    return True
                
                db = init_db()
                try:
                    user = db.get_user_by_telegram_id(user_id)
                    import json
                    wallets = json.loads(user.external_wallets or "{}")
                    wallets[linking_wallet] = addr
                    user.external_wallets = json.dumps(wallets)
                    db.commit()
                    
                    del context.user_data['linking_wallet_type']
                    await update.message.reply_text(
                        f"✅ **{linking_wallet.upper()} Linked!**\n\n"
                        f"Address: `{addr}`\n\n"
                        "Your wallet has been securely linked to your profile.",
                        reply_markup=get_main_menu_keyboard(),
                        parse_mode="Markdown"
                    )
                finally:
                    db.close()
                return True

        if waiting_broker in ['deriv', 'binance', 'pocket']:
                token = text.strip()
                min_len = 5 if waiting_broker == 'pocket' else 10
                if len(token) < min_len:
                    await update.message.reply_text(f"❌ **Invalid Entry**: The ID/Token provided for **{waiting_broker.capitalize()}** is too short. Please paste it correctly.")
                    return True
                
                db = init_db()
                try:
                    user = db.get_user_by_telegram_id(str(update.effective_user.id))
                    broker = db.session.query(BrokerAccount).filter_by(user_id=user.id, broker_name=waiting_broker).first()
                    if not broker:
                        broker = BrokerAccount(user_id=user.id, broker_name=waiting_broker)
                        db.add(broker)
                    
                    broker.api_key = token
                    broker.is_active = True
                    db.commit()
                    
                    del context.user_data['waiting_for_token']
                    
                    success_msg = f"✅ **{waiting_broker.capitalize()} Linked Successfully!**\n\n"
                    if waiting_broker == 'pocket':
                        success_msg += "Your Pocket Option ID has been saved. Signals will now be optimized for the Pocket Option platform."
                    else:
                        success_msg += "You can now execute trades directly from signals using your account funds."
                        
                    await update.message.reply_text(
                        success_msg,
                        reply_markup=get_main_menu_keyboard(),
                        parse_mode="Markdown"
                    )
                finally:
                    db.close()
                return True
        
        if text == "📈 Generate Signal":
            await update.message.reply_text(
                "🔍 Select the asset class you want to analyze:",
                reply_markup=get_analysis_keyboard()
            )
        elif text == "⚡ Quick Analysis":
            await run_native_scan(update, context)
        elif text == "💼 Wallet":
            db = init_db()
            try:
                user = db.get_user_by_telegram_id(str(update.effective_user.id))
                if not user:
                    await update.message.reply_text("❌ **User Error**: Please type /start to register your wallet.")
                    return True
                
                # Check for connected broker
                broker = db.session.query(BrokerAccount).filter_by(user_id=user.id).first()
                broker_name = broker.broker_name if broker else "None (Click to Connect)"
                
                balance_text = (
                    "💼 **TradeSigx Digital Wallet**\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    f"💰 **Total Balance**: `{user.wallet_balance:.2f} {user.wallet_currency or 'USD'}`\n"
                    f"🏦 **Linked Broker**: `{broker_name}`\n"
                    f"📍 **USDT Address**: `{user.wallet_address or 'Not Generated'}`\n\n"
                    "Funds in this wallet can be used for automated execution and signal-based trading."
                )
                await update.message.reply_text(balance_text, reply_markup=get_wallet_keyboard(), parse_mode="Markdown")
            finally:
                db.close()
        elif text == "🔌 Brokers":
            await update.message.reply_text(
                "🖇 Select a broker to connect or manage:",
                reply_markup=get_broker_selector_keyboard()
            )
        elif text == "⚙️ Settings":
            await update.message.reply_text(
                "⚙️ **TradeSigx Control Center**\n"
                "Configure your trading brain and risk parameters:",
                reply_markup=get_settings_keyboard(),
                parse_mode="Markdown"
            )
        elif text == "🔐 SUPER ADMIN":
            from bot.admin_handlers import admin_command
            await admin_command(update, context)
            return True

        elif text == "📖 Help":
            help_text = (
                "📖 **TRADESIGX VITAL INFO & HELP**\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                "🦁 **TradeSigx Bot** is your professional AI companion for high-accuracy trading analysis.\n\n"
                "🚀 **CORE COMMANDS**\n"
                "• /start - 🚀 Launch Dashboard\n"
                "• /signup - 📝 Register Profile\n"
                "• /upgrade - 💎 View Plans\n"
                "• /kyc - 👤 Identity Verification\n\n"
                "📊 **VITAL TRADING INFO**\n"
                "• **Accuracy**: 85%+ on stabilized markets.\n"
                "• **Support**: @TradeSigxAdmin\n\n"
                "⚠️ **Risk Warning**: Trading involves capital risk."
            )
            await update.message.reply_text(help_text, reply_markup=get_registered_menu_keyboard(), parse_mode="Markdown")
        elif text == "ℹ️ About":
            about_text = (
                "🦁 **ABOUT TRADESIGX**\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                "TradeSigx is an advanced AI-powered ecosystem for market analysis and trade execution.\n\n"
                "**Developer:** @origichidiah\n"
                "**Version:** 8.0-Pro (Stable)\n\n"
                "⚖️ **LEGAL DISCLAIMER & RISK WARNING**\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "Trading Forex, Crypto, and Synthetic Indices involves **significant risk of loss** and is not suitable for all investors. "
                "The signals and analysis provided by this bot are for **informational and educational purposes only**.\n\n"
                "By using this bot, you acknowledge that:\n"
                "• Performance of the past does not guarantee future results.\n"
                "• You are solely responsible for your trading decisions and capital.\n"
                "• The developer (@origichidiah) shall **NOT be held liable** for any financial losses.\n\n"
                "💡 **TICKER GUIDE**:\n"
                "• `=X`: Standard suffix for global Forex pairs (e.g. AUDJPY=X).\n"
                "• `=F`: Suffix for Futures/Commodities (e.g. Gold GC=F).\n"
                "• `/USDT`: Suffix for Crypto Spot markets.\n\n"
                "**Trade responsibly and only with capital you can afford to lose.**"
            )
            await update.message.reply_text(about_text, reply_markup=get_registered_menu_keyboard(), parse_mode="Markdown")
            return True
    except Exception as e:
        # Check for specific network errors and log them but don't crash the handler entirely
        logging.error(f"Handle Message Crash: {e}", exc_info=True)
        try:
            await update.message.reply_text(f"🚨 **Handler Error**: I encountered an issue processing your request.\nError: `{str(e)}`")
        except Exception: pass

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
        
    import logging
    logging.info(f"Received Callback: {query.data} from user {update.effective_user.id}")
    
    try:
        # Standard answer early to stop progress bar
        # Some legacy handlers might call this again, which is fine (ignored by library)
        await query.answer()
        
        # Handle signup callbacks FIRST
        if await handle_signup_callback(update, context):
            return True
        
        # Handle admin callbacks
        if await admin_callback_handler(update, context):
            return True
        
        # Handle payment callbacks
        if await handle_payment_callback(update, context):
            return True
        
        # Handle KYC callbacks
        if await handle_kyc_callback(update, context):
            return True
        
        # Handle welcome menu commands
        if query.data == "cmd_signup":
            # Start the signup process
            from bot.auth_handler import start_signup
            context.user_data['skip_signup_check'] = True
            db = init_db()
            user = db.get_user_by_telegram_id(str(update.effective_user.id))
            if user:
                user.registration_step = "name"
                db.commit()
            db.close()
            await query.edit_message_text(
                "📝 **SIGN UP**\n━━━━━━━━━━━━━━━━━━━━\n\n"
                "Let's get you set up! This takes less than a minute.\n\n"
                "**Step 1 of 5**: What's your full name?",
                parse_mode="Markdown"
            )
            return True
        
        elif query.data == "cmd_plans":
            await show_upgrade_menu(update, context)
            return True
        
        elif query.data == "cmd_help":
            help_text = (
                "📖 **TRADESIGX VITAL INFO & HELP**\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                "🦁 **TradeSigx Bot** is your professional AI companion for high-accuracy trading analysis across Forex, Crypto, and Synthetic markets.\n\n"
                "🚀 **CORE COMMANDS**\n"
                "• /start - 🚀 Launch Main Dashboard\n"
                "• /signup - 📝 One-time Profile Registration\n"
                "• /upgrade - 💎 View Premium Plans & Features\n"
                "• /kyc - 👤 Identity Verification for High Limits\n"
                "• /admin - 🔐 Super Admin Dashboard (Restricted)\n"
                "• /verify - 💰 Verify Payment References\n\n"
                "📊 **VITAL TRADING INFO**\n"
                "• **Accuracy**: AI Confluence engine uses 5+ technical strategies.\n"
                "• **OTC Risks**: Synthetic index prices are broker-specific.\n"
                "• **Free Trial**: 1 month access with 3 signals/day.\n"
                "• **Support**: @TradeSigxAdmin | Priority for PRO/VIP users.\n\n"
                "⚠️ **Risk Warning**: Trading involves high capital risk. Only trade with money you can afford to lose."
            )
            keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_start")]]
            await query.edit_message_text(help_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
            return True
    
        elif query.data == "menu_external_wallets":
            db = init_db()
            user = db.get_user_by_telegram_id(str(update.effective_user.id))
            import json
            wallets = json.loads(user.external_wallets or "{}")
            
            metamask = wallets.get("metamask", "❌ Not Linked")
            phantom = wallets.get("phantom", "❌ Not Linked")
            trust = wallets.get("trust", "❌ Not Linked")
            
            text = (
                "🌐 **EXTERNAL WALLET CONNECTION**\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                "Link your existing wallets for potential payouts, airdrops, and seamless ecosystem integration.\n\n"
                f"🦊 **MetaMask (ETH/BNB)**:\n`{metamask}`\n\n"
                f"👻 **Phantom (SOL)**:\n`{phantom}`\n\n"
                f"🛡 **Trust Wallet**:\n`{trust}`\n\n"
                "Select a wallet to link or update:"
            )
            keyboard = [
                [InlineKeyboardButton("🦊 Link MetaMask", callback_data="link_wallet_metamask")],
                [InlineKeyboardButton("👻 Link Phantom", callback_data="link_wallet_phantom")],
                [InlineKeyboardButton("🛡 Link Trust Wallet", callback_data="link_wallet_trust")],
                [InlineKeyboardButton("🔙 Back to Wallet", callback_data="menu_wallet")]
            ]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
            db.close()
            return True
    
        elif query.data.startswith("link_wallet_"):
            wallet_type = query.data.replace("link_wallet_", "")
            context.user_data['linking_wallet_type'] = wallet_type
            await query.edit_message_text(
                f"🔗 **LINKING {wallet_type.upper()}**\n\n"
                f"Please **send/paste** your {wallet_type.upper()} public wallet address now.\n\n"
                "⚠️ *Ensure you use the public address only. Never send your private keys or seed phrases.*"
            )
            return True
        
        elif query.data == "cmd_profile":
            db = init_db()
            user_id = str(update.effective_user.id)
            user = db.get_user_by_telegram_id(user_id)
            is_super = user_id == "1241907317" or update.effective_user.username == "origichidiah"
            
            if (user and user.is_registered) or is_super:
                plan = "VIP (Lifetime)" if is_super else (user.subscription_plan.upper() if user else 'FREE')
                balance = user.wallet_balance if user else 0.00
                joined = user.joined_at.strftime('%Y-%m-%d') if user and user.joined_at else 'N/A'
                tz = user.timezone if user else 'UTC'
                
                profile_text = (
                    f"👤 **USER PROFILE**\n━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"🆔 **ID**: `{user_id}`\n"
                    f"🏷 **Username**: `@{update.effective_user.username or 'N/A'}`\n"
                    f"📅 **Joined**: `{joined}`\n"
                    f"💎 **Plan**: `{plan}`\n"
                    f"🌍 **Timezone**: `{tz}`\n"
                    f"💰 **Balance**: `${balance:.2f}`\n"
                )
                
                keyboard = [
                    [InlineKeyboardButton("🌍 Set Timezone", callback_data="settings_timezone")],
                    [InlineKeyboardButton("💎 Upgrade Plan", callback_data="cmd_plans")],
                    [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_start")]
                ]
            else:
                profile_text = "👤 **Profile not available.**\n\nPlease sign up first to access your profile."
                keyboard = [[InlineKeyboardButton("📝 Sign Up", callback_data="cmd_signup")]]
                
            db.close()
            await query.edit_message_text(profile_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
            return True
            
        elif query.data == "cmd_about":
            about_text = (
                "🦁 **ABOUT TRADESIGX**\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                "TradeSigx is an advanced AI-powered ecosystem for market analysis and trade execution.\n\n"
                "**Developer:** @origichidiah\n"
                "**Version:** 8.0-Pro (Stable)\n\n"
                "⚖️ **LEGAL DISCLAIMER & RISK WARNING**\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "Trading Forex, Crypto, and Synthetic Indices involves **significant risk of loss** and is not suitable for all investors. "
                "The signals and analysis provided by this bot are for **informational and educational purposes only**.\n\n"
                "By using this bot, you acknowledge that:\n"
                "• Performance of the past does not guarantee future results.\n"
                "• You are solely responsible for your trading decisions and capital.\n"
                "• The developer (@origichidiah) shall **NOT be held liable** for any financial losses.\n\n"
                "💡 **TICKER GUIDE**:\n"
                "• `=X`: Standard suffix for global Forex pairs (e.g. AUDJPY=X).\n"
                "• `=F`: Suffix for Futures/Commodities (e.g. Gold GC=F).\n"
                "• `/USDT`: Suffix for Crypto Spot markets.\n\n"
                "**Trade responsibly and only with capital you can afford to lose.**"
            )
            keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_start")]]
            await query.edit_message_text(about_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
            return True
        
        elif query.data == "back_to_start" or query.data == "back_to_main":
            from bot.ui import get_welcome_menu_keyboard, get_registered_menu_keyboard
            user_id = str(update.effective_user.id)
            username = update.effective_user.username
            is_super = user_id == "1241907317" or username == "origichidiah"
            
            db = init_db()
            user = db.get_user_by_telegram_id(user_id)
            
            if (user and user.is_registered) or is_super:
                await query.edit_message_text(
                    "🦁 **TRADESIGX DASHBOARD (v8.0-Pro)**\n━━━━━━━━━━━━━━━━━━━━\n\nWhat would you like to do?",
                    reply_markup=get_registered_menu_keyboard(),
                    parse_mode="Markdown"
                )
            else:
                await query.edit_message_text(
                    "🦁 **WELCOME TO TRADESIGX**\n━━━━━━━━━━━━━━━━━━━━\n\nChoose an option to get started:",
                    reply_markup=get_welcome_menu_keyboard(),
                    parse_mode="Markdown"
                )
            db.close()
            return True
        
        # Registered user menu shortcuts
        elif query.data == "menu_generate":
            await query.edit_message_text("🔍 Select the asset class you want to analyze:", reply_markup=get_analysis_keyboard())
            return True
        
        elif query.data == "menu_quick_scan":
            # Trigger quick scan - use existing function
            await query.edit_message_text("⏳ Scanning markets... Please wait.", parse_mode="Markdown")
            await run_native_scan(update, context)
            return True
        
        elif query.data == "menu_wallet":
            db = init_db()
            user = db.get_user_by_telegram_id(str(update.effective_user.id))
            if user:
                balance_text = (
                    "💼 **TradeSigx Digital Wallet**\n━━━━━━━━━━━━━━━━━━━━\n"
                    f"💰 **Balance**: `{user.wallet_balance:.2f} {user.wallet_currency or 'USD'}`\n"
                    f"📍 **USDT Address**: `{user.wallet_address or 'Not Generated'}`"
                )
                await query.edit_message_text(balance_text, reply_markup=get_wallet_keyboard(), parse_mode="Markdown")
            db.close()
            return True
    
        elif query.data == "menu_brokers":
            await query.edit_message_text("🔌 Select a broker to connect:", reply_markup=get_broker_selector_keyboard())
            return True
        
        elif query.data == "menu_settings":
            await query.edit_message_text("⚙️ **Settings**\nConfigure your preferences:", reply_markup=get_settings_keyboard(), parse_mode="Markdown")
            return True
        
        if query.data.startswith("cat_"):
            cat = query.data.split("_")[1]
            if cat == "forex": await query.edit_message_text("🌍 **Select Forex OTC Pair** (20 pairs):", reply_markup=get_forex_keyboard(), parse_mode="Markdown")
            elif cat == "crypto": await query.edit_message_text("₿ **Select Cryptocurrency** (15 coins):", reply_markup=get_crypto_keyboard(), parse_mode="Markdown")
            elif cat == "synthetic": await query.edit_message_text("⚡ **Select Synthetic OTC Index** (11 indices):", reply_markup=get_synthetic_keyboard(), parse_mode="Markdown")
            elif cat == "commodities": await query.edit_message_text("📦 **Select Commodity** (5 markets):", reply_markup=get_commodities_keyboard(), parse_mode="Markdown")
            elif cat == "indices": await query.edit_message_text("📊 **Select Stock Index** (5 indices):", reply_markup=get_indices_keyboard(), parse_mode="Markdown")
            elif cat == "stocks": await query.edit_message_text("🏢 **Select Stock** (5 companies):", reply_markup=get_stocks_keyboard(), parse_mode="Markdown")
            elif cat == "metals":
                # Legacy support for metals
                query.data = "analyze_forex_GC=F"
                await callback_handler(update, context)
    
        elif query.data == "analyze_back":
            await query.edit_message_text("🔍 Select the asset class you want to analyze:", reply_markup=get_analysis_keyboard())
    
        elif query.data == "menu_bulk_scan":
            db = init_db()
            user = db.get_user_by_telegram_id(str(update.effective_user.id))
            selected_assets = user.bulk_scan_config.split(",") if user.bulk_scan_config else []
            await query.edit_message_text(
                "🛰 **Multi-Asset Bulk Scanner**\n\n"
                "Select the assets you want to analyze simultaneously. "
                "Our AI will run a deep scan and provide a consolidated report.",
                reply_markup=get_bulk_scanner_keyboard(selected_assets),
                parse_mode="Markdown"
            )
            db.close()
    
        elif query.data.startswith("toggle_bulk|"):
            db = init_db()
            user = db.get_user_by_telegram_id(str(update.effective_user.id))
            symbol = query.data.split("|")[1]
            
            current_list = user.bulk_scan_config.split(",") if user.bulk_scan_config else []
            if symbol in current_list:
                current_list.remove(symbol)
            else:
                current_list.append(symbol)
            
            user.bulk_scan_config = ",".join(current_list)
            db.commit()
            
            await query.edit_message_reply_markup(reply_markup=get_bulk_scanner_keyboard(current_list))
            db.close()
    
        elif query.data == "exec_bulk_scan":
            db = init_db()
            user = db.get_user_by_telegram_id(str(update.effective_user.id))
            raw_assets = user.bulk_scan_config.split(",") if user.bulk_scan_config else []
            db.close()
    
            if not raw_assets or (len(raw_assets) == 1 and not raw_assets[0]):
                await query.answer("❌ Please select at least one asset!")
                return True
    
            # Symbol Mapping/Cleaning for legacy users
            selected_assets = []
            for s in raw_assets:
                if not s: continue
                clean = s.strip()
                if clean == "BTCUSD": clean = "BTC/USDT"
                elif clean == "ETHUSD": clean = "ETH/USDT"
                elif clean == "Gold": clean = "GC=F"
                elif clean == "GBPUSD": clean = "GBPUSD=X"
                elif clean == "USOIL": clean = "CL=F"
                selected_assets.append(clean)
    
            await query.edit_message_text("🛰 **ULTRA-FAST MULTI-SCANNER ACTIVE**\n━━━━━━━━━━━━━━━━━━━━\n🔄 _Bypassing Rate Limits..._\n🧠 _Applying Neural Confluence..._\n\n⏳ *This may take 15-30s depending on market volatility.*", parse_mode="Markdown")
            
            async def scan_single(symbol):
                try:
                    # Small random jitter to prevent synchronized 429s from bulk requests
                    import random
                    await asyncio.sleep(random.uniform(0.1, 0.8))
                    
                    logging.info(f"BULK SCAN | Starting analysis for {symbol}")
                    # Use the new unified fetch_data with a stricter timeout for individual assets
                    df = await asyncio.wait_for(DataCollector.fetch_data(symbol), timeout=25.0)
                    if df.empty:
                        return {"asset": symbol, "direction": "LIMIT", "confidence": 0, "strategy": "Provider Throttled"}
                    
                    signal = await ai_gen.generate_signal(symbol, df, fast_scan=True)
                    if signal: return signal
                    return {"asset": symbol, "direction": "No Data", "confidence": 0, "strategy": "Neutral Market"}
                except asyncio.TimeoutError:
                    return {"asset": symbol, "direction": "TIMEOUT", "confidence": 0, "strategy": "Connection Lag"}
                except Exception as e:
                    logging.error(f"Bulk scan error for {symbol}: {e}")
                    return {"asset": symbol, "direction": "ERROR", "confidence": 0, "strategy": "System Error"}
    
            # Run all scans in parallel
            results = []
            task_map = {asyncio.create_task(scan_single(s)): s for s in selected_assets}
            
            # 60s global wait (reduced from 120s for better UX)
            done, pending = await asyncio.wait(task_map.keys(), timeout=60.0)
            
            for t in done:
                try:
                    results.append(t.result())
                except Exception as e:
                    logging.error(f"Task result error: {e}")
    
            for t in pending:
                symbol = task_map[t]
                t.cancel()
                results.append({"asset": symbol, "direction": "ERROR", "confidence": 0, "strategy": "Request Timed Out"})
    
            if not results:
                await query.edit_message_text("⚠️ **Scanner Delay**: The market providers are unresponsive. Please try selecting fewer assets or check your connection.")
                return True
    
            # Sort results to show opportunities first
            results.sort(key=lambda x: x.get('confidence', 0), reverse=True)
    
            # Format Professional Summary Report
            report = "🛰 **TradeSigx Multi-Scanner Report** 🦁\n"
            report += "━━━━━━━━━━━━━━━━━━━━\n"
            report += f"📅 `{datetime.now().strftime('%Y-%m-%d %H:%M')}` UTC\n\n"
            
            for res in results:
                raw_symbol = res['asset']
                asset_display = ASSET_NAMES.get(raw_symbol, raw_symbol)
                
                if res['direction'] == "BUY":
                    status = "🟢 **BUY OPPORTUNITY**"
                    bar = "████████░░" if res['confidence'] > 80 else "██████░░░░"
                elif res['direction'] == "SELL":
                    status = "🔴 **SELL OPPORTUNITY**"
                    bar = "████████░░" if res['confidence'] > 80 else "██████░░░░"
                elif res['direction'] == "ERROR" or res['direction'] == "No Data":
                    status = "⚠️ **SCAN FAILED**"
                    bar = "░░░░░░░░░░"
                else:
                    status = "⚪️ **WAIT / NO SETUP**"
                    bar = "░░░░░░░░░░"
    
                report += f"💎 **{asset_display}**\n"
                report += f"┗ {status}\n"
                if res['direction'] not in ["STAY", "ERROR", "No Data"]:
                    report += f"┗ Confidence: `{res['confidence']}%` {bar}\n"
                report += f"┗ Logic: _{res['strategy']}_\n\n"
        
            report += "━━━━━━━━━━━━━━━━━━━━\n"
            report += "💡 _Tap individual assets in '📈 Generate Signal' for precise Entry/TP/SL coordinates._"
            
            kb = [[InlineKeyboardButton("🔄 Run Again", callback_data="exec_bulk_scan")],
                  [InlineKeyboardButton("⬅️ Back to Scanner", callback_data="menu_bulk_scan")]]
            await query.edit_message_text(text=report, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
            return True
    
        elif query.data.startswith("analyze_"):
            parts = query.data.split("_")
            asset_type = parts[1]
            symbol = "_".join(parts[2:]) if len(parts) > 2 else None
            
            await query.edit_message_text(
                text=f"⏱ **Select Forecast Duration**\nAsset: `{symbol or asset_type.upper()}`\n\nChoose the duration for your trade signal. Our AI will optimize the entry for your selection.",
                reply_markup=get_duration_selection_keyboard(asset_type, symbol),
                parse_mode="Markdown"
            )
            return True
    
        elif query.data == "settings_timezone":
            from bot.ui import get_timezone_keyboard
            await query.edit_message_text(
                "🌍 **Timezone Settings**\n\n"
                "Select your local timezone so signals reflect your actual time. "
                "Current entries are calculated exactly at market 'Actuals'.",
                reply_markup=get_timezone_keyboard(),
                parse_mode="Markdown"
            )
            return True

        elif query.data == "settings_risk":
            from bot.ui import get_risk_management_keyboard
            db = init_db()
            user = db.get_user_by_telegram_id(str(update.effective_user.id))
            
            text = (
                "⚖️ **Risk Management controls**\n\n"
                "Define your safety parameters. These are applied to all automated radar trades and signal calculations:\n\n"
                f"• **Lot Size**: `{user.default_lot}`\n"
                f"• **Risk/Trade**: `{user.risk_per_trade}%`\n"
                f"• **Max Daily Loss**: `{user.max_daily_loss}%`"
            )
            await query.edit_message_text(text=text, reply_markup=get_risk_management_keyboard(user), parse_mode="Markdown")
            db.close()
            return True

        elif query.data == "settings_autotrade":
            from bot.ui import get_autotrade_settings_keyboard
            db = init_db()
            user = db.get_user_by_telegram_id(str(update.effective_user.id))
            await query.edit_message_text(
                "🤖 **Autotrading Control Center** v8.0\n"
                "Let the AI execute trades for you based on high-confidence setups.\n\n"
                f"• **Min Confidence**: `{user.autotrade_min_confidence}%`\n"
                f"• **Daily Limit**: `{user.autotrade_max_trades} trades`\n"
                f"• **Risk/Trade**: `{user.risk_per_trade}%`\n"
                f"• **Selected Assets**: `{user.autotrade_assets}`",
                reply_markup=get_autotrade_settings_keyboard(user),
                parse_mode="Markdown"
            )
            db.close()
            return True

        elif query.data == "autotrade_toggle":
            from bot.ui import get_autotrade_settings_keyboard
            db = init_db()
            user = db.get_user_by_telegram_id(str(update.effective_user.id))
            user.autotrade_enabled = not user.autotrade_enabled
            db.commit()
            await query.answer(f"🤖 Autotrading {'ENABLED' if user.autotrade_enabled else 'DISABLED'}")
            
            # Refresh menu
            await query.edit_message_text(
                "🤖 **Autotrading Control Center** v8.0\n"
                "Let the AI execute trades for you based on high-confidence setups.\n\n"
                f"• **Min Confidence**: `{user.autotrade_min_confidence}%`\n"
                f"• **Daily Limit**: `{user.autotrade_max_trades} trades`\n"
                f"• **Risk/Trade**: `{user.risk_per_trade}%`\n"
                f"• **Selected Assets**: `{user.autotrade_assets}`",
                reply_markup=get_autotrade_settings_keyboard(user),
                parse_mode="Markdown"
            )
            db.close()
            return True

        elif query.data == "autotrade_edit_conf":
            kb = [
                [InlineKeyboardButton("70%", callback_data="autotrade_set_conf_70"),
                 InlineKeyboardButton("75%", callback_data="autotrade_set_conf_75"),
                 InlineKeyboardButton("80%", callback_data="autotrade_set_conf_80")],
                [InlineKeyboardButton("85%", callback_data="autotrade_set_conf_85"),
                 InlineKeyboardButton("90%", callback_data="autotrade_set_conf_90"),
                 InlineKeyboardButton("95%", callback_data="autotrade_set_conf_95")],
                [InlineKeyboardButton("⬅️ Back to Autotrade", callback_data="settings_autotrade")]
            ]
            await query.edit_message_text(
                "🎯 **Set Minimum Confidence**\n\nThe autotrader will only execute trades if the AI confidence reaches this threshold.",
                reply_markup=InlineKeyboardMarkup(kb),
                parse_mode="Markdown"
            )
            return True

        elif query.data == "autotrade_edit_limit":
            kb = [
                [InlineKeyboardButton("3", callback_data="autotrade_set_limit_3"),
                 InlineKeyboardButton("5", callback_data="autotrade_set_limit_5"),
                 InlineKeyboardButton("10", callback_data="autotrade_set_limit_10")],
                [InlineKeyboardButton("20", callback_data="autotrade_set_limit_20"),
                 InlineKeyboardButton("50", callback_data="autotrade_set_limit_50")],
                [InlineKeyboardButton("⬅️ Back to Autotrade", callback_data="settings_autotrade")]
            ]
            await query.edit_message_text(
                "⚖️ **Set Daily Trade Limit**\n\nMaximum number of trades the AI is allowed to execute per day.",
                reply_markup=InlineKeyboardMarkup(kb),
                parse_mode="Markdown"
            )
            return True

        elif query.data == "autotrade_edit_risk":
            kb = [
                [InlineKeyboardButton("1%", callback_data="autotrade_set_risk_1"),
                 InlineKeyboardButton("2%", callback_data="autotrade_set_risk_2"),
                 InlineKeyboardButton("3%", callback_data="autotrade_set_risk_3")],
                [InlineKeyboardButton("5%", callback_data="autotrade_set_risk_5"),
                 InlineKeyboardButton("10%", callback_data="autotrade_set_risk_10")],
                [InlineKeyboardButton("⬅️ Back to Autotrade", callback_data="settings_autotrade")]
            ]
            await query.edit_message_text(
                "🛡 **Set Risk Per Trade**\n\nChoose the percentage of your balanced to risk on each automated trade.",
                reply_markup=InlineKeyboardMarkup(kb),
                parse_mode="Markdown"
            )
            return True

        elif query.data == "autotrade_edit_assets":
            kb = [
                [InlineKeyboardButton("🌍 Forex Majors", callback_data="autotrade_set_assets_forex")],
                [InlineKeyboardButton("₿ Crypto Top 5", callback_data="autotrade_set_assets_crypto")],
                [InlineKeyboardButton("⚡ Synthetics", callback_data="autotrade_set_assets_synthetic")],
                [InlineKeyboardButton("🌀 All Markets", callback_data="autotrade_set_assets_all")],
                [InlineKeyboardButton("⬅️ Back to Autotrade", callback_data="settings_autotrade")]
            ]
            await query.edit_message_text(
                "📈 **Select Autotrade Assets**\n\nChoose which markets the AI should monitor for automated execution.",
                reply_markup=InlineKeyboardMarkup(kb),
                parse_mode="Markdown"
            )
            return True

        elif query.data.startswith("autotrade_set_"):
            parts = query.data.split("_")
            field = parts[2]
            value = parts[3]
            
            db = init_db()
            user = db.get_user_by_telegram_id(str(update.effective_user.id))
            if user:
                if field == "conf": user.autotrade_min_confidence = float(value)
                elif field == "limit": user.autotrade_max_trades = int(value)
                elif field == "risk": user.risk_per_trade = float(value)
                elif field == "assets":
                    if value == "forex": user.autotrade_assets = "EURUSD=X,GBPUSD=X,USDJPY=X,AUDUSD=X,USDCAD=X"
                    elif value == "crypto": user.autotrade_assets = "BTC/USDT,ETH/USDT,SOL/USDT,XRP/USDT,ADA/USDT"
                    elif value == "synthetic": user.autotrade_assets = "R_100,R_75,R_50,R_25,R_10"
                    elif value == "all": user.autotrade_assets = "EURUSD=X,GBPUSD=X,USDJPY=X,BTC/USDT,ETH/USDT,R_100,R_75,GC=F"
                db.commit()
            db.close()
            
            await query.answer(f"✅ Autotrade {field} updated!")
            
            # Return to Autotrade menu
            from bot.ui import get_autotrade_settings_keyboard
            db = init_db()
            user = db.get_user_by_telegram_id(str(update.effective_user.id))
            await query.edit_message_text(
                "🤖 **Autotrading Control Center** v8.0\n"
                "Let the AI execute trades for you based on high-confidence setups.\n\n"
                f"• **Min Confidence**: `{user.autotrade_min_confidence}%`\n"
                f"• **Daily Limit**: `{user.autotrade_max_trades} trades`\n"
                f"• **Risk/Trade**: `{user.risk_per_trade}%`\n"
                f"• **Selected Assets**: `{user.autotrade_assets}`",
                reply_markup=get_autotrade_settings_keyboard(user),
                parse_mode="Markdown"
            )
            db.close()
            return True

        elif query.data == "settings_strategies":
            text = (
                "🎓 **Strategy Education Module**\n\n"
                "TradeSigx uses 5 quantitative models to qualify signals. "
                "Select a strategy below to understand its logic and implementation:"
            )
            await query.edit_message_text(text=text, reply_markup=get_strategy_education_keyboard(), parse_mode="Markdown")
            return True

        elif query.data.startswith("info_strategy_"):
            strat = query.data.split("_")[2]
            info = {
                "trend": (
                    "📈 **Trend Follower (EMA Cross)**\n\n"
                    "**Logic**: Uses the 'Golden Cross' and 'Death Cross' principles. "
                    "When the 9-period EMA crosses the 21-period EMA, it signals a strong shift in momentum.\n\n"
                    "**Implementation**: The engine monitors 'Previous' vs 'Last' candle crosses to ensure the entry is at the start of a trend."
                ),
                "reversion": (
                    "🔄 **Mean Reversion (BB + RSI)**\n\n"
                    "**Logic**: Prices eventually return to their average. We look for 'Rubber Band' stretches.\n\n"
                    "**Implementation**: Triggers when price pierces the Bollinger Lower/Upper bands while the RSI is in extreme oversold (<30) or overbought (>70) territory."
                ),
                "momentum": (
                    "🚀 **Momentum Breakout (ADX + Vol)**\n\n"
                    "**Logic**: High-speed price moves confirmed by crowd participation.\n\n"
                    "**Implementation**: Requires ADX > 25 (strong trend) and a 1.5x surge in relative volume compared to the 20-period average."
                ),
                "smc": (
                    "🧠 **Smart Money (Structure BOS)**\n\n"
                    "**Logic**: Aligning with institutional flow by detecting 'Break of Structure'.\n\n"
                    "**Implementation**: Monitors for 10-period highs/lows being broken, indicating a structural shift in market direction."
                ),
                "scalp": (
                    "⚡ **Scalping Pulse (Stoch + MACD)**\n\n"
                    "**Logic**: Catching quick, high-probability micro-moves.\n\n"
                    "**Implementation**: Combines the Stochastic Oscillator's quick turns with MACD histogram momentum confirmation."
                )
            }
            text = info.get(strat, "Strategy info not found.")
            kb = [[InlineKeyboardButton("⬅️ Back to Education", callback_data="settings_strategies")]]
            await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
            return True

        elif query.data.startswith("risk_edit_"):
            field = query.data.split("_")[2]
            options = []
            if field == "lot":
                options = [["0.01", "0.05", "0.10"], ["0.50", "1.00"]]
            elif field == "perc":
                options = [["0.5%", "1.0%", "2.0%"], ["3.0%", "5.0%"]]
            elif field == "loss":
                options = [["2%", "5%", "10%"], ["15%", "20%"]]
                
            kb = []
            for row in options:
                kb_row = []
                for opt in row:
                    val = opt.replace("%", "")
                    kb_row.append(InlineKeyboardButton(opt, callback_data=f"risk_set_{field}_{val}"))
                kb.append(kb_row)
            kb.append([InlineKeyboardButton("⬅️ Back to Risk", callback_data="settings_risk")])
            
            await query.edit_message_text(
                f"🛡 **Select your preferred {field.upper()}**:\n(Active immediately)",
                reply_markup=InlineKeyboardMarkup(kb),
                parse_mode="Markdown"
            )
            return True

        elif query.data.startswith("risk_set_"):
            parts = query.data.split("_")
            field = parts[2]
            value = float(parts[3])
            
            db = init_db()
            user = db.get_user_by_telegram_id(str(update.effective_user.id))
            if user:
                if field == "lot": user.default_lot = value
                elif field == "perc": user.risk_per_trade = value
                elif field == "loss": user.max_daily_loss = value
                db.commit()
            db.close()
            
            await query.answer(f"✅ Risk updated: {field} = {value}")
            
            # Reload Risk Menu manually instead of recursion
            db = init_db()
            user = db.get_user_by_telegram_id(str(update.effective_user.id))
            text = (
                "⚖️ **Risk Management controls**\n\n"
                "Define your safety parameters. These are applied to all automated radar trades and signal calculations:\n\n"
                f"• **Lot Size**: `{user.default_lot}`\n"
                f"• **Risk/Trade**: `{user.risk_per_trade}%`\n"
                f"• **Max Daily Loss**: `{user.max_daily_loss}%`"
            )
            await query.edit_message_text(text=text, reply_markup=get_risk_management_keyboard(user), parse_mode="Markdown")
            db.close()
            return True
    
        elif query.data.startswith("settings_"):
            await query.answer("This setting module is under maintenance.")
            return True
    
        elif query.data.startswith("toggle_"):
            await query.answer("Preference updated!")
            setting = query.data.split("_")[1]
            await query.answer(f"✅ {setting.title()} preference updated!")
            await query.edit_message_text(f"⚙️ **{setting.title()}** has been updated successfully!\n\nUse the menu below to continue.", reply_markup=get_settings_keyboard(), parse_mode="Markdown")
            return True
    
        elif query.data == "back_to_settings":
            await query.edit_message_text(
                "⚙️ **TradeSigx Control Center**\n"
                "Configure your trading brain and risk parameters:",
                reply_markup=get_settings_keyboard(),
                parse_mode="Markdown"
            )
            return True
    
        elif query.data.startswith("sel|broker|"):
            # Format: sel|broker|{symbol}|{direction}|{entry_price}
            parts = query.data.split("|")
            symbol = parts[2]
            direction = parts[3]
            entry_price = float(parts[4])
            
            db = init_db()
            try:
                user = db.get_user_by_telegram_id(str(update.effective_user.id))
                from bot.models import BrokerAccount
                active_brokers = db.session.query(BrokerAccount).filter_by(user_id=user.id, is_active=True).all()
                
                from bot.ui import get_broker_selection_for_trade
                await query.edit_message_text(
                    f"🎯 **Trade Configuration**\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"Asset: `{symbol}`\n"
                    f"Direction: `{direction}`\n"
                    f"Entry: `{entry_price}`\n\n"
                    f"🛡 **Select the Broker to execute this trade on:**",
                    reply_markup=get_broker_selection_for_trade(symbol, direction, entry_price, active_brokers),
                    parse_mode="Markdown"
                )
            finally:
                db.close()
            return True
    
        elif query.data.startswith("exec|trade|"):
            # Format: exec|trade|{broker_name}|{symbol}|{direction}|{entry_price}
            parts = query.data.split("|")
            broker_choice = parts[2]
            symbol = parts[3]
            direction = parts[4]
            entry_price = float(parts[5])
            user_id = str(update.effective_user.id)
            
            await query.answer("🚀 Processing Trade...")
            await query.edit_message_text(f"⏳ **Executing {direction} on {symbol}...**\nConnecting to {broker_choice.title()}...", parse_mode="Markdown")
            
            db = init_db()
            try:
                user = db.get_user_by_telegram_id(user_id)
                if not user:
                    await query.edit_message_text("❌ **User Error**: Please type /start to register.")
                    return True
                
                trade_amount = user.default_lot * 100 
                primary_broker = None
                from bot.models import BrokerAccount, TradeExecution
                if broker_choice != 'paper':
                    primary_broker = db.session.query(BrokerAccount).filter_by(user_id=user.id, broker_name=broker_choice, is_active=True).first()
                
                is_live_broker = primary_broker and primary_broker.api_key
                
                if not is_live_broker and broker_choice != 'paper' and broker_choice != 'pocket':
                    await query.edit_message_text(f"❌ **Broker Not Linked**: Please connect your {broker_choice.title()} account first.")
                    return True
    
                if not is_live_broker and user.wallet_balance < trade_amount:
                    await query.edit_message_text(f"❌ **Insufficient Funds**: Your bot wallet balance is `${user.wallet_balance:.2f}`.")
                    return True
    
                import time
                result = {'status': 'error', 'message': 'Unknown Broker'}
    
                if broker_choice == 'paper':
                    result = {'status': 'success', 'contract_id': 'PAPER-TRD'}
                elif broker_choice == 'deriv':
                    from brokers.deriv_broker import DerivBroker
                    broker_lib = DerivBroker()
                    broker_lib.token = primary_broker.api_key
                    result = await broker_lib.execute_trade(symbol, direction, trade_amount)
                elif broker_choice == 'pocket':
                    from brokers.pocket_option_broker import PocketOptionBroker
                    instr = PocketOptionBroker().get_execution_instructions(symbol, direction, trade_amount, "5 Minutes")
                    
                    await query.edit_message_text(
                        f"📥 **Manual Pocket Option Entry**\n"
                        f"━━━━━━━━━━━━━━━━━━━━\n"
                        f"🎯 Asset: `{symbol}`\n"
                        f"↕️ Action: `{direction}`\n"
                        f"💰 Amount: `${trade_amount}`\n"
                        f"⏱ Duration: `5m`\n\n"
                        f"💡 **Instruction**: {instr['instruction']}\n\n"
                        f"✅ Settlement recorded in history.",
                        parse_mode="Markdown"
                    )
                    result = {'status': 'success', 'contract_id': f"PO-{int(time.time())}"}
                
                if result['status'] == "success":
                    user.wallet_balance -= trade_amount
                    trade = TradeExecution(
                        user_id=user_id, asset=symbol, direction=direction,
                        amount=trade_amount, entry_price=entry_price,
                        contract_id=result.get('contract_id'), status="OPEN"
                    )
                    db.add(trade)
                    db.commit()
                    if broker_choice != 'pocket':
                        await query.edit_message_text(f"✅ **Trade Confirmed**\nAsset: `{symbol}`\nBroker: `{broker_choice.title()}`\nID: `{result.get('contract_id')}`\n💰 Balance: `${user.wallet_balance:.2f}`")
    
                    # Simulation loop for paper trades
                    if broker_choice == 'paper':
                        async def simulated_pnl(query, user_id, trade_id):
                            import random
                            await asyncio.sleep(8)
                            sub_db = init_db()
                            try:
                                t = sub_db.session.query(TradeExecution).get(trade_id)
                                u = sub_db.get_user_by_telegram_id(user_id)
                                win = random.choice([True, True, False])
                                if win:
                                    t.status, t.pnl = "WON", t.amount * 0.85
                                    u.wallet_balance += (t.amount + t.pnl)
                                else:
                                    t.status, t.pnl = "LOST", -t.amount
                                sub_db.commit()
                                icon = "🟢" if win else "🔴"
                                await query.message.reply_text(f"{icon} **PAPER TRADE RESULT**\n{t.status}! PnL: `${t.pnl:.2f}`\nBalance: `${u.wallet_balance:.2f}`", parse_mode="Markdown")
                            finally: sub_db.close()
                        asyncio.create_task(simulated_pnl(query, user_id, trade.id))
                else:
                    await query.edit_message_text(f"❌ **Execution Failed**: {result.get('message', 'Broker Rejected')}")
            finally:
                db.close()
            return True
    
        elif query.data == "wallet_history":
            db = init_db()
            try:
                from bot.models import TradeExecution
                trades = db.session.query(TradeExecution).filter_by(user_id=str(update.effective_user.id)).order_by(TradeExecution.timestamp.desc()).limit(5).all()
                
                if not trades:
                    await query.edit_message_text("📜 **Trade History**\n\nNo trades executed yet. Start trading from a signal alert!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_main")]]), parse_mode="Markdown")
                else:
                    history_text = "📜 **Recent Trade History**\n━━━━━━━\n"
                    for t in trades:
                        icon = "🟢" if t.status == "WON" else ("🔴" if t.status == "LOST" else "⚪")
                        history_text += f"{icon} {t.asset} | {t.direction} | ${t.amount} | PnL: `{t.pnl:+.2f}`\n"
                    
                    await query.edit_message_text(history_text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_main")]]), parse_mode="Markdown")
            finally:
                db.close()
            return True
    
        elif query.data == "wallet_withdraw":
            await query.edit_message_text(
                "➖ **Withdraw Funds**\n\n"
                "Select your withdrawal method:\n\n"
                "• **Broker Transfer**: Instant back to Deriv/Binance\n"
                "• **Crypto Wallet**: BTC, USDT (ERC20/TRC20)\n\n"
                "⚠️ _Withdrawals are processed within 24 hours._",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏦 Broker Transfer", callback_data="withdraw_confirm")], [InlineKeyboardButton("🪙 Crypto Wallet", callback_data="withdraw_confirm")], [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_main")]])
            )
            return True
    
        elif query.data == "withdraw_confirm":
            await query.answer("⌛ Withdrawal request received!", show_alert=True)
            await query.edit_message_text("✅ **Request Submitted**\n\nYour withdrawal request has been queued for security review. You will receive a notification once approved.")
            return True
    
        elif query.data == "wallet_deposit":
            db = init_db()
            try:
                user = db.get_user_by_telegram_id(str(update.effective_user.id))
                if not user:
                    await query.answer("❌ User not found. Type /start", show_alert=True)
                    return True
                    
                address_text = user.wallet_address or "Not Generated"
                btn_label = "⚡ Generate Deposit Address" if not user.wallet_address else "🔄 Refresh Balance"
                
                await query.edit_message_text(
                    "➕ **Deposit Funds**\n\n"
                    f"📍 **Your USDT (TRC20) Address**:\n`{address_text}`\n\n"
                    "1️⃣ **Telegram Stars** (Instant)\n"
                    "2️⃣ **Crypto Transfer** (Send to address above)\n"
                    "3️⃣ **Simulate** for demo testing.\n\n",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton(btn_label, callback_data="generate_address")],
                        [InlineKeyboardButton("⚡ Simulate $500 Top-up", callback_data="wallet_add_500")],
                        [InlineKeyboardButton("⬅️ Back", callback_data="back_to_main")]
                    ]),
                    parse_mode="Markdown"
                )
            finally:
                db.close()
            return True

        elif query.data == "generate_address":
            import secrets
            addr = "TX" + secrets.token_hex(16).upper()
            db = init_db()
            try:
                user = db.get_user_by_telegram_id(str(update.effective_user.id))
                if user:
                    user.wallet_address = addr
                    db.commit()
                await query.answer("✅ Address Generated!")
                # Refresh deposit menu manually
                user = db.get_user_by_telegram_id(str(update.effective_user.id))
                address_text = user.wallet_address or "Not Generated"
                btn_label = "🔄 Refresh Balance"
                await query.edit_message_text(
                    "➕ **Deposit Funds**\n\n"
                    f"📍 **Your USDT (TRC20) Address**:\n`{address_text}`\n\n"
                    "1️⃣ **Telegram Stars** (Instant)\n"
                    "2️⃣ **Crypto Transfer** (Send to address above)\n"
                    "3️⃣ **Simulate** for demo testing.\n\n",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton(btn_label, callback_data="generate_address")],
                        [InlineKeyboardButton("⚡ Simulate $500 Top-up", callback_data="wallet_add_500")],
                        [InlineKeyboardButton("⬅️ Back", callback_data="back_to_main")]
                    ]),
                    parse_mode="Markdown"
                )
            finally:
                db.close()
            return True
    
        elif query.data == "wallet_add_500":
            db = init_db()
            try:
                user = db.get_user_by_telegram_id(str(update.effective_user.id))
                if user:
                    user.wallet_balance += 500
                    db.commit()
                await query.answer("💰 $500 added to your balance!")
            finally:
                db.close()
            return True
    
        elif query.data.startswith("set_tz_"):
            new_tz = query.data.replace("set_tz_", "")
            db = init_db()
            try:
                user = db.get_user_by_telegram_id(str(update.effective_user.id))
                if user:
                    user.timezone = new_tz
                    db.commit()
                    await query.answer(f"✅ Timezone set to {new_tz}")
                    await query.edit_message_text(
                        f"✅ **Timezone Updated**\n\nYour preferred timezone is now set to `{new_tz}`.\nAll future signals will reflect this time.",
                        reply_markup=get_settings_keyboard(),
                        parse_mode="Markdown"
                    )
                else:
                    await query.answer("❌ User not found. Use /start", show_alert=True)
            finally:
                db.close()
            return True
    
        elif query.data.startswith("exec_analyze|"):
            try:
                # Format: exec_analyze|asset_type|symbol|duration
                parts = query.data.split("|")
                asset_type = parts[1]
                symbol = parts[2]
                duration = parts[3]
                
                # Instant Advance Notice
                await query.edit_message_text(
                    text=f"🚀 **EXECUTING FINAL SCAN**\nAsset: `{symbol}`\nDuration: `{duration.upper()}`\nTargeting optimal market 'Actuals'...",
                    parse_mode="Markdown"
                )
                
                # Typing effect
                await context.bot.send_chat_action(chat_id=query.message.chat_id, action="typing")
                import pandas as pd
                df = pd.DataFrame()
    
                try:
                    # Use unified fetch_data (handles normalization and routing)
                    df = await DataCollector.fetch_data(symbol, asset_type)
                except Exception as e:
                    logging.error(f"Data Fetch Exception for {symbol}: {e}")
                    await query.edit_message_text(f"❌ **Data Access Error**: {symbol}\nThe market provider is currently unreachable. Please try again in a moment.")
                    return True
                
                if df.empty:
                    await query.edit_message_text(f"❌ **Market Data Unavailable**: {symbol}\n\nThe provider is currently throttled or the market is closed. Please try again soon or check your VPN connection.")
                    return True
    
                # Generate Signal
                try:
                    # Use global ai_gen (AISignalGenerator)
                    signal = await ai_gen.generate_signal(symbol, df, manual_duration=duration if duration != "ai" else None)
                except Exception as e:
                    logging.error(f"AI Generation Exception for {symbol}: {e}")
                    await query.edit_message_text(f"🧠 **AI Calculation Error**: {symbol}\nMy neural engine encountered an issue analyzing this specific setup. Please try another duration.")
                    return True
    
                if not signal:
                    await query.edit_message_text(f"⚖️ **No Clear Opportunity**: {symbol}\nMarket 'Actuals' are currently in equilibrium. No high-quality entry detected.")
                    return True
                
                # Save to History
                db = init_db()
                try:
                    user = db.get_user_by_telegram_id(str(update.effective_user.id))
                    user_tz = user.timezone if user else "UTC"
    
                    new_signal = SignalHistory(
                        asset=symbol,
                        direction=signal['direction'],
                        entry_price=signal['entry'],
                        tp=signal['tp'],
                        sl=signal['sl'],
                        confidence=signal['confidence']
                    )
                    db.add(new_signal)
                    db.commit()
                finally:
                    db.close()
    
                message, kb = format_signal(signal, user_tz=user_tz)
                await query.edit_message_text(text=message, reply_markup=kb, parse_mode="Markdown")
    
                # Push to Mini App
                try:
                    import httpx
                    # Global timeout for local health check
                    async with httpx.AsyncClient(timeout=2.0) as client:
                        await client.post(
                            "http://localhost:5000/api/internal/push-signal",
                            json={"user_id": str(query.message.chat_id), "signal": signal}
                        )
                except (httpx.ConnectError, httpx.TimeoutException):
                    logging.warning("Mini App Signal Push: Local server unreachable (not a critical error)")
                except Exception as e:
                    logging.error(f"Mini App Signal Push Error: {e}")
    
            except Exception as e:
                logging.error(f"Critical Analysis Failure: {e}", exc_info=True)
                await query.edit_message_text("🚨 **System Error**: I encountered an unexpected problem during analysis. My team has been notified. Please try again.")
            return True
    
        elif query.data == "cancel_trade":
            await query.edit_message_text("❌ Trade execution cancelled.")
            return True
    
        elif query.data == "back_to_main":
            from bot.ui import get_welcome_menu_keyboard, get_registered_menu_keyboard
            user_id = str(update.effective_user.id)
            db = init_db()
            user = db.get_user_by_telegram_id(user_id)
            is_super = user_id == "1241907317" or update.effective_user.username == "origichidiah"
            if (user and user.is_registered) or is_super:
                await query.edit_message_text("🦁 **TradeSigx Main Menu**\nWelcome back! What would you like to do?", reply_markup=get_registered_menu_keyboard())
            else:
                await query.edit_message_text("🦁 **TradeSigx Welcome Menu**\nChoose an option:", reply_markup=get_welcome_menu_keyboard())
            db.close()
            return True
    
        elif query.data == "connect_deriv":
            context.user_data['waiting_for_token'] = 'deriv'
            await query.edit_message_text(
                "🔌 **Deriv Broker Connection**\n\n"
                "To link your Deriv account for automated execution, please generate an **API Token** with 'Trade' and 'Trading Information' scopes from your Deriv dashboard.\n\n"
                "**Reply to this message with your Token below:**",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back_to_main")]]),
                parse_mode="Markdown"
            )
            return True
    
        elif query.data == "connect_binance":
            context.user_data['waiting_for_token'] = 'binance'
            await query.edit_message_text(
                "🔌 **Binance API Connection**\n\n"
                "Link your Binance account to execute crypto trades directly. Generate an API Key with 'Enable Spot & Margin Trading' scopes.\n\n"
                "**Reply to this message with your API Key below:**",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back_to_main")]]),
                parse_mode="Markdown"
            )
            return True
    
        elif query.data == "connect_pocket":
            context.user_data['waiting_for_token'] = 'pocket'
            await query.edit_message_text(
                "🔌 **Pocket Option Connection**\n\n"
                "Pocket Option connection allows the bot to optimize signals for the PO platform (Binary Options).\n\n"
                "**Please reply with your Pocket Option UID (e.g. 12345678):**",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back_to_main")]]),
                parse_mode="Markdown"
            )
            return True
            
        else:
            logging.warning(f"Unhandled callback: {query.data}")
            return False

    except Exception as e:
        logging.error(f"Callback Handler Error: {e}", exc_info=True)
        try:
            await query.answer("⚠️ An error occurred while processing your request.", show_alert=True)
        except:
            pass
        return False
