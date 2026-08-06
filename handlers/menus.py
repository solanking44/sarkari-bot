from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import get_user_stats
from config import CHANNEL_INVITE_LINK

async def send_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🛠️ Form Tools (Compress/PDF)", callback_data="menu_tools")],
        [InlineKeyboardButton("🎂 Sarkari Age Calculator", callback_data="set_age_calc")],
        [InlineKeyboardButton("📢 Job Alerts", callback_data="menu_jobs"), InlineKeyboardButton("📚 Free Notes", callback_data="menu_notes")],
        [InlineKeyboardButton("🧠 Daily Quiz", callback_data="start_quiz"), InlineKeyboardButton("🏆 Leaderboard", callback_data="show_leaderboard")],
        [InlineKeyboardButton("🎁 Refer & Earn Points", callback_data="refer_info"), InlineKeyboardButton("📖 Exam Books", callback_data="menu_books")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "👋 **Welcome to Sarkari Aspirant Buddy Bot!**\n\nApna option select karein:"
    
    if update.callback_query:
        await update.callback_query.message.edit_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

async def menu_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    await query.answer()

    if data == "menu_tools":
        keyboard = [
            [InlineKeyboardButton("🖼️ Compress Photo (<50KB)", callback_data="set_photo_50")],
            [InlineKeyboardButton("✍️ Compress Signature (<20KB)", callback_data="set_sig_20")],
            [InlineKeyboardButton("📄 Images to PDF", callback_data="set_img_pdf")],
            [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")]
        ]
        await query.message.edit_text("📸 **Form Helper Tools:**\nSelect tool:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "menu_jobs":
        keyboard = [
            [InlineKeyboardButton("🔴 SSC Jobs", url=CHANNEL_INVITE_LINK), InlineKeyboardButton("🚆 Railway", url=CHANNEL_INVITE_LINK)],
            [InlineKeyboardButton("🏦 Banking", url=CHANNEL_INVITE_LINK), InlineKeyboardButton("👮 Police/Defence", url=CHANNEL_INVITE_LINK)],
            [InlineKeyboardButton("📜 Admit Card / Results", url=CHANNEL_INVITE_LINK)],
            [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
        ]
        await query.message.edit_text("🎯 **Category-Wise Latest Vacancies:**", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "menu_books":
        keyboard = [
            [InlineKeyboardButton("📚 SSC CGL Best Books", url="https://amzn.to/3EXAMPLE")],
            [InlineKeyboardButton("📚 Reasoning & Math Formulas", url="https://amzn.to/3EXAMPLE")],
            [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
        ]
        await query.message.edit_text("🛒 **Recommended Books for Government Exams:**", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "refer_info":
        bot_info = await context.bot.get_me()
        user_id = query.from_user.id
        ref_link = f"https://t.me/{bot_info.username}?start={user_id}"
        
        stats = await get_user_stats(user_id)
        score = stats[0] if stats else 0
        referrals = stats[1] if stats else 0
        
        text = (
            f"🎁 **Refer & Earn Bonus Points!**\n\n"
            f"Apne dosto ko invite karein aur har referral par **+20 Quiz Points** paayein!\n\n"
            f"🔗 **Your Referral Link:**\n`{ref_link}`\n\n"
            f"📊 **Your Stats:**\n"
            f"• Total Referrals: {referrals}\n"
            f"• Current Points: {score}"
        )
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
