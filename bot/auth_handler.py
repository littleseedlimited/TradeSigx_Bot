"""
Authentication & Signup Handler for TradeSigx Bot
Multi-step registration with Name, Email, Phone, Country
"""
import re
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes
from utils.db import init_db, User, SUPER_ADMIN_ID
import datetime

# Common country list
COUNTRIES = [
    "Nigeria", "United States", "United Kingdom", "India", "South Africa",
    "Ghana", "Kenya", "Egypt", "UAE", "Canada", "Australia", "Germany",
    "France", "Brazil", "Indonesia", "Philippines", "Pakistan", "Bangladesh",
    "Turkey", "Malaysia", "Singapore", "Japan", "China", "Russia", "Mexico"
]

# Validation patterns
EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
PHONE_PATTERN = re.compile(r'^\+?[1-9]\d{7,14}$')

def get_country_keyboard():
    """Generate country selection keyboard"""
    keyboard = []
    row = []
    for i, country in enumerate(COUNTRIES):
        row.append(InlineKeyboardButton(country, callback_data=f"signup_country_{country}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("🌍 Other", callback_data="signup_country_Other")])
    return InlineKeyboardMarkup(keyboard)

async def start_signup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Initiate signup flow"""
    user_id = str(update.effective_user.id)
    username = update.effective_user.username
    
    db = init_db()
    try:
        user = db.get_user_by_telegram_id(user_id)
        
        if not user:
            # Create new user entry
            user = User(
                telegram_id=user_id,
                username=username,
                registration_step="name"
            )
            db.add(user)
            db.commit()
        elif user.is_registered:
            await update.message.reply_text(
                "✅ You're already registered! Use the menu to access features.",
                reply_markup=ReplyKeyboardRemove()
            )
            return
        else:
            # Resume/Reset signup
            user.registration_step = "name"
            # Ensure we update username if they set one since last attempt
            if username and not user.username:
                user.username = username
            db.commit()
        
        # Check for missing username (Mandatory Requirement)
        if not user.username:
            user.registration_step = "set_username"
            db.commit()
            await update.message.reply_text(
                "🦁 **WELCOME TO TRADESIGX**\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                "I noticed you don't have a Telegram @username set.\n"
                "**Requirement**: Please type a unique username for your account below:",
                parse_mode="Markdown",
                reply_markup=ReplyKeyboardRemove()
            )
            return

        await update.message.reply_text(
            "🦁 **WELCOME TO TRADESIGX**\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Let's get you set up! This takes less than a minute.\n\n"
            "**Step 1 of 6**: What's your full name?",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove()
        )
    finally:
        db.close()

async def handle_signup_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Process signup flow messages. Returns True if handled."""
    user_id = str(update.effective_user.id)
    text = update.message.text.strip()
    
    db = init_db()
    try:
        user = db.get_user_by_telegram_id(user_id)
        
        if not user or user.is_registered:
            return False
        
        step = user.registration_step
        
        # Step 1: Name
        # Step 0: Set Username (if missing from Telegram)
        if step == "set_username":
            if len(text) < 3 or len(text) > 30:
                await update.message.reply_text("❌ Username must be 3-30 characters.")
                return True
            
            # Simple check for unique username in DB
            existing = db.session.query(User).filter(User.username == text).first()
            if existing:
                await update.message.reply_text("❌ This username is already taken. Please try another.")
                return True
                
            user.username = text
            user.registration_step = "name"
            db.commit()
            await update.message.reply_text(
                f"✅ Username set to **{text}**!\n\n"
                "**Step 1 of 6**: What's your full name?",
                parse_mode="Markdown"
            )
            return True

        # Step 1: Name
        if step == "name":
            if len(text) < 2 or len(text) > 100:
                await update.message.reply_text("❌ Please enter a valid name (2-100 characters).")
                return True
            
            user.full_name = text
            user.registration_step = "email"
            db.commit()
            
            await update.message.reply_text(
                f"Great, **{text}**! 👋\n\n"
                "**Step 2 of 6**: What's your email address?\n\n"
                "⚠️ **This is mandatory** for account recovery and pro features.",
                parse_mode="Markdown"
            )
            return True
        
        # Step 2: Email
        elif step == "email":
            if not EMAIL_PATTERN.match(text):
                await update.message.reply_text("❌ Please enter a valid email address (e.g., user@example.com).")
                return True
            
            # Check if email already exists
            existing = db.session.query(User).filter(User.email == text.lower()).first()
            if existing and existing.telegram_id != user_id:
                await update.message.reply_text("❌ This email is already registered to another account.")
                return True
            
            user.email = text.lower()
            user.registration_step = "phone"
            db.commit()
            
            await update.message.reply_text(
                "✅ Email saved!\n\n"
                "**Step 3 of 6**: What's your phone number?\n\n"
                "⚠️ **This is mandatory** for SMS alerts and account verification.\n"
                "Include country code (e.g., +234XXXXXXXXXX or +1XXXXXXXXXX)",
                parse_mode="Markdown"
            )
            return True
        
        # Step 3: Phone
        elif step == "phone":
            # Clean phone number
            phone = text.replace(" ", "").replace("-", "")
            if not phone.startswith("+"):
                phone = "+" + phone
            
            if not PHONE_PATTERN.match(phone):
                await update.message.reply_text(
                    "❌ Please enter a valid phone number with country code.\n"
                    "Example: +2348012345678 or +14155551234"
                )
                return True
            
            user.phone = phone
            user.registration_step = "country"
            db.commit()
            
            await update.message.reply_text(
                "✅ Phone saved!\n\n"
                "**Step 4 of 6**: Select your country:\n\n"
                "⚠️ **This is mandatory** to provide relevant market signals for your region.",
                reply_markup=get_country_keyboard(),
                parse_mode="Markdown"
            )
            return True
        
        # Step 5: Terms (handled via callback)
        elif step == "terms":
            # In case they type instead of clicking
            await update.message.reply_text(
                "Please click one of the buttons above to accept or decline the terms.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ I Accept", callback_data="signup_terms_accept")],
                    [InlineKeyboardButton("❌ Decline", callback_data="signup_terms_decline")]
                ])
            )
            return True
        
        # Step: Other Country
        elif step == "country_other":
            if len(text) < 2 or len(text) > 50:
                await update.message.reply_text("❌ Please enter a valid country name.")
                return True
            
            user.country = text
            user.registration_step = "terms"
            db.commit()
            
            await show_terms(update, context)
            return True
        
        return False
    finally:
        db.close()

