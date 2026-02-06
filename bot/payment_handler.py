"""
Payment Handler for TradeSigx Bot
Supports: Paystack, Crypto (USDT), Bank Transfer, Telegram Stars
"""
import os
import logging
import secrets
import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import ContextTypes
from utils.db import init_db, User, PaymentTransaction

# Plan pricing (in USD)
PLAN_PRICES = {
    "basic": {"usd": 9.99, "ngn": 15000, "stars": 500},
    "pro": {"usd": 29.99, "ngn": 45000, "stars": 1500},
    "vip": {"usd": 99.99, "ngn": 150000, "stars": 5000}
}

# Paystack configuration
PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY", "")
PAYSTACK_PUBLIC_KEY = os.getenv("PAYSTACK_PUBLIC_KEY", "")

# Crypto wallet for receiving payments
CRYPTO_WALLET = {
    "USDT_TRC20": "TYourWalletAddressHere",
    "USDT_BEP20": "0xYourWalletAddressHere",
    "BTC": "bc1qYourBitcoinAddressHere"
}

# Bank details for transfer
BANK_DETAILS = {
    "bank_name": "Your Bank Name",
    "account_name": "TradeSigx Ltd",
    "account_number": "0123456789",
    "sort_code": "058",
    "note": "Use your Telegram ID as reference"
}

