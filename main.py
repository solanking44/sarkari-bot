import logging
import os
import re
from datetime import datetime
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
)

from config import BOT_TOKEN, CHANNEL_INVITE_LINK
from database import init_db, get_user_stats
from handlers.force_sub import force_sub_middleware
from handlers.tools import handle_photo_upload, convert_to_pdf_callback, calculate_age, USER_STATE
from handlers.quiz import start_quiz_handler, quiz_answer_handler, leaderboard_handler
from handlers.admin import broadcast_command, add_job_command
from handlers.ai_helper import get_ai_response

logging.basicConfig(level=logging.INFO)

# --- Render Port Binding (Health Check) ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot service running smoothly!")

def run_health_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()
# ------------------------------------------

# --- Advanced Live Mock Test Database & Engine ---
MOCK_BANK = [
    {"q": "Q1: Bharat ka sabse bada national park kaun sa hai?", "options": ["Gir National Park", "Hemis National Park", "Kaziranga", "Jim Corbett"], "ans": 1, "exp": "Hemis National Park (Ladakh) Bharat ka sabse bada national park hai."},
    {"q": "Q2: NITI Aayog ke Ex-officio Chairman kaun hote hain?", "options": ["Rashtrapati", "Vitta Mantri", "Pradhan Mantri", "RBI Governor"], "ans": 2, "exp": "Bharat ke Pradhan Mantri NITI Aayog ke adhyaksh hote hain."},
    {"q": "Q3: Computer me Brain of Computer kise kaha jata hai?", "options": ["RAM", "ROM", "CPU", "Hard Disk"], "ans": 2, "exp": "CPU (Central Processing Unit) ko computer ka brain kehte hain."},
    {"q": "Q4: International Women's Day har saal kab manaya jata hai?", "options": ["8 March", "10 April", "15 May", "1 December"], "ans": 0, "exp": "Har saal 8 March ko International Women's Day manaya jata hai."},
    {"q": "Q5: Bharat me Pehli Passenger Train (1853) kahan se kahan tak chali thi?", "options": ["Delhi to Agra", "Bombay to Thane", "Kolkata to Howrah", "Madras to Arkonam"], "ans": 1, "exp": "16 April 1853 ko pehli train Bombay se Thane ke beech chali thi."}
]

USER_MOCK_STATE = {}

async def start_mock_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    USER_MOCK_STATE[user_id] = {
        "index": 0,
        "score": 0,
        "answers": []
    }
    await render_test_card(query, user_id)