async def handle_signup_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Handle signup-related callbacks. Returns True if handled."""
    query = update.callback_query
    data = query.data
    
    if not data.startswith("signup_"):
        return False
    
    await query.answer()
    user_id = str(update.effective_user.id)
    
    db = init_db()
    try:
        user = db.get_user_by_telegram_id(user_id)
        if not user:
            return False
        
        # Country Selection
        if data.startswith("signup_country_"):
            country = data.replace("signup_country_", "")
            
            if country == "Other":
                user.registration_step = "country_other"
                db.commit()
                await query.edit_message_text(
                    "🌍 Please type your country name:",
                    parse_mode="Markdown"
                )
            else:
                user.country = country
                user.registration_step = "terms"
                db.commit()
                
                await query.edit_message_text(
                    f"✅ Country set to **{country}**!\n\n"
                    "**Step 5 of 6**: Please review our Terms of Service:",
                    parse_mode="Markdown"
                )
                await show_terms_inline(query.message, context)
            return True
        
        # Terms Acceptance
        elif data == "signup_terms_accept":
            user.terms_accepted = True
            user.is_registered = True
            user.registration_step = "complete"
            # FREE Plan expires after 30 days
            user.plan_expires_at = datetime.datetime.utcnow() + datetime.timedelta(days=30)
            db.commit()
            
            # Clear access cache to reflect registered status in handlers
            if 'is_registered_cached' in context.user_data:
                del context.user_data['is_registered_cached']
            
            await query.edit_message_text(
                "🎉 **REGISTRATION COMPLETE!**\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                f"Welcome to TradeSigx, **{user.full_name}**!\n\n"
                "You're now on the **FREE** plan with 3 signals per day.\n\n"
                "🛡 **FINAL STEP**: Please verify your identity (KYC) to unlock full withdrawal capabilities and priority analysis.\n\n"
                "🚀 **Quick Start**:\n"
                "• Use /menu to access all features\n"
                "• Use /upgrade to unlock unlimited signals\n"
                "• Click the button below to start KYC\n\n"
                "Happy trading! 📈",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🛡 Start KYC Verification", callback_data="cmd_kyc")],
                    [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_main")]
                ])
            )
            return True
        
        elif data == "signup_terms_decline":
            await query.edit_message_text(
                "❌ You must accept the Terms of Service to use TradeSigx.\n\n"
                "Use /signup when you're ready to continue.",
                parse_mode="Markdown"
            )
            return True
        
        return False
    finally:
        db.close()

async def show_terms(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show terms of service"""
    await update.message.reply_text(
        "📜 **TERMS OF SERVICE**\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "By using TradeSigx, you agree to:\n\n"
        "1. Trading signals are for educational purposes only\n"
        "2. Past performance does not guarantee future results\n"
        "3. You trade at your own risk\n"
        "4. No refunds on subscription payments\n"
        "5. Your data is protected under our Privacy Policy\n\n"
        "Do you accept these terms?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ I Accept", callback_data="signup_terms_accept")],
            [InlineKeyboardButton("❌ Decline", callback_data="signup_terms_decline")]
        ]),
        parse_mode="Markdown"
    )

