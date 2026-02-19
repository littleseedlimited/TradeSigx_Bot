"""
Super Admin Handler for TradeSigx Bot
Full CRUD, User Management, KYC Review, Plan Upgrades
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ContextTypes
from utils.db import init_db, User, SUPER_ADMIN_ID
from config import Config
import datetime

def is_super_admin(user_id: str) -> bool:
    """Check if user is the Super Admin"""
    return str(user_id) == SUPER_ADMIN_ID

def is_admin(user_id: str) -> bool:
    """Check if user is any admin"""
    if is_super_admin(user_id):
        return True
    db = init_db()
    try:
        user = db.get_user_by_telegram_id(str(user_id))
        return user and user.is_admin
    finally:
        db.close()

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main admin command handler"""
    user_id = str(update.effective_user.id)
    
    if not is_admin(user_id):
        await update.message.reply_text("⛔ Access Denied. Admin privileges required.")
        return
    
    keyboard = [
        [InlineKeyboardButton("👥 View User Grid (Monospace)", callback_data="admin_users_1")],
        [InlineKeyboardButton("📊 System Stats", callback_data="admin_stats")],
        [InlineKeyboardButton("✅ Verify User", callback_data="admin_kyc_pending")],
        [InlineKeyboardButton("🔍 Search User Intelligence", callback_data="admin_search")],
        [InlineKeyboardButton("📢 Broadcast Announcement", callback_data="admin_broadcast")],
        [InlineKeyboardButton("⬅️ Close Console", callback_data="back_to_main")],
    ]
    
    await update.message.reply_text(
        "🛡️ **SUPER ADMIN CONSOLE**\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Choose an action:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def admin_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all admin callback queries"""
    query = update.callback_query
    data = query.data
    
    # ONLY handle admin prefixed data
    if not data.startswith("admin_"):
        return False

    await query.answer()
    user_id = str(update.effective_user.id)
    
    if not is_admin(user_id):
        await query.edit_message_text("⛔ Access Denied.")
        return True # Handled (but denied)
    
    # User List with Pagination
    if data.startswith("admin_users_"):
        page = int(data.split("_")[2])
        db = init_db()
        try:
            users = db.get_users_paginated(page=page, per_page=10)
            total = db.get_user_count()
            total_pages = (total + 9) // 10
            
            if not users:
                await query.edit_message_text("No users found.")
                return
            
            text = (
                "👥 **SUPER ADMIN USER GRID**\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "`┃ STATUS ┃ TELEGRAM ID ┃ PLAN ┃` \n"
                "━━━━━━━━━━━━━━━━━━━━\n"
            )
            for u in users:
                kyc = "✅" if u.kyc_status == "approved" else ("⌛" if u.kyc_status == "pending" else "⚪")
                ban = "🚫" if u.is_banned else " "
                status = f"{kyc}{ban}"
                plan = u.subscription_plan[:3].upper()
                text += f"`┃ {status:<6} ┃ {u.telegram_id:<11} ┃ {plan:<4} ┃` [View](https://t.me/share/url?url=/admin_view_{u.telegram_id})\n"
            
            nav_buttons = []
            if page > 1:
                nav_buttons.append(InlineKeyboardButton("◀️ Prev", callback_data=f"admin_users_{page-1}"))
            if page < total_pages:
                nav_buttons.append(InlineKeyboardButton("Next ▶️", callback_data=f"admin_users_{page+1}"))
            
            # Create a matrix of View Profile buttons for the current page
            user_buttons = []
            for u in users:
                short_name = (u.username or u.full_name or str(u.telegram_id))[:10]
                user_buttons.append(InlineKeyboardButton(f"👤 {short_name}", callback_data=f"admin_view_{u.telegram_id}"))
            
            # Split user buttons into groups of 2 for the keyboard
            keyboard = [user_buttons[i:i + 2] for i in range(0, len(user_buttons), 2)]
            
            if nav_buttons:
                keyboard.append(nav_buttons)
            keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="admin_back")])
            
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        finally:
            db.close()
        return True
    
    # Stats Dashboard
    elif data == "admin_stats":
        db = init_db()
        try:
            total_users = db.get_user_count()
            registered = db.session.query(User).filter(User.is_registered == True).count()
            free_users = db.session.query(User).filter(User.subscription_plan == "free").count()
            basic_users = db.session.query(User).filter(User.subscription_plan == "basic").count()
            pro_users = db.session.query(User).filter(User.subscription_plan == "pro").count()
            vip_users = db.session.query(User).filter(User.subscription_plan == "vip").count()
            pending_kyc = db.session.query(User).filter(User.kyc_status == "pending").count()
            
            text = (
                "📊 **PLATFORM STATISTICS**\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                f"👥 **Total Users**: {total_users}\n"
                f"✅ **Registered**: {registered}\n\n"
                f"📦 **Plan Distribution**:\n"
                f"   🆓 Free: {free_users}\n"
                f"   💎 Basic: {basic_users}\n"
                f"   ⭐ Pro: {pro_users}\n"
                f"   👑 VIP: {vip_users}\n\n"
                f"📋 **Pending KYC**: {pending_kyc}\n"
            )
            
            keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="admin_back")]]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        finally:
            db.close()
        return True
    
    # Pending KYC
    elif data == "admin_kyc_pending":
        db = init_db()
        try:
            pending = db.get_pending_kyc()
            
            if not pending:
                text = "✅ No pending KYC submissions."
            else:
                text = "📋 **PENDING KYC REVIEWS**\n━━━━━━━━━━━━━━━━━━━━\n\n"
                for u in pending:
                    text += f"• `{u.telegram_id}` - {u.full_name or 'N/A'}\n"
            
            keyboard = []
            for u in pending[:5]:  # Show first 5
                keyboard.append([InlineKeyboardButton(f"Review {u.telegram_id}", callback_data=f"admin_kyc_review_{u.telegram_id}")])
            keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="admin_back")])
            
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        finally:
            db.close()
        return True
    
    # KYC Review
    elif data.startswith("admin_kyc_review_"):
        target_id = data.split("_")[3]
        db = init_db()
        try:
            user = db.get_user_by_telegram_id(target_id)
            if not user:
                await query.edit_message_text("User not found.")
                return
            
            text = (
                f"📋 **KYC REVIEW**\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"**User**: {user.full_name or 'N/A'}\n"
                f"**Telegram ID**: `{user.telegram_id}`\n"
                f"**Email**: {user.email or 'N/A'}\n"
                f"**Phone**: {user.phone or 'N/A'}\n"
                f"**Country**: {user.country or 'N/A'}\n"
                f"**Submitted**: {user.kyc_submitted_at or 'N/A'}\n\n"
                f"📄 Documents will be sent separately."
            )
            
            keyboard = [
                [InlineKeyboardButton("✅ Approve", callback_data=f"admin_kyc_approve_{target_id}"),
                 InlineKeyboardButton("❌ Reject", callback_data=f"admin_kyc_reject_{target_id}")],
                [InlineKeyboardButton("🔙 Back", callback_data="admin_kyc_pending")]
            ]
            
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
            
            # Send document files if available
            if user.kyc_id_document:
                try:
                    await context.bot.send_photo(query.message.chat_id, user.kyc_id_document, caption="📄 ID Document")
                except: pass
            if user.kyc_selfie:
                try:
                    await context.bot.send_photo(query.message.chat_id, user.kyc_selfie, caption="🤳 Selfie with ID")
                except: pass
        finally:
            db.close()
        return True
    
    # KYC Approve
    elif data.startswith("admin_kyc_approve_"):
        target_id = data.split("_")[3]
        db = init_db()
        try:
            user = db.get_user_by_telegram_id(target_id)
            if user:
                user.kyc_status = "approved"
                user.kyc_reviewed_at = datetime.datetime.utcnow()
                db.commit()
                
                # Notify user
                try:
                    await context.bot.send_message(
                        target_id,
                        "✅ **KYC APPROVED**\n\nYour identity verification has been approved! You now have full access to all features.",
                        parse_mode="Markdown"
                    )
                except: pass
                
                await query.edit_message_text(f"✅ KYC approved for user `{target_id}`.", parse_mode="Markdown")
        finally:
            db.close()
        return True
    
    # KYC Reject
    elif data.startswith("admin_kyc_reject_"):
        target_id = data.split("_")[3]
        context.user_data['kyc_reject_target'] = target_id
        await query.edit_message_text(
            f"❌ **Rejecting KYC for `{target_id}`**\n\nPlease reply with the rejection reason:",
            parse_mode="Markdown"
        )
        return True
    
    # User Detail View (Intelligence Mode)
    elif data.startswith("admin_view_"):
        target_id = data.split("_")[2]
        db = init_db()
        try:
            user = db.get_user_by_telegram_id(target_id)
            if not user:
                await query.edit_message_text("User not found.")
                return
            
            # Show ALL fields as requested
            text = (
                f"🧠 **USER INTELLIGENCE REPORT**\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"👤 **Core Profile**\n"
                f"┣ ID: `{user.telegram_id}`\n"
                f"┣ DB_ID: `{user.id}`\n"
                f"┣ Name: `{user.full_name or 'N/A'}`\n"
                f"┣ User: @{user.username or 'N/A'}\n"
                f"┣ Email: `{user.email or 'N/A'}`\n"
                f"┣ Phone: `{user.phone or 'N/A'}`\n"
                f"┣ Country: `{user.country or 'N/A'}`\n"
                f"┗ Joined: `{user.joined_at}`\n\n"
                
                f"💎 **Subscription & Access**\n"
                f"┣ Plan: `{user.subscription_plan.upper()}`\n"
                f"┣ Expires: `{user.plan_expires_at or 'NEVER'}`\n"
                f"┣ KYC: `{user.kyc_status.upper()}`\n"
                f"┣ Registered: `{'YES' if user.is_registered else 'NO'}`\n"
                f"┣ Admin: `{'YES' if user.is_admin else 'NO'}`\n"
                f"┗ Banned: `{'YES' if user.is_banned else 'NO'}`\n\n"
                
                f"💰 **Financials & Usage**\n"
                f"┣ Balance: `${user.wallet_balance:.2f}`\n"
                f"┣ Lot: `{user.default_lot}` | Risk: `{user.risk_per_trade}%` \n"
                f"┗ Signals Today: `{user.signals_used_today}`\n"
            )
            
            keyboard = [
                [InlineKeyboardButton("⬆️ Upgrade Plan", callback_data=f"admin_upgrade_{target_id}"),
                 InlineKeyboardButton("💰 Add Balance", callback_data=f"admin_addbal_{target_id}")],
                [InlineKeyboardButton("⭐ Promote Admin" if not user.is_admin else "🎖️ Demote Admin", 
                                      callback_data=f"admin_promote_{target_id}" if not user.is_admin else f"admin_demote_{target_id}")],
                [InlineKeyboardButton("🚫 Ban User" if not user.is_banned else "✅ Unban User", 
                                      callback_data=f"admin_ban_{target_id}" if not user.is_banned else f"admin_unban_{target_id}"),
                 InlineKeyboardButton("🔄 Reset Signals", callback_data=f"admin_reset_{target_id}")],
                [InlineKeyboardButton("🗑️ DELETE ACCOUNT", callback_data=f"admin_del_conf_{target_id}")],
                [InlineKeyboardButton("🔙 Back to Grid", callback_data="admin_users_1")]
            ]
            
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        finally:
            db.close()
        return True
    
    # Upgrade Plan
    elif data.startswith("admin_upgrade_"):
        target_id = data.split("_")[2]
        keyboard = [
            [InlineKeyboardButton("🆓 Free", callback_data=f"admin_setplan_{target_id}_free"),
             InlineKeyboardButton("💎 Basic", callback_data=f"admin_setplan_{target_id}_basic")],
            [InlineKeyboardButton("⭐ Pro", callback_data=f"admin_setplan_{target_id}_pro"),
             InlineKeyboardButton("👑 VIP", callback_data=f"admin_setplan_{target_id}_vip")],
            [InlineKeyboardButton("🔙 Back", callback_data=f"admin_view_{target_id}")]
        ]
        await query.edit_message_text(f"Select new plan for `{target_id}`:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return True
    
    # Set Plan
    elif data.startswith("admin_setplan_"):
        parts = data.split("_")
        target_id = parts[2]
        new_plan = parts[3]
        
        db = init_db()
        try:
            user = db.get_user_by_telegram_id(target_id)
            if user:
                user.subscription_plan = new_plan
                if new_plan != "free":
                    user.plan_expires_at = datetime.datetime.utcnow() + datetime.timedelta(days=30)
                else:
                    user.plan_expires_at = None
                db.commit()
                
                # Notify user
                try:
                    await context.bot.send_message(
                        target_id,
                        f"🎉 **PLAN UPGRADED**\n\nYour subscription has been upgraded to **{new_plan.upper()}** by an administrator!",
                        parse_mode="Markdown"
                    )
                except: pass
                
                await query.edit_message_text(f"✅ Plan updated to **{new_plan.upper()}** for `{target_id}`.", parse_mode="Markdown")
        finally:
            db.close()
        return True
    
    # Promote User to Admin
    elif data.startswith("admin_promote_"):
        target_id = data.split("_")[2]
        db = init_db()
        try:
            user = db.get_user_by_telegram_id(target_id)
            if user:
                user.is_admin = True
                db.commit()
                await query.edit_message_text(f"⭐ User `{target_id}` has been **PROMOTED** to Admin.", parse_mode="Markdown")
        finally:
            db.close()
        return True

    # Demote Admin to User
    elif data.startswith("admin_demote_"):
        target_id = data.split("_")[2]
        db = init_db()
        try:
            user = db.get_user_by_telegram_id(target_id)
            if user:
                user.is_admin = False
                db.commit()
                await query.edit_message_text(f"🎖️ User `{target_id}` has been **DEMOTED** to User.", parse_mode="Markdown")
        finally:
            db.close()
        return True

    # Delete Confirmation
    elif data.startswith("admin_del_conf_"):
        target_id = data.split("_")[3]
        keyboard = [
            [InlineKeyboardButton("🔥 YES, DELETE NOW", callback_data=f"admin_delete_{target_id}")],
            [InlineKeyboardButton("🔙 Cancel", callback_data=f"admin_view_{target_id}")]
        ]
        await query.edit_message_text(
            f"⚠️ **CRITICAL WARNING**\n\nYou are about to **PERMANENTLY DELETE** user `{target_id}` and all their associated data (Settings, Balance, Plans).\n\n**This action CANNOT be undone.** Continue?",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return True

    # Actual Delete Execution
    elif data.startswith("admin_delete_"):
        target_id = data.split("_")[2]
        from utils.db import TradeExecution, BrokerAccount
        db = init_db()
        try:
            user = db.get_user_by_telegram_id(target_id)
            if user:
                # Manual cascade for SQLite consistency as seen in server.py
                db.session.query(TradeExecution).filter(TradeExecution.user_id == target_id).delete()
                db.session.query(BrokerAccount).filter(BrokerAccount.user_id == user.id).delete()
                db.session.delete(user)
                db.commit()
                await query.edit_message_text(f"🗑️ User `{target_id}` has been **PERMANENTLY DELETED**.", parse_mode="Markdown")
        finally:
            db.close()
        return True

    # Add Balance Preparation (Native Request)
    elif data.startswith("admin_addbal_"):
        target_id = data.split("_")[2]
        context.user_data['admin_bal_target'] = target_id
        await query.edit_message_text(
            f"💰 **Balance Adjustment for `{target_id}`**\n\nReply with the amount to ADD or SUBTRACT.\n\nExamples:\n`100` (Add $100)\n`-50` (Subtract $50)",
            parse_mode="Markdown"
        )
        return True

    # Manual Signal Reset
    elif data.startswith("admin_reset_"):
        target_id = data.split("_")[2]
        db = init_db()
        try:
            user = db.get_user_by_telegram_id(target_id)
            if user:
                user.signals_used_today = 0
                db.commit()
                await query.edit_message_text(f"🔄 Daily signal count has been **RESET** for `{target_id}`.", parse_mode="Markdown")
        finally:
            db.close()
        return True

    # Ban User
    elif data.startswith("admin_ban_"):
        target_id = data.split("_")[2]
        db = init_db()
        try:
            user = db.get_user_by_telegram_id(target_id)
            if user:
                user.is_banned = True
                db.commit()
                await query.edit_message_text(f"🚫 User `{target_id}` has been **BANNED**.", parse_mode="Markdown")
        finally:
            db.close()
        return True
    
    # Unban User
    elif data.startswith("admin_unban_"):
        target_id = data.split("_")[2]
        db = init_db()
        try:
            user = db.get_user_by_telegram_id(target_id)
            if user:
                user.is_banned = False
                user.ban_reason = None
                db.commit()
                await query.edit_message_text(f"✅ User `{target_id}` has been **UNBANNED**.", parse_mode="Markdown")
        finally:
            db.close()
        return True
    
    # Search User
    elif data == "admin_search":
        context.user_data['admin_search_mode'] = True
        await query.edit_message_text(
            "🔍 **SEARCH USER**\n\nReply with a Telegram ID, username, or email to search:",
            parse_mode="Markdown"
        )
        return True
    
    # Broadcast
    elif data == "admin_broadcast":
        context.user_data['admin_broadcast_mode'] = True
        await query.edit_message_text(
            "📢 **BROADCAST MESSAGE**\n\nReply with the message you want to send to ALL users:",
            parse_mode="Markdown"
        )
        return True
    
    # Back to Admin Menu
    elif data == "admin_back":
        await query.edit_message_text(
            "🛡️ **SUPER ADMIN CONSOLE**\n━━━━━━━━━━━━━━━━━━━━\nChoose an action:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("👥 View User Grid (Monospace)", callback_data="admin_users_1")],
                [InlineKeyboardButton("📊 System Stats", callback_data="admin_stats")],
                [InlineKeyboardButton("✅ Verify User", callback_data="admin_kyc_pending")],
                [InlineKeyboardButton("🔍 Search User Intelligence", callback_data="admin_search")],
                [InlineKeyboardButton("📢 Broadcast Announcement", callback_data="admin_broadcast")],
                [InlineKeyboardButton("⬅️ Close Console", callback_data="back_to_main")],
            ]),
            parse_mode="Markdown"
        )
        return True
    
    return False