async def render_test_card(query, user_id):
    state = USER_MOCK_STATE[user_id]
    idx = state["index"]
    
    if idx >= len(MOCK_BANK):
        score = state["score"]
        total = len(MOCK_BANK)
        accuracy = (score / total) * 100
        
        result_text = (
            f"🎯 **Mock Test Completed!**\n\n"
            f"📊 **Performance Summary:**\n"
            f"• Total Questions: {total}\n"
            f"• Correct Answers: {score}\n"
            f"• Accuracy Rate: {accuracy:.1f}%\n"
            f"• Status: {'🏆 Excellent' if accuracy >= 80 else '👍 Good Effort'}\n\n"
            f"💡 Keep practicing to improve speed & accuracy!"
        )
        keyboard = [[InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]]
        await query.message.edit_text(result_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        del USER_MOCK_STATE[user_id]
        return

    item = MOCK_BANK[idx]
    keyboard = []
    for opt_idx, opt in enumerate(item["options"]):
        keyboard.append([InlineKeyboardButton(f"{chr(65+opt_idx)}. {opt}", callback_data=f"mtans_{opt_idx}")])
    
    keyboard.append([InlineKeyboardButton("❌ Cancel Test", callback_data="main_menu")])

    await query.message.edit_text(
        f"⏱️ **Live Exam Simulation (Q {idx+1}/{len(MOCK_BANK)})**\n\n"
        f"**{item['q']}**",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def handle_mock_ans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if user_id not in USER_MOCK_STATE:
        await query.message.edit_text("❌ Test session expire ho chuka hai. Main menu se dobara start karein.")
        return

    choice = int(query.data.split("_")[1])
    state = USER_MOCK_STATE[user_id]
    current_q = MOCK_BANK[state["index"]]

    if choice == current_q["ans"]:
        state["score"] += 1

    state["index"] += 1
    await render_test_card(query, user_id)

# --- Super Main Interface Router ---
async def send_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("⚡ Ask Groq AI Tutor", callback_data="set_ai_mode"), InlineKeyboardButton("⏱️ Live Mock Test", callback_data="start_mock_test")],
        [InlineKeyboardButton("📰 Daily Current Affairs", callback_data="menu_ca"), InlineKeyboardButton("📄 Syllabus & PYQs", callback_data="menu_syllabus")],
        [InlineKeyboardButton("🛠️ Form Tools (Compress/PDF)", callback_data="menu_tools"), InlineKeyboardButton("🎂 Age Calculator", callback_data="set_age_calc")],
        [InlineKeyboardButton("🧠 Daily Quiz", callback_data="start_quiz"), InlineKeyboardButton("🏆 Leaderboard", callback_data="show_leaderboard")],
        [InlineKeyboardButton("📢 Job Alerts", callback_data="menu_jobs"), InlineKeyboardButton("🎁 Refer & Earn", callback_data="refer_info")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = (
        "🚀 **Sarkari Aspirant Ultimate Super-Bot**\n\n"
        "Welcome! Aapka All-in-One Exam Preparation Suite active hai.\n"
        "Neeche diye gaye kisi bhi feature ko tap karke explore karein:"
    )
    
    if update.callback_query:
        await update.callback_query.message.edit_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    if not await force_sub_middleware(update, context):
        return

    if data in ["check_subscription", "main_menu"]:
        await send_main_menu(update, context)
    elif data == "set_ai_mode":
        USER_STATE[query.from_user.id] = "awaiting_ai_prompt"
        await query.message.reply_text("⚡ **Groq AI Exam Tutor Mode Active!**\n\nApna koi bhi doubt ya question message me type karke bhejein.")
    elif data == "set_age_calc":
        USER_STATE[query.from_user.id] = "awaiting_age_input"
        await query.message.reply_text("🎂 Apni Date of Birth aur Cutoff Date is format me bhejein:\n`DD-MM-YYYY | DD-MM-YYYY`", parse_mode="Markdown")
    elif data.startswith("set_"):
        mode = data.replace("set_", "")
        USER_STATE[query.from_user.id] = mode
        msg = "📸 **Apni photo upload karein** (Target <50KB)" if mode == "photo_50" else "✍️ **Apna signature upload karein** (Target <20KB)"
        if mode == "img_pdf":
            msg = "📄 **Images ek ek karke bhejein**, phir 'Convert to PDF' button par click karein."
        await query.message.reply_text(msg, parse_mode="Markdown")
    elif data == "make_pdf":
        await convert_to_pdf_callback(update, context)
    elif data == "start_quiz":
        await start_quiz_handler(update, context)
    elif data.startswith("ans_"):
        await quiz_answer_handler(update, context)
    elif data == "start_mock_test":
        await start_mock_test(update, context)
    elif data.startswith("mtans_"):
        await handle_mock_ans(update, context)
    elif data == "show_leaderboard":
        await leaderboard_handler(update, context)
    elif data == "menu_ca":
        ca_text = (
            "🗞️ **Daily Current Affairs Express:**\n\n"
            "1. RBI ne latest Monetary Policy announcement me Repo Rate unchanged rakha.\n"
            "2. ISRO ne upcoming space mission launch timeline declare ki.\n"
            "3. National Sports Awards list update hui.\n\n"
            "📌 PDF version ke liye hamara main telegram channel check karein!"
        )
        keyboard = [
            [InlineKeyboardButton("📥 Download Daily PDF", url=CHANNEL_INVITE_LINK)],
            [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")]
        ]
        await query.message.edit_text(ca_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    elif data == "menu_syllabus":
        syl_text = "📄 **Syllabus & Previous Year Question Papers (PYQs):**"
        keyboard = [
            [InlineKeyboardButton("🔴 SSC CGL / CHSL", url=CHANNEL_INVITE_LINK), InlineKeyboardButton("🚆 Railway NTPC / Group D", url=CHANNEL_INVITE_LINK)],
            [InlineKeyboardButton("🏦 Bank PO / Clerk", url=CHANNEL_INVITE_LINK), InlineKeyboardButton("👮 Police & Defence", url=CHANNEL_INVITE_LINK)],
            [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")]
        ]
        await query.message.edit_text(syl_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    elif data == "menu_tools":
        keyboard = [
            [InlineKeyboardButton("🖼️ Compress Photo (<50KB)", callback_data="set_photo_50")],
            [InlineKeyboardButton("✍️ Compress Signature (<20KB)", callback_data="set_sig_20")],
            [InlineKeyboardButton("📄 Convert Images to PDF", callback_data="set_img_pdf")],
            [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")]
        ]
        await query.message.edit_text("📸 **Form Assistant & Utility Tools:**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    elif data == "menu_jobs":
        keyboard = [
            [InlineKeyboardButton("🔴 Latest Government Jobs", url=CHANNEL_INVITE_LINK)],
            [InlineKeyboardButton("📜 Admit Cards & Keys", url=CHANNEL_INVITE_LINK)],
            [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")]
        ]
        await query.message.edit_text("🎯 **Live Recruitment & Notification Updates:**", reply_markup=InlineKeyboardMarkup(keyboard))
    elif data == "refer_info":
        bot_info = await context.bot.get_me()
        user_id = query.from_user.id
        ref_link = f"https://t.me/{bot_info.username}?start={user_id}"
        stats = await get_user_stats(user_id)
        score = stats[0] if stats else 0
        referrals = stats[1] if stats else 0
        text = (
            f"🎁 **Referral & Bonus Program!**\n\n"
            f"Apna link dosto ke sath share karein:\n`{ref_link}`\n\n"
            f"📊 **Aapke Stats:**\n"
            f"• Total Referrals: {referrals}\n"
            f"• Reward Points: {score}"
        )
        keyboard = [[InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await force_sub_middleware(update, context):
        return
    await send_main_menu(update, context)

async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    mode = USER_STATE.get(user_id)
    text = update.message.text.strip()
    
    if mode == "awaiting_age_input":
        try:
            parts = text.split("|")
            if len(parts) != 2:
                raise ValueError("Invalid format")
            dob_str, cutoff_str = parts[0].strip(), parts[1].strip()
            years, months, days = await calculate_age(dob_str, cutoff_str)
            res_text = f"🎂 **Age Calculation Result:**\n\n👉 **{years} Years, {months} Months, {days} Days**"
            await update.message.reply_text(res_text, parse_mode="Markdown")
            USER_STATE[user_id] = None
        except Exception:
            await update.message.reply_text("❌ Galat Format! Kripya is format me bhejein:\n`DD-MM-YYYY | DD-MM-YYYY`", parse_mode="Markdown")
    else:
        status_msg = await update.message.reply_text("⚡ Groq AI request process kar raha hai...")
        ai_reply = await get_ai_response(text)
        await status_msg.edit_text(f"🤖 **Groq AI Answer:**\n\n{ai_reply}", parse_mode="Markdown")
        USER_STATE[user_id] = None

async def post_init(application):
    await init_db()

if __name__ == "__main__":
    Thread(target=run_health_server, daemon=True).start()
    
    app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("broadcast", broadcast_command))
    app.add_handler(CommandHandler("add_job", add_job_command))
    
    app.add_handler(CallbackQueryHandler(callback_router))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo_upload))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_handler))

    print("🤖 Sarkari Super-Bot fully operational...")
    app.run_polling()
