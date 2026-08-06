from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import TelegramError
from config import CHANNEL_ID, CHANNEL_INVITE_LINK
from database import add_user

async def is_subscribed(bot, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=int(CHANNEL_ID), user_id=user_id)
        return member.status in ['creator', 'administrator', 'member']
    except TelegramError:
        return False

async def force_sub_middleware(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user = update.effective_user
    
    ref_id = None
    if context.args and context.args[0].isdigit():
        ref_id = int(context.args[0])

    await add_user(user.id, user.first_name, ref_id)
    
    subscribed = await is_subscribed(context.bot, user.id)
    if not subscribed:
        keyboard = [
            [InlineKeyboardButton("📢 Join Channel First", url=CHANNEL_INVITE_LINK)],
            [InlineKeyboardButton("✅ Try Again / Check", callback_data="check_subscription")]
        ]
        text = "⚠️ **Access Denied!**\n\nBot ko use karne ke liye pehle hamara official Telegram Channel join karein."
        
        if update.callback_query:
            await update.callback_query.answer("Pehle Channel Join Karein!", show_alert=True)
        else:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return False
    return True
