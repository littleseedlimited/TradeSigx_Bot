"""
KYC Handler for TradeSigx Bot
Document upload and verification workflow
"""
import logging
import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from utils.db import init_db

async def start_kyc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start KYC verification process"""
    user_id = str(update.effective_user.id)
    
    db = init_db()
    try:
        user = db.get_user_by_telegram_id(user_id)
        
        if not user or not user.is_registered:
            await update.message.reply_text("❌ Please complete registration first with /signup")
            return
        
        if user.kyc_status == "approved":
            await update.message.reply_text(
                "✅ **KYC Already Verified**\n\n"
                "Your identity has been verified. You have full access to all features!",
                parse_mode="Markdown"
            )
            return
        
        if user.kyc_status == "pending":
            await update.message.reply_text(
                "⏳ **KYC Under Review**\n\n"
                "Your documents are being reviewed. You'll be notified once approved.\n"
                "This usually takes 1-24 hours.",
                parse_mode="Markdown"
            )
            return
        
        # Start or restart KYC
        context.user_data['kyc_step'] = 'id_document'
        
        rejection_msg = ""
        if user.kyc_status == "rejected":
            rejection_msg = f"\n\n⚠️ Previous rejection reason: {user.kyc_rejection_reason or 'Not specified'}\n"
        
        await update.message.reply_text(
            f"🔐 **IDENTITY VERIFICATION (KYC)**\n"
            f"━━━━━━━━━━━━━━━━━━━━{rejection_msg}\n\n"
            f"To unlock full features, we need to verify your identity.\n\n"
            f"**Step 1 of 2**: Please send a clear photo of your **Government-issued ID**\n\n"
            f"Accepted documents:\n"
            f"• Passport\n"
            f"• Driver's License\n"
            f"• National ID Card\n\n"
            f"📸 _Send the photo now..._",
            parse_mode="Markdown"
        )
    finally:
        db.close()

async def handle_kyc_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Handle KYC document photo uploads. Returns True if handled."""
    user_id = str(update.effective_user.id)
    
    kyc_step = context.user_data.get('kyc_step')
    if not kyc_step:
        return False
    
    if not update.message.photo:
        await update.message.reply_text("❌ Please send a photo, not a file or text.")
        return True
    
    # Get the largest photo
    photo = update.message.photo[-1]
    file_id = photo.file_id
    
    db = init_db()
    try:
        user = db.get_user_by_telegram_id(user_id)
        if not user:
            return False
        
        if kyc_step == 'id_document':
            user.kyc_id_document = file_id
            db.commit()
            
            context.user_data['kyc_step'] = 'selfie'
            
            await update.message.reply_text(
                "✅ ID Document received!\n\n"
                "**Step 2 of 2**: Please send a **selfie holding your ID**\n\n"
                "Requirements:\n"
                "• Your face must be clearly visible\n"
                "• Hold your ID next to your face\n"
                "• The ID details should be readable\n\n"
                "📸 _Send the selfie now..._",
                parse_mode="Markdown"
            )
            return True
        
        elif kyc_step == 'selfie':
            user.kyc_selfie = file_id
            user.kyc_status = "pending"
            user.kyc_submitted_at = datetime.datetime.utcnow()
            db.commit()
            
            context.user_data.pop('kyc_step', None)
            
            await update.message.reply_text(
                "✅ **KYC SUBMITTED SUCCESSFULLY**\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                "Your documents have been submitted for review!\n\n"
                "⏱ **Estimated review time**: 1-24 hours\n\n"
                "You'll receive a notification once your verification is complete.\n\n"
                "Thank you for your patience! 🙏",
                parse_mode="Markdown"
            )
            
            # Notify admins
            from utils.db import SUPER_ADMIN_ID
            try:
                await context.bot.send_message(
                    SUPER_ADMIN_ID,
                    f"📋 **NEW KYC SUBMISSION**\n\n"
                    f"User: {user.full_name or user.username}\n"
                    f"ID: `{user.telegram_id}`\n"
                    f"Email: {user.email}\n\n"
                    f"Use /admin to review.",
                    parse_mode="Markdown"
                )
            except: pass
            
            return True
    finally:
        db.close()
    
    return False

async def cancel_kyc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel ongoing KYC process"""
    context.user_data.pop('kyc_step', None)
    await update.message.reply_text(
        "❌ KYC process cancelled. Use /kyc to start again.",
        parse_mode="Markdown"
    )

async def kyc_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check KYC status"""
    user_id = str(update.effective_user.id)
    
    db = init_db()
    try:
        user = db.get_user_by_telegram_id(user_id)
        
        if not user:
            await update.message.reply_text("❌ Please register first with /signup")
            return
        
        status_emoji = {
            "not_submitted": "⚪",
            "pending": "🟡",
            "approved": "🟢",
            "rejected": "🔴"
        }
        
        status_text = {
            "not_submitted": "Not Submitted",
            "pending": "Under Review",
            "approved": "Verified ✅",
            "rejected": "Rejected"
        }
        
        emoji = status_emoji.get(user.kyc_status, "⚪")
        status = status_text.get(user.kyc_status, "Unknown")
        
        text = (
            f"🔐 **KYC STATUS**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{emoji} Status: **{status}**\n"
        )
        
        if user.kyc_submitted_at:
            text += f"📅 Submitted: {user.kyc_submitted_at.strftime('%Y-%m-%d %H:%M')}\n"
        
        if user.kyc_reviewed_at:
            text += f"📅 Reviewed: {user.kyc_reviewed_at.strftime('%Y-%m-%d %H:%M')}\n"
        
        if user.kyc_status == "rejected" and user.kyc_rejection_reason:
            text += f"\n❌ Rejection Reason: {user.kyc_rejection_reason}\n"
        
        keyboard = []
        if user.kyc_status in ["not_submitted", "rejected"]:
            keyboard.append([InlineKeyboardButton("📤 Submit KYC", callback_data="start_kyc")])
        
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None,
            parse_mode="Markdown"
        )
    finally:
        db.close()

async def handle_kyc_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Handle KYC-related callbacks"""
    query = update.callback_query
    
    if query.data == "start_kyc":
        await query.answer()
        context.user_data['kyc_step'] = 'id_document'
        
        await query.edit_message_text(
            "🔐 **IDENTITY VERIFICATION (KYC)**\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "**Step 1 of 2**: Please send a clear photo of your **Government-issued ID**\n\n"
            "Accepted documents:\n"
            "• Passport\n"
            "• Driver's License\n"
            "• National ID Card\n\n"
            "📸 _Send the photo now..._",
            parse_mode="Markdown"
        )
        return True
    
    return False