async def admin_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin text inputs for search, broadcast, KYC rejection"""
    user_id = str(update.effective_user.id)
    text = update.message.text or ""
    
    if not is_admin(user_id):
        return False

    # IGNORE commands or menu buttons - let main handler take over
    menu_buttons = ["📈 Generate Signal", "⚡ Quick Analysis", "💼 Wallet", "🔌 Brokers", "⚙️ Settings", "📖 Help", "ℹ️ About"]
    if text.startswith("/") or text in menu_buttons:
        # Clear modes if they try to navigate away
        context.user_data['admin_search_mode'] = False
        context.user_data['admin_broadcast_mode'] = False
        return False
    
    # Search Mode
    if context.user_data.get('admin_search_mode'):
        context.user_data['admin_search_mode'] = False
        search_term = update.message.text.strip()
        
        db = init_db()
        try:
            # Search by telegram_id, username, or email
            user = db.session.query(User).filter(
                (User.telegram_id == search_term) | 
                (User.username == search_term) | 
                (User.email == search_term)
            ).first()
            
            if user:
                keyboard = [[InlineKeyboardButton("View Profile", callback_data=f"admin_view_{user.telegram_id}")]]
                await update.message.reply_text(
                    f"✅ Found: `{user.telegram_id}` - {user.full_name or user.username or 'N/A'}",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode="Markdown"
                )
            else:
                await update.message.reply_text("❌ No user found with that identifier.")
        finally:
            db.close()
        return True
    
    # Broadcast Mode
    if context.user_data.get('admin_broadcast_mode'):
        context.user_data['admin_broadcast_mode'] = False
        message = update.message.text
        
        db = init_db()
        try:
            users = db.get_all_users()
            success = 0
            failed = 0
            
            for user in users:
                try:
                    await context.bot.send_message(
                        user.telegram_id,
                        f"📢 **ANNOUNCEMENT**\n\n{message}",
                        parse_mode="Markdown"
                    )
                    success += 1
                except:
                    failed += 1
            
            await update.message.reply_text(f"📢 Broadcast complete!\n✅ Sent: {success}\n❌ Failed: {failed}")
        finally:
            db.close()
        return True
    
    # KYC Rejection Reason
    if context.user_data.get('kyc_reject_target'):
        target_id = context.user_data.pop('kyc_reject_target')
        reason = update.message.text
        
        db = init_db()
        try:
            user = db.get_user_by_telegram_id(target_id)
            if user:
                user.kyc_status = "rejected"
                user.kyc_rejection_reason = reason
                user.kyc_reviewed_at = datetime.datetime.utcnow()
                db.commit()
                
                # Notify user
                try:
                    await context.bot.send_message(
                        target_id,
                        f"❌ **KYC REJECTED**\n\nYour identity verification was not approved.\n\n**Reason**: {reason}\n\nPlease resubmit with valid documents.",
                        parse_mode="Markdown"
                    )
                except: pass
                
                await update.message.reply_text(f"❌ KYC rejected for `{target_id}` with reason: {reason}", parse_mode="Markdown")
        finally:
            db.close()
        return True

    # Balance Adjustment Processing
    if context.user_data.get('admin_bal_target'):
        target_id = context.user_data.pop('admin_bal_target')
        try:
            amount = float(update.message.text.strip())
            db = init_db()
            try:
                user = db.get_user_by_telegram_id(target_id)
                if user:
                    old_bal = user.wallet_balance
                    user.wallet_balance += amount
                    db.commit()
                    
                    action = "ADDED" if amount >= 0 else "SUBTRACTED"
                    await update.message.reply_text(
                        f"💰 **BALANCE UPDATED**\n"
                        f"━━━━━━━━━━━━━━━━━━━━\n"
                        f"User: `{target_id}`\n"
                        f"Action: {action} `${abs(amount):.2f}`\n"
                        f"Previous: `${old_bal:.2f}`\n"
                        f"New Balance: **`${user.wallet_balance:.2f}`**",
                        parse_mode="Markdown"
                    )
                    
                    # Notify user
                    try:
                        await context.bot.send_message(
                            target_id,
                            f"💰 **WALLET UPDATE**\n\nYour balance has been adjusted by an administrator.\n\nAdjustment: `{' insurgent' if amount >= 0 else ''}${amount:.2f}`\nNew Total: **`${user.wallet_balance:.2f}`**",
                            parse_mode="Markdown"
                        )
                    except: pass
            finally:
                db.close()
        except ValueError:
            await update.message.reply_text("❌ Invalid amount. Please enter a number (e.g. 100 or -50).")
        return True
    
    return False