async def show_upgrade_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show available subscription plans"""
    user_id = str(update.effective_user.id)
    
    db = init_db()
    try:
        user = db.get_user_by_telegram_id(user_id)
        current_plan = user.subscription_plan if user else "free"
        
        text = (
            "💎 **UPGRADE YOUR PLAN**\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Your current plan: **{current_plan.upper()}**\n\n"
            "🆓 **FREE** - $0/month\n"
            "   • 3 signals per day\n"
            "   • 15-minute delay\n"
            "   • Community support\n\n"
            "💎 **BASIC** - $9.99/month\n"
            "   • 15 signals per day\n"
            "   • Real-time signals\n"
            "   • Email support\n\n"
            "⭐ **PRO** - $29.99/month\n"
            "   • Unlimited signals\n"
            "   • Automated Radar Scanner\n"
            "   • Priority support\n\n"
            "👑 **VIP** - $99.99/month\n"
            "   • Everything in Pro\n"
            "   • Dedicated account manager\n"
            "   • Early access to features\n"
            "   • Tailored professional support\n\n"
            "Select a plan to upgrade:"
        )
        
        keyboard = [
            [InlineKeyboardButton("💎 Basic - $9.99", callback_data="pay_plan_basic")],
            [InlineKeyboardButton("⭐ Pro - $29.99", callback_data="pay_plan_pro")],
            [InlineKeyboardButton("👑 VIP - $99.99", callback_data="pay_plan_vip")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_start")]
        ]
        
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        else:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    finally:
        db.close()

async def handle_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Handle payment-related callbacks. Returns True if handled."""
    query = update.callback_query
    data = query.data
    
    if not data.startswith("pay_"):
        return False
    
    await query.answer()
    user_id = str(update.effective_user.id)
    
    # Plan Selection
    if data.startswith("pay_plan_"):
        plan = data.replace("pay_plan_", "")
        context.user_data['selected_plan'] = plan
        
        prices = PLAN_PRICES.get(plan, {})
        
        text = (
            f"💳 **PAYMENT FOR {plan.upper()} PLAN**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"💵 Price: **${prices.get('usd', 0):.2f}** / month\n"
            f"🇳🇬 NGN: ₦{prices.get('ngn', 0):,}\n"
            f"⭐ Telegram Stars: {prices.get('stars', 0)}\n\n"
            f"Select your preferred payment method:"
        )
        
        keyboard = [
            [InlineKeyboardButton("💳 Paystack (Card/Bank)", callback_data=f"pay_method_paystack_{plan}")],
            [InlineKeyboardButton("🪙 Crypto (USDT)", callback_data=f"pay_method_crypto_{plan}")],
            [InlineKeyboardButton("🏦 Bank Transfer", callback_data=f"pay_method_bank_{plan}")],
            [InlineKeyboardButton("⭐ Telegram Stars", callback_data=f"pay_method_stars_{plan}")],
            [InlineKeyboardButton("🔙 Back to Plans", callback_data="upgrade_menu")]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return True
    
    # Paystack Payment
    if data.startswith("pay_method_paystack_"):
        plan = data.replace("pay_method_paystack_", "")
        prices = PLAN_PRICES.get(plan, {})
        
        db = init_db()
        try:
            user = db.get_user_by_telegram_id(user_id)
            if not user or not user.email:
                await query.edit_message_text(
                    "❌ Please complete your registration with a valid email first.\n"
                    "Use /signup to register."
                )
                return True
            
            # Generate payment reference
            ref = f"TSX-{secrets.token_hex(8).upper()}"
            
            # Create payment record
            db.create_payment(
                user_id=user.id, 
                amount=prices.get('ngn', 0), 
                method="paystack", 
                plan=plan, 
                ref=ref
            )
            
            # Generate Paystack link (simplified - in production use API)
            amount_kobo = int(prices.get('ngn', 0) * 100)
            paystack_url = f"https://paystack.com/pay/tradesigx-{plan}"
            
            text = (
                f"💳 **PAYSTACK PAYMENT**\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"**Plan**: {plan.upper()}\n"
                f"**Amount**: ₦{prices.get('ngn', 0):,}\n"
                f"**Reference**: `{ref}`\n\n"
                f"Click the button below to complete payment:\n\n"
                f"📧 Payment will be sent to: {user.email}\n\n"
                f"_After payment, use /verify {ref} to activate your plan._"
            )
            
            keyboard = [
                [InlineKeyboardButton("💳 Pay Now", url=paystack_url)],
                [InlineKeyboardButton("✅ I've Paid", callback_data=f"pay_verify_{ref}")],
                [InlineKeyboardButton("🔙 Back to Plan Selection", callback_data=f"pay_plan_{plan}")]
            ]
            
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        finally:
            db.close()
        return True
    
    # Crypto Payment
    if data.startswith("pay_method_crypto_"):
        plan = data.replace("pay_method_crypto_", "")
        prices = PLAN_PRICES.get(plan, {})
        
        ref = f"TSX-{secrets.token_hex(8).upper()}"
        
        db = init_db()
        try:
            user = db.get_user_by_telegram_id(user_id)
            db.create_payment(
                user_id=user.id if user else 0, 
                amount=prices.get('usd', 0), 
                method="crypto", 
                plan=plan, 
                ref=ref
            )
        finally:
            db.close()
        
        text = (
            f"🪙 **CRYPTO PAYMENT**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"**Plan**: {plan.upper()}\n"
            f"**Amount**: ${prices.get('usd', 0):.2f} USDT\n"
            f"**Reference**: `{ref}`\n\n"
            f"Send USDT to one of these addresses:\n\n"
            f"**TRC20 (Recommended)**:\n"
            f"`{CRYPTO_WALLET['USDT_TRC20']}`\n\n"
            f"**BEP20**:\n"
            f"`{CRYPTO_WALLET['USDT_BEP20']}`\n\n"
            f"⚠️ **IMPORTANT**:\n"
            f"• Send EXACT amount\n"
            f"• Use correct network\n"
            f"• Include `{ref}` in memo if possible\n\n"
            f"_After sending, click 'I've Paid' and we'll verify within 30 minutes._"
        )
        
        keyboard = [
            [InlineKeyboardButton("✅ I've Paid", callback_data=f"pay_verify_{ref}")],
            [InlineKeyboardButton("🔙 Back to Plan Selection", callback_data=f"pay_plan_{plan}")]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return True
    
    # Bank Transfer
    if data.startswith("pay_method_bank_"):
        plan = data.replace("pay_method_bank_", "")
        prices = PLAN_PRICES.get(plan, {})
        
        ref = f"TSX-{secrets.token_hex(8).upper()}"
        
        db = init_db()
        try:
            user = db.get_user_by_telegram_id(user_id)
            db.create_payment(
                user_id=user.id if user else 0, 
                amount=prices.get('ngn', 0), 
                method="bank_transfer", 
                plan=plan, 
                ref=ref
            )
        finally:
            db.close()
        
        text = (
            f"🏦 **BANK TRANSFER**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"**Plan**: {plan.upper()}\n"
            f"**Amount**: ₦{prices.get('ngn', 0):,}\n"
            f"**Reference**: `{ref}`\n\n"
            f"Transfer to:\n\n"
            f"🏦 **Bank**: {BANK_DETAILS['bank_name']}\n"
            f"👤 **Account Name**: {BANK_DETAILS['account_name']}\n"
            f"🔢 **Account Number**: `{BANK_DETAILS['account_number']}`\n\n"
            f"⚠️ **IMPORTANT**:\n"
            f"• Use `{ref}` as transfer narration/reference\n"
            f"• Take a screenshot of your receipt\n\n"
            f"_After payment, click 'I've Paid' and send your receipt screenshot._"
        )
        
        keyboard = [
            [InlineKeyboardButton("✅ I've Paid", callback_data=f"pay_verify_{ref}")],
            [InlineKeyboardButton("🔙 Back to Plan Selection", callback_data=f"pay_plan_{plan}")]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return True
    
    # Telegram Stars Payment
    if data.startswith("pay_method_stars_"):
        plan = data.replace("pay_method_stars_", "")
        prices = PLAN_PRICES.get(plan, {})
        stars = prices.get('stars', 0)
        
        # Create invoice for Telegram Stars
        title = f"TradeSigx {plan.upper()} Plan"
        description = f"1 Month {plan.upper()} Subscription"
        payload = f"{user_id}_{plan}_{secrets.token_hex(4)}"
        currency = "XTR"  # Telegram Stars currency code
        price = [LabeledPrice(label=title, amount=stars)]
        
        try:
            await context.bot.send_invoice(
                chat_id=query.message.chat_id,
                title=title,
                description=description,
                payload=payload,
                provider_token="",  # Empty for Telegram Stars
                currency=currency,
                prices=price,
                start_parameter=f"upgrade_{plan}"
            )
            await query.edit_message_text(
                f"⭐ **TELEGRAM STARS PAYMENT**\n\n"
                f"A payment invoice for **{stars} Stars** has been sent above.\n"
                f"Complete the payment to activate your {plan.upper()} plan!",
                parse_mode="Markdown"
            )
        except Exception as e:
            logging.error(f"Stars invoice error: {e}")
            await query.edit_message_text(
                "❌ Unable to create Stars invoice. Please try another payment method.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data=f"pay_plan_{plan}")]])
            )
        return True
    
    # Payment Verification Request
    if data.startswith("pay_verify_"):
        ref = data.replace("pay_verify_", "")
        context.user_data['pending_payment_ref'] = ref
        
        await query.edit_message_text(
            f"✅ **PAYMENT VERIFICATION**\n\n"
            f"Reference: `{ref}`\n\n"
            f"Please send your payment proof (screenshot) or wait for automatic verification.\n\n"
            f"Our team will verify your payment within:\n"
            f"• **Crypto**: 30 minutes\n"
            f"• **Bank Transfer**: 1-2 hours\n"
            f"• **Paystack**: Instant\n\n"
            f"You'll receive a notification once verified!",
            parse_mode="Markdown"
        )
        return True
    
    # Upgrade Menu
    if data == "upgrade_menu":
        await show_upgrade_menu(update, context)
        return True
    
    return False

async def handle_successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle successful Telegram Stars payment"""
    payment = update.message.successful_payment
    payload = payment.invoice_payload
    
    try:
        parts = payload.split("_")
        user_id = parts[0]
        plan = parts[1]
        
        db = init_db()
        try:
            user = db.get_user_by_telegram_id(user_id)
            if user:
                user.subscription_plan = plan
                user.plan_expires_at = datetime.datetime.utcnow() + datetime.timedelta(days=30)
                db.commit()
                
                await update.message.reply_text(
                    f"🎉 **PAYMENT SUCCESSFUL!**\n\n"
                    f"Your **{plan.upper()}** plan is now active!\n"
                    f"Expires: {user.plan_expires_at.strftime('%Y-%m-%d')}\n\n"
                    f"Enjoy unlimited access to all TradeSigx features! 🚀",
                    parse_mode="Markdown"
                )
        finally:
            db.close()
    except Exception as e:
        logging.error(f"Payment processing error: {e}")

async def verify_payment_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manually verify a payment by reference"""
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /verify <payment_reference>")
        return
    
    ref = args[0].upper()
    
    db = init_db()
    try:
        payment = db.get_payment_by_ref(ref)
        if not payment:
            await update.message.reply_text("❌ Payment reference not found.")
            return
        
        if payment.status == "completed":
            await update.message.reply_text("✅ This payment has already been verified and activated.")
            return
        
        await update.message.reply_text(
            f"⏳ **Payment Pending Verification**\n\n"
            f"Reference: `{ref}`\n"
            f"Amount: ${payment.amount:.2f}\n"
            f"Method: {payment.payment_method}\n"
            f"Plan: {payment.plan_purchased.upper()}\n\n"
            f"Please wait for admin verification or contact support.",
            parse_mode="Markdown"
        )
    finally:
        db.close()

def activate_user_plan(user_id: str, plan: str, db) -> bool:
    """Activate a user's subscription plan"""
    user = db.get_user_by_telegram_id(user_id)
    if user:
        user.subscription_plan = plan
        user.plan_expires_at = datetime.datetime.utcnow() + datetime.timedelta(days=30)
        db.commit()
        return True
    return False
