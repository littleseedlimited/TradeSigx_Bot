import os
import logging
import asyncio
import subprocess
import sys
from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from bot.handlers import start_command, handle_message, callback_handler
from utils.db import init_db
from api.server import app as api_app  # Combined Process
import uvicorn

# Load environment variables
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start_combined_api():
    """Starts the FastAPI server within the same process to save memory"""
    config = uvicorn.Config(api_app, host="0.0.0.0", port=int(os.getenv("PORT", 5000)), log_level="info")
    server = uvicorn.Server(config)
    await server.serve()

async def start_polling(application):
    """Wait for application to be initialized then start polling"""
    await application.initialize()
    await application.start()
    await application.updater.start_polling()

async def market_radar_loop(application):
    """Background Radar: Scans every 30 minutes and notifies users of high-confidence trades"""
    print("Market Radar Logic Initialized.")
    from bot.handlers import scan_market_now
    from utils.formatter import format_signal
    from utils.db import init_db
    
    # Simple deduplication cache: symbol_direction -> last_alert_time
    last_alerts = {}
    import time
    
    while True:
        try:
            logging.info("Radar Detector: Scanning Markets for prime setups...")
            signals = await scan_market_now()
            
            if signals:
                db = init_db()
                users = db.get_all_users()
                
                for signal in signals:
                    # 1. Anytime Signals Mode (1% Threshold)
                    # 2. Must meet the trend-alignment criteria (handled by engine)
                    if signal['confidence'] < 1:
                        continue
    
                    # Deduplication logic (skip if we alerted for this asset/direction in the last hour)
                    alert_key = f"{signal['asset']}_{signal['direction']}"
                    if alert_key in last_alerts and (time.time() - last_alerts[alert_key]) < 3600:
                        continue
                    
                    # Parallel Message Dispatch
                    async def notify_user(user, signal, last_alerts, alert_key):
                        try:
                            if not user.notifications_enabled:
                                return
                                
                            user_tz = user.timezone or "UTC"
                            message, kb = format_signal(signal, user_tz=user_tz)
                            full_msg = f"🔔 **SIGNAL DETECTED** (High Confidence) 🔔\n\n{message}"
                            
                            await application.bot.send_message(
                                chat_id=user.telegram_id,
                                text=full_msg,
                                reply_markup=kb,
                                parse_mode="Markdown"
                            )
                        except Exception:
                            pass # Handle blocked users

                    # Create batches of 5 to prevent RAM spikes
                    batch_size = 5
                    for i in range(0, len(users), batch_size):
                        batch = users[i:i + batch_size]
                        notif_tasks = [notify_user(u, signal, last_alerts, alert_key) for u in batch]
                        if notif_tasks:
                            await asyncio.gather(*notif_tasks)
                        await asyncio.sleep(0.1) # Micro-pause for RAM stability
                    
                    last_alerts[alert_key] = time.time()
                    logging.info(f"Radar Alert: Dispatched {alert_key} to {len(users)} users.")
                
                db.close()
                
            # High-Frequency Scan: Every 5 minutes (300 seconds)
            await asyncio.sleep(300) 
            
        except Exception as e:
            logging.error(f"Radar Detector Error: {e}")
            await asyncio.sleep(60) # Back off on error

async def main():
    # Initialize Database & Seed Plans
    from utils.db import init_db, seed_plans
    init_db(force_create=False)
    seed_plans()
    
    # Check for Token
    if not TOKEN:
        print("CRITICAL: TELEGRAM_BOT_TOKEN not found in .env file.")
        return

    # Combined API & Bot Process (RAM Efficient)
    asyncio.create_task(start_combined_api())
    print("TradeSigx API Server Initialized in Main Process.")
    
    print("TradeSigx Bot: Building Application layer...")
    # Build Application
    from telegram.request import HTTPXRequest
    request = HTTPXRequest(connect_timeout=60, read_timeout=60)
    application = ApplicationBuilder().token(TOKEN).request(request).build()
    
    print("TradeSigx Bot: Registering Handlers...")
    # Add Handlers
    application.add_handler(CommandHandler("start", start_command))
    
    # New Auth & Admin Commands
    from bot.admin_handlers import admin_command
    from bot.auth_handler import start_signup
    from bot.payment_handler import show_upgrade_menu, verify_payment_command, handle_successful_payment
    from bot.kyc_handler import start_kyc, kyc_status
    
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CommandHandler("signup", start_signup))
    application.add_handler(CommandHandler("upgrade", show_upgrade_menu))
    application.add_handler(CommandHandler("verify", verify_payment_command))
    application.add_handler(CommandHandler("kyc", start_kyc))
    application.add_handler(CommandHandler("kycstatus", kyc_status))
    
    # Payment success handler (for Telegram Stars)
    from telegram.ext import PreCheckoutQueryHandler
    async def precheckout_callback(update, context):
        await update.pre_checkout_query.answer(ok=True)
    application.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, handle_successful_payment))
    
    # Photo handler (for KYC documents)
    application.add_handler(MessageHandler(filters.PHOTO, handle_message))
    
    # Text message handler
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    application.add_handler(CallbackQueryHandler(callback_handler))
    
    # NEW: Set Bot Commands Menu (Blue Button in Telegram)
    async def set_commands(app):
        from telegram import BotCommand
        commands = [
            BotCommand("start", "🚀 Launch Main Menu"),
            BotCommand("signup", "📝 Register Profile"),
            BotCommand("upgrade", "💎 View Subscription Plans"),
            BotCommand("kyc", "👤 Verify Identity"),
            BotCommand("admin", "🔐 Super Admin Dashboard (Restricted)"),
            BotCommand("verify", "💰 Verify Payment Reference")
        ]
        await app.bot.set_my_commands(commands)
        logging.info("Bot command menu initialized successfully.")

    print("TradeSigx Bot: Entering Safe-Start sequence...")
    
    # PROTECTIVE WATCHDOG & RECOVERY LOOP
    max_retries = 20
    retry_delay = 15
    market_radar_task = None
    autotrader_task = None
    
    while True:
        for attempt in range(max_retries):
            try:
                # 1. Clear potentially stalled tasks
                if market_radar_task: market_radar_task.cancel()
                if autotrader_task: autotrader_task.cancel()
                
                if application.updater and application.updater.running:
                    await application.updater.stop()
                    await application.stop()
                    await application.shutdown()
                
                # 2. Re-establish Polling
                await application.initialize()
                await set_commands(application)
                await application.start()
                await application.updater.start_polling(drop_pending_updates=True)
                print(f"TradeSigx Bot Online (Recovery Attempt {attempt}).")
                
                # 3. Start Heartbeat tasks
                market_radar_task = asyncio.create_task(market_radar_loop(application))
                from engine.autotrader import AutoTrader
                from bot.handlers import ai_gen
                shared_auto_trader = AutoTrader(ai=ai_gen)
                autotrader_task = asyncio.create_task(shared_auto_trader.start())
                
                # 4. Stay Alive & Monitor
                while True:
                    await asyncio.sleep(60)
                    if not application.updater or not application.updater.running:
                        break
                        
            except Exception as e:
                print(f"System Pulsar: Recovery Attempt {attempt + 1} failed: {e}")
                await asyncio.sleep(retry_delay)
        
        await asyncio.sleep(60) # Global cooldown
    
    if api_process:
        api_process.terminate()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
