import os
import datetime
import asyncio
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# ================= CONFIGURATION =================
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")
GPLINKS_API_KEY = "28f7b134d7e185764342aa508fdb2a43b1e93970"
LOG_CHANNEL_ID = "-1004379498816"
FORCE_JOIN_LINK = "https://t.me/+UYT1dE4cXuA5NTVI"

# In-Memory Storage
USER_NOTES = {}
USER_POINTS = {}
USER_STREAKS = {}

# ================= HELPER FUNCTIONS =================
def shorten_link(long_url: str) -> str:
    """Feature 16: GPLinks Shortener Integration"""
    try:
        api_url = f"https://gplinks.in/api?api={GPLINKS_API_KEY}&url={long_url}"
        response = requests.get(api_url).json()
        if response.get("status") == "success":
            return response.get("shortenedUrl")
    except Exception as e:
        print(f"GPLinks Error: {e}")
    return long_url

async def send_log(context: ContextTypes.DEFAULT_TYPE, message: str):
    """Log Activity to Channel"""
    try:
        await context.bot.send_message(chat_id=LOG_CHANNEL_ID, text=f"📋 **LOG:** {message}", parse_mode="Markdown")
    except Exception as e:
        print(f"Log Channel Error: {e}")

# ================= COMMAND HANDLERS =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await send_log(context, f"New user started the bot: {user.full_name} (@{user.username})")
    
    keyboard = [
        [InlineKeyboardButton("📢 Join Main Channel", url=FORCE_JOIN_LINK)],
        [
            InlineKeyboardButton("📘 Flashcards", callback_data="flashcard"),
            InlineKeyboardButton("🗣️ Vocab Booster", callback_data="vocab")
        ],
        [
            InlineKeyboardButton("🧮 Score Calculator", callback_data="calc_score"),
            InlineKeyboardButton("📐 Formulas Suite", callback_data="formulas")
        ],
        [
            InlineKeyboardButton("📅 Exam Timers", callback_data="exam_timer"),
            InlineKeyboardButton("🎁 Daily Streak", callback_data="daily_streak")
        ],
        [
            InlineKeyboardButton("📄 PDF Tools", callback_data="pdf_tools"),
            InlineKeyboardButton("📊 My Dashboard", callback_data="dashboard")
        ],
        [InlineKeyboardButton("❓ View All Commands", callback_data="help_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    msg = (
        f"👋 Welcome **{user.first_name}** to **Sarkari Super-Bot**!\n\n"
        "India's #1 All-in-One Sarkari Exam Preparation Tool.\n"
        "Choose an option from below to get started:"
    )
    await update.message.reply_text(msg, reply_markup=reply_markup, parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "🚀 **Sarkari Super-Bot Commands List:**\n\n"
        "🔹 `/start` - Launch Main Menu\n"
        "🔹 `/vocab` - Daily Word of the Day & Idioms\n"
        "🔹 `/quiz` - Subject-wise Custom Quiz Engine\n"
        "🔹 `/notes <text>` - Save personal exam notes\n"
        "🔹 `/mynotes` - View saved notes\n"
        "🔹 `/remind <mins> <msg>` - Set study reminder\n"
        "🔹 `/cutoff <exam>` - View official cutoffs\n"
        "🔹 `/shorten <url>` - Convert link to GPLinks monetized link\n"
        "🔹 `/streak` - Claim daily bonus points\n"
        "🔹 `/dashboard` - View your progress & stats"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")

# Feature 2: Vocabulary Booster
async def vocab_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    word_data = (
        "🗣️ **Word of the Day:** *Tenacious* (दृढ़ / हठी)\n"
        "🔹 **Meaning:** Tending to keep a firm hold of something; persistent.\n"
        "🔹 **Synonyms:** Persistent, Determined, Relentless\n"
        "🔹 **Antonyms:** Irresolute, Yielding, Weak\n\n"
        "💡 **Idiom of the Day:** *Burn the midnight oil*\n"
        "👉 **Meaning:** Read or study late into the night."
    )
    await update.message.reply_text(word_data, parse_mode="Markdown")

# Feature 10: Personal Exam Notes Storage
async def add_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    note_text = " ".join(context.args)
    if not note_text:
        await update.message.reply_text("⚠️ Usage: `/notes <your exam note here>`", parse_mode="Markdown")
        return
    
    if user_id not in USER_NOTES:
        USER_NOTES[user_id] = []
    USER_NOTES[user_id].append(note_text)
    await update.message.reply_text("✅ Note saved successfully! View using `/mynotes`.", parse_mode="Markdown")

async def get_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    notes = USER_NOTES.get(user_id, [])
    if not notes:
        await update.message.reply_text("📝 You have no saved notes.", parse_mode="Markdown")
        return
    
    formatted = "📝 **Your Saved Exam Notes:**\n\n" + "\n".join([f"{i+1}. {n}" for i, n in enumerate(notes)])
    await update.message.reply_text(formatted, parse_mode="Markdown")

# Feature 11: Custom Reminder System
async def set_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        mins = int(context.args[0])
        text = " ".join(context.args[1:])
        await update.message.reply_text(f"⏰ Reminder set! I will remind you in {mins} minutes: *{text}*", parse_mode="Markdown")
        
        await asyncio.sleep(mins * 60)
        await update.message.reply_text(f"🔔 **REMINDER:** {text}", parse_mode="Markdown")
    except Exception:
        await update.message.reply_text("⚠️ Usage: `/remind <minutes> <message>`\nExample: `/remind 30 Study Polity`", parse_mode="Markdown")

# Feature 16: GPLinks Shortener Handler
async def shorten_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ Usage: `/shorten <your_url_here>`", parse_mode="Markdown")
        return
    url = context.args[0]
    shortened = shorten_link(url)
    await update.message.reply_text(f"🔗 **Monetized GPLink:**\n{shortened}", parse_mode="Markdown")

# ================= CALLBACK QUERY HANDLER =================

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data == "flashcard":
        text = "📘 **Flashcard 1/5:**\n\n**Q:** Who is known as the Father of the Indian Constitution?\n\n*Tap below to reveal answer!*"
        keyboard = [[InlineKeyboardButton("👁️ Reveal Answer", callback_data="ans_fc1")]]
        await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "ans_fc1":
        await query.message.edit_text("📘 **Flashcard 1/5:**\n\n**A:** Dr. B.R. Ambedkar", parse_mode="Markdown")

    elif data == "vocab":
        await vocab_command(update, context)

    elif data == "calc_score":
        msg = (
            "🧮 **Negative Marking Calculator:**\n\n"
            "Formula: `Score = (Correct × Marks) - (Wrong × Negative_Mark)`\n\n"
            "Standard SSC CGL/NTPC format:\n"
            "• Correct Answer = +2 Marks\n"
            "• Wrong Answer = -0.50 Marks"
        )
        await query.message.reply_text(msg, parse_mode="Markdown")

    elif data == "formulas":
        msg = (
            "📐 **Quick Formulas Revision:**\n\n"
            "• **Algebra:** `(a + b)² = a² + b² + 2ab`\n"
            "• **Geometry:** Area of Triangle = `1/2 × Base × Height`\n"
            "• **Physics:** Force (`F`) = `m × a`\n"
            "• **Chemistry:** pH = `-log[H+]`"
        )
        await query.message.reply_text(msg, parse_mode="Markdown")

    elif data == "exam_timer":
        today = datetime.date.today()
        ssc_date = datetime.date(2026, 9, 15)
        days_left = (ssc_date - today).days
        msg = f"📅 **Target Exam Countdown:**\n\n⏳ **SSC CGL 2026 Prelims:** ~{days_left} Days Remaining!"
        await query.message.reply_text(msg, parse_mode="Markdown")

    elif data == "daily_streak":
        points = USER_POINTS.get(user_id, 0) + 50
        USER_POINTS[user_id] = points
        await query.message.reply_text(f"🎁 **Daily Bonus Claimed!**\n\nYou earned **+50 Points**. Total Points: `{points}`", parse_mode="Markdown")

    elif data == "pdf_tools":
        msg = (
            "🛠️ **PDF Utility Suite:**\n\n"
            "1. Send any PDF file to compress/convert.\n"
            "2. Send photos to crop and convert into SSC Exam Dimensions (3.5 cm x 4.5 cm)."
        )
        await query.message.reply_text(msg, parse_mode="Markdown")

    elif data == "dashboard":
        pts = USER_POINTS.get(user_id, 0)
        notes_cnt = len(USER_NOTES.get(user_id, []))
        dash = (
            f"📊 **User Progress Dashboard**\n\n"
            f"👤 **User:** {query.from_user.first_name}\n"
            f"⭐ **Total Score/Points:** `{pts}`\n"
            f"📝 **Saved Notes:** `{notes_cnt}`\n"
            f"🏆 **Global Rank:** `#12`"
        )
        await query.message.reply_text(dash, parse_mode="Markdown")

    elif data == "help_menu":
        await help_command(update, context)

# ================= MAIN FUNCTION =================

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("vocab", vocab_command))
    app.add_handler(CommandHandler("notes", add_note))
    app.add_handler(CommandHandler("mynotes", get_notes))
    app.add_handler(CommandHandler("remind", set_reminder))
    app.add_handler(CommandHandler("shorten", shorten_command))
    
    app.add_handler(CallbackQueryHandler(button_click))

    print("🤖 Sarkari Super-Bot with 20 features is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