async def show_terms_inline(message, context: ContextTypes.DEFAULT_TYPE):
    """Show terms via message object"""
    await message.reply_text(
        "📜 **TERMS OF SERVICE**\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "By using TradeSigx, you agree to:\n\n"
        "1. Trading signals are for educational purposes only\n"
        "2. Past performance does not guarantee future results\n"
        "3. You trade at your own risk\n"
        "4. No refunds on subscription payments\n"
        "5. Your data is protected under our Privacy Policy\n\n"
        "Do you accept these terms?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ I Accept", callback_data="signup_terms_accept")],
            [InlineKeyboardButton("❌ Decline", callback_data="signup_terms_decline")]
        ]),
        parse_mode="Markdown"
    )

def check_user_access(user) -> tuple:
    """
    Check if user can access features.
    Returns (can_access: bool, message: str)
    """
    # SUPER ADMIN: Universal bypass
    if user and str(user.telegram_id) == SUPER_ADMIN_ID:
        return True, ""
        
    if not user:
        return False, "Please /signup first to use TradeSigx."
    
    if not user.is_registered:
        return False, "Please complete your registration with /signup."
    
    # Strict Enforcement of Mandatory Fields
    if not user.email or not user.phone or not user.country:
        user.is_registered = False # Force re-signup if data is missing
        return False, "⚠️ **Profile Incomplete**: We noticed some mandatory fields (Email, Phone, or Country) are missing. Please use /signup to update your profile."

    if user.is_banned:
        return False, f"Your account has been suspended. Reason: {user.ban_reason or 'Contact support.'}"
    
    return True, ""

def check_signal_limit(user) -> tuple:
    """
    Check if user can generate more signals today.
    Returns (can_generate: bool, message: str)
    """
    # SUPER ADMIN bypass: Unlimited signals, no expiry
    if user and str(user.telegram_id) == SUPER_ADMIN_ID:
        return True, ""

    today = datetime.datetime.utcnow().strftime("%Y-%m-%d")
    
    # Reset daily counter
    if user.last_signal_date != today:
        user.signals_used_today = 0
        user.last_signal_date = today
    
    # Get plan limits
    plan = user.subscription_plan
    limits = {"free": 3, "basic": 15, "pro": -1, "vip": -1}
    limit = limits.get(plan, 3)
    
    # Check expiry
    if user.plan_expires_at and user.plan_expires_at < datetime.datetime.utcnow():
        if plan == "free":
            return False, (
                "⚠️ **Trial Expired**\n\n"
                "Your 1-month Free trial has ended. "
                "To continue receiving high-quality signals, please upgrade to a paid plan.\n\n"
                "Use /upgrade to see active plans."
            )
        else:
            # Downgrade paid plan to free (but free will still be checked above if it also expired eventually)
            user.subscription_plan = "free"
            limit = 3
    
    if limit == -1:
        return True, ""
    
    if user.signals_used_today >= limit:
        return False, (
            f"⚠️ **Daily Limit Reached**\n\n"
            f"You've used all {limit} signals for today on the **{plan.upper()}** plan.\n\n"
            f"🚀 Upgrade to **PRO** for unlimited signals!\n"
            f"Use /upgrade to see plans."
        )
    
    return True, ""

def increment_signal_usage(user, db):
    """Increment the user's daily signal count (Admin bypass)"""
    # SUPER ADMIN bypass: Never increment usage
    if user and str(user.telegram_id) == SUPER_ADMIN_ID:
        return

    today = datetime.datetime.utcnow().strftime("%Y-%m-%d")
    if user.last_signal_date != today:
        user.signals_used_today = 0
        user.last_signal_date = today
    user.signals_used_today += 1
    db.commit()
