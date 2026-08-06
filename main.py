import os
import datetime
import asyncio
import json
import threading
import urllib.request
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# ================= DUMMY WEB SERVER FOR RENDER PORT BINDING =================
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Sarkari Super-Bot is running fine!")

    def log_message(self, format, *args):
        return  # Terminal log clean rakhne ke liye

def start_health_check_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

# Start Web Server Thread
threading.Thread(target=start_health_check_server, daemon=True).start()

# ================= CONFIGURATION =================
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")
GPLINKS_API_KEY = "28f7b134d7e185764342aa508fdb2a43b1e93970"
LOG_CHANNEL_ID = "-1004379498816"
FORCE_JOIN_LINK = "https://t.me/+UYT1dE4cXuA5NTVI"
ADMIN_ID = os.getenv("ADMIN_ID", "123456789")

# ================= IN-MEMORY DATABASE =================
USER_NOTES = {}
USER_POINTS = {}
USER_STREAKS = {}
USER_REFERRALS = {}
USER_STATE = {}
USER_LEVELS = {}
ALL_USER_IDS = set()

# Mock Questions Bank
MOCK_BANK = {
    "gk": [
        {"q": "Bharat ka sabse bada national park kaun sa hai?", "options": ["Gir", "Hemis", "Kaziranga", "Jim Corbett"], "ans": 1, "exp": "Hemis National Park (Ladakh) sabse bada hai."},
        {"q": "NITI Aayog ke ex-officio Chairman kaun hote hain?", "options": ["Rashtrapati", "Vitta Mantri", "Pradhan Mantri", "RBI Governor"], "ans": 2, "exp": "Bharat ke Pradhan Mantri iske adhyaksh hote hain."}
    ],
    "maths": [
        {"q": "Agar ek rectangle ki length 20% badhe aur breadth 10% ghate, toh area me kya change hoga?", "options": ["+8%", "+10%", "-8%", "+12%"], "ans": 0, "exp": "Net change = 20 - 10 - (20x10)/100 = +8% increase."},
        {"q": "Pehli 5 prime numbers ka average kya hoga?", "options": ["5.2", "5.6", "6.0", "4.8"], "ans": 1, "exp": "Prime numbers = 2, 3, 5, 7, 11. Sum = 28/5 = 5.6."}
    ],
    "reasoning": [
        {"q": "Odd one out chunie: Apple, Mango, Potato, Banana", "options": ["Apple", "Mango", "Potato", "Banana"], "ans": 2, "exp": "Potato ek vegetable/stem hai, baki sab fruits hain."},
        {"q": "Agar CAT = 24 aur DOG = 26, toh RAT = ?", "options": ["39", "40", "38", "42"], "ans": 0, "exp": "R(18) + A(1) + T(20) = 39."}
    ]
}

# ================= HELPER FUNCTIONS =================

def shorten_link(long_url: str) -> str:
    """GPLinks Shortener Integration"""
    try:
        params = urllib.parse.urlencode({'api': GPLINKS_API_KEY, 'url': long_url})
        api_url = f"https://gplinks.in/api?{params}"
        req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            if data.get("status") == "success":
                return data.get("shortenedUrl")
    except Exception as e:
        print(f"GPLinks Error: {e}")
    return long_url

async def send_log(context: ContextTypes.DEFAULT_TYPE, message: str):
    """Log Activity to Channel"""
    try:
        await context.bot.send_message(chat_id=LOG_CHANNEL_ID, text=f"📋 **BOT LOG:**\n{message}", parse_mode="Markdown")
    except Exception as e:
        print(f"Log Error: {e}")

def calculate_exact_age(dob_str: str, cutoff_str: str):
    """Exact Age Calculator"""
    dob = datetime.datetime.strptime(dob_str, "%d-%m-%Y").date()
    cutoff = datetime.datetime.strptime(cutoff_str, "%d-%m-%Y").date()
    
    years = cutoff.year - dob.year
    months = cutoff.month - dob.month
    days = cutoff.day - dob.day

    if days < 0:
        months -= 1
        days += 30
    if months < 0:
        years -= 1
        months += 12

    return years, months, days

# ================= COMMAND HANDLERS =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    ALL_USER_IDS.add(user_id)

    # Handle Referral System
    if context.args and context.args[0].startswith("ref_"):
        referrer_id = context.args[0].replace("ref_", "")
        if referrer_id != str(user_id) and user_id not in USER_POINTS:
            try:
                ref_int = int(referrer_id)
                USER_REFERRALS[ref_int] = USER_REFERRALS.get(ref_int, 0) + 1
                USER_POINTS[ref_int] = USER_POINTS.get(ref_int, 0) + 100
                await context.bot.send_message(
                    chat_id=ref_int, 
                    text=f"🎉 **New Referral!** {user.first_name} joined using your link. Earned **+100 Points**!"
                )
            except Exception:
                pass

    if user_id not in USER_POINTS:
        USER_POINTS[user_id] = 50
        USER_LEVELS[user_id] = "Beginner Aspirant"

    await send_log(context, f"User Active: {user.full_name} (`{user_id}`)")

    keyboard = [
        [InlineKeyboardButton("📢 Join Official Channel", url=FORCE_JOIN_LINK)],
        [
            InlineKeyboardButton("⏱️ Multi-Subject Mock", callback_data="select_mock_subject"),
            InlineKeyboardButton("⚡ Ask AI Doubts", callback_data="ai_doubt")
        ],
        [
            InlineKeyboardButton("📰 Current Affairs Express", callback_data="ca_express"),
            InlineKeyboardButton("📄 Syllabus & PYQs Hub", callback_data="syllabus_hub")
        ],
        [
            InlineKeyboardButton("📘 Flashcards", callback_data="flashcards"),
            InlineKeyboardButton("🗣️ Vocab & Idioms", callback_data="vocab")
        ],
        [
            InlineKeyboardButton("🧮 Negative Score Calc", callback_data="calc_score"),
            InlineKeyboardButton("🎂 Precise Age Calc", callback_data="calc_age_info")
        ],
        [
            InlineKeyboardButton("📅 Target Exam Timers", callback_data="exam_timer"),
            InlineKeyboardButton("📐 Formula Bank", callback_data="formula_categories")
        ],
        [
            InlineKeyboardButton("🎁 Refer & Earn", callback_data="referral"),
            InlineKeyboardButton("🏆 Live Leaderboard", callback_data="leaderboard")
        ],
        [
            InlineKeyboardButton("📄 PDF & Form Assistant", callback_data="pdf_tools"),
            InlineKeyboardButton("📊 My Progress Card", callback_data="dashboard")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    msg = (
        f"🚀 **Welcome {user.first_name} to Sarkari Super-Bot!**\n\n"
        "India's #1 Ultra-Advanced Exam Preparation Portal.\n"
        "Select any feature below to start learning:"
    )
    await update.message.reply_text(msg, reply_markup=reply_markup, parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "🛠️ **Mega Command Suite:**\n\n"
        "• `/start` - Launch Main Navigation Menu\n"
        "• `/notes <text>` - Save personal study note\n"
        "• `/mynotes` - View all saved notes\n"
        "• `/age <DD-MM-YYYY> <Cutoff DD-MM-YYYY>` - Precise age calculation\n"
        "• `/remind <mins> <msg>` - Set live study alarm\n"
        "• `/timetable <daily_hours>` - Generate instant custom schedule\n"
        "• `/eligible <10th/12th/Graduate>` - Instant exam eligibility list\n"
        "• `/shorten <url>` - Convert link to GPLinks monetized link\n"
        "• `/dashboard` - Check rank, level & score"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")

async def generate_timetable(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        hours = float(context.args[0])
        if hours < 1 or hours > 16:
            raise ValueError()
        
        gk_time = round(hours * 0.3, 1)
        math_time = round(hours * 0.3, 1)
        reasoning_time = round(hours * 0.2, 1)
        revision_time = round(hours * 0.2, 1)

        plan = (
            f"📅 **Personalized Study Schedule ({hours} Hours/Day):**\n\n"
            f"⏱️ **GK & Current Affairs:** {gk_time} Hours\n"
            f"⏱️ **Quantitative Aptitude:** {math_time} Hours\n"
            f"⏱️ **Reasoning & Logic:** {reasoning_time} Hours\n"
            f"⏱️ **Revision & Mock Test:** {revision_time} Hours\n\n"
            f"💡 *Pro Tip: Take a 5-minute break every 50 minutes of studying!*"
        )
        await update.message.reply_text(plan, parse_mode="Markdown")
    except Exception:
        await update.message.reply_text("⚠️ Usage: `/timetable <daily_study_hours>`\nExample: `/timetable 6`", parse_mode="Markdown")

async def check_eligibility(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ Usage: `/eligible 10th` OR `/eligible 12th` OR `/eligible Graduate`", parse_mode="Markdown")
        return
    
    qual = context.args[0].lower()
    if "10" in qual:
        text = "🎓 **Exams Eligible for 10th Pass:**\n• SSC MTS & Havaldar\n• Railway Group D & RPF Constable\n• GD Constable (CAPF)\n• Post Office GDS"
    elif "12" in qual:
        text = "🎓 **Exams Eligible for 12th Pass:**\n• SSC CHSL & Stenographer\n• Railway NTPC (Undergraduate Posts)\n• NDA / NA Entrance Exam\n• State Police Constables"
    else:
        text = "🎓 **Exams Eligible for Graduates:**\n• SSC CGL & CPO\n• UPSC CSE / CDS\n• IBPS PO & Clerk / SBI PO\n• Railway NTPC (Graduate Posts)"
    
    await update.message.reply_text(text, parse_mode="Markdown")

async def add_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    note = " ".join(context.args)
    if not note:
        await update.message.reply_text("⚠️ Usage: `/notes <your note here>`", parse_mode="Markdown")
        return
    if user_id not in USER_NOTES:
        USER_NOTES[user_id] = []
    USER_NOTES[user_id].append(note)
    await update.message.reply_text("✅ Note saved! Access using `/mynotes`.", parse_mode="Markdown")

async def get_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    notes = USER_NOTES.get(user_id, [])
    if not notes:
        await update.message.reply_text("📝 No saved notes found.", parse_mode="Markdown")
        return
    text = "📝 **Your Saved Exam Notes:**\n\n" + "\n".join([f"{i+1}. {n}" for i, n in enumerate(notes)])
    await update.message.reply_text(text, parse_mode="Markdown")

async def age_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        dob_str = context.args[0]
        cutoff_str = context.args[1]
        y, m, d = calculate_exact_age(dob_str, cutoff_str)
        await update.message.reply_text(
            f"🎂 **Exact Age Result:**\n\n👉 **{y} Years, {m} Months, {d} Days** as of {cutoff_str}",
            parse_mode="Markdown"
        )
    except Exception:
        await update.message.reply_text("⚠️ Format: `/age DD-MM-YYYY DD-MM-YYYY`", parse_mode="Markdown")

async def set_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        mins = int(context.args[0])
        msg = " ".join(context.args[1:])
        await update.message.reply_text(f"⏰ Reminder set for {mins} minutes!", parse_mode="Markdown")
        await asyncio.sleep(mins * 60)
        await update.message.reply_text(f"🔔 **REMINDER:** {msg}", parse_mode="Markdown")
    except Exception:
        await update.message.reply_text("⚠️ Usage: `/remind <minutes> <message>`", parse_mode="Markdown")

async def shorten_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ Usage: `/shorten <url>`", parse_mode="Markdown")
        return
    shortened = shorten_link(context.args[0])
    await update.message.reply_text(f"🔗 **Monetized Link:**\n{shortened}", parse_mode="Markdown")

# ================= CALLBACK ROUTER =================

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data == "select_mock_subject":
        keyboard = [
            [InlineKeyboardButton("🧠 General Knowledge", callback_data="start_mock_gk")],
            [InlineKeyboardButton("📐 Mathematics", callback_data="start_mock_maths")],
            [InlineKeyboardButton("🧩 Reasoning", callback_data="start_mock_reasoning")],
            [InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]
        ]
        await query.message.reply_text("🎯 **Select Mock Test Subject:**", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("start_mock_"):
        subj = data.replace("start_mock_", "")
        q = MOCK_BANK[subj][0]
        keyboard = []
        for idx, opt in enumerate(q["options"]):
            keyboard.append([InlineKeyboardButton(f"{chr(65+idx)}. {opt}", callback_data=f"ansmock_{subj}_{idx}")])
        await query.message.reply_text(
            f"⏱️ **Live Mock Test ({subj.upper()}):**\n\n{q['q']}", 
            reply_markup=InlineKeyboardMarkup(keyboard), 
            parse_mode="Markdown"
        )

    elif data.startswith("ansmock_"):
        parts = data.split("_")
        subj, ans_idx = parts[1], int(parts[2])
        q = MOCK_BANK[subj][0]
        
        if ans_idx == q["ans"]:
            USER_POINTS[user_id] = USER_POINTS.get(user_id, 0) + 20
            res = f"✅ **Correct! (+20 Points)**\n\n💡 **Explanation:** {q['exp']}"
        else:
            res = f"❌ **Incorrect!**\n\n💡 **Explanation:** {q['exp']}"
            
        keyboard = [[InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]]
        await query.message.reply_text(res, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "ca_express":
        text = (
            "📰 **Daily Current Affairs Express:**\n\n"
            "1. RBI updates key policy rates to maintain monetary stability.\n"
            "2. India announces new renewable energy initiative target for 2030.\n"
            "3. National Sports Awards winners felicitated.\n\n"
            "📌 *For full daily PDF digests, check our main channel!*"
        )
        keyboard = [
            [InlineKeyboardButton("📥 Download PDF", url=FORCE_JOIN_LINK)],
            [InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]
        ]
        await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "syllabus_hub":
        keyboard = [
            [InlineKeyboardButton("🔴 SSC CGL / CHSL", url=FORCE_JOIN_LINK), InlineKeyboardButton("🚆 Railway NTPC", url=FORCE_JOIN_LINK)],
            [InlineKeyboardButton("🏦 Bank PO / Clerk", url=FORCE_JOIN_LINK), InlineKeyboardButton("👮 Defence / Police", url=FORCE_JOIN_LINK)],
            [InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]
        ]
        await query.message.reply_text("📄 **Official Syllabus & PYQ Portal:**", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "ai_doubt":
        USER_STATE[user_id] = "awaiting_ai_question"
        await query.message.reply_text("⚡ **AI Exam Assistant Active!**\n\nType any concept or doubt message in chat:")

    elif data == "flashcards":
        text = "📘 **Flashcard:**\n\n**Q:** Which article of the Constitution deals with Fundamental Rights?\n\n*Tap to reveal answer!*"
        keyboard = [[InlineKeyboardButton("👁️ Reveal Answer", callback_data="ans_fc")]]
        await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "ans_fc":
        await query.message.edit_text("📘 **Flashcard:**\n\n**A:** Articles 12 to 35 (Part III of the Constitution)", parse_mode="Markdown")

    elif data == "vocab":
        text = (
            "🗣️ **Vocabulary & Idioms Booster:**\n\n"
            "• **Word:** *Prudent* (बुद्धिमान/विवेकपूर्ण)\n"
            "• **Meaning:** Acting with or showing care for the future.\n"
            "• **Idiom:** *Hit the nail on the head* (सटीक बात कहना)"
        )
        await query.message.reply_text(text, parse_mode="Markdown")

    elif data == "calc_score":
        text = (
            "🧮 **Negative Score Formula:**\n\n"
            "`Final Score = (Correct Answers × Marks) - (Wrong Answers × Negative Penalty)`\n\n"
            "• SSC Format: +2 for Correct, -0.50 for Wrong\n"
            "• Banking Format: +1 for Correct, -0.25 for Wrong"
        )
        await query.message.reply_text(text, parse_mode="Markdown")

    elif data == "calc_age_info":
        await query.message.reply_text("🎂 Use `/age DD-MM-YYYY Cutoff_DD-MM-YYYY` to compute exact cutoff eligibility.", parse_mode="Markdown")

    elif data == "exam_timer":
        today = datetime.date.today()
        ssc_days = (datetime.date(2026, 9, 15) - today).days
        rrb_days = (datetime.date(2026, 11, 10) - today).days
        text = f"📅 **Target Countdown:**\n\n⏳ **SSC CGL 2026:** {ssc_days} Days\n⏳ **RRB NTPC 2026:** {rrb_days} Days"
        await query.message.reply_text(text, parse_mode="Markdown")

    elif data == "formula_categories":
        text = (
            "📐 **Quick Formula Bank:**\n\n"
            "• **Algebra:** `(a + b)² = a² + b² + 2ab`\n"
            "• **Trigonometry:** `sin²θ + cos²θ = 1`\n"
            "• **Physics:** `Work = Force × Displacement`"
        )
        await query.message.reply_text(text, parse_mode="Markdown")

    elif data == "referral":
        bot_info = await context.bot.get_me()
        ref_link = f"https://t.me/{bot_info.username}?start=ref_{user_id}"
        refs = USER_REFERRALS.get(user_id, 0)
        pts = USER_POINTS.get(user_id, 0)
        text = (
            f"🎁 **Referral Program:**\n\n"
            f"Your referral link:\n`{ref_link}`\n\n"
            f"📊 **Stats:** Referrals: `{refs}` | Points: `{pts}`"
        )
        await query.message.reply_text(text, parse_mode="Markdown")

    elif data == "leaderboard":
        text = (
            "🏆 **Global Aspirants Leaderboard:**\n\n"
            "1. 🥇 Rahul Sharma - 1,250 Pts\n"
            "2. 🥈 Priya Singh - 980 Pts\n"
            "3. 🥉 Amit Kumar - 850 Pts"
        )
        await query.message.reply_text(text, parse_mode="Markdown")

    elif data == "pdf_tools":
        text = (
            "🛠️ **Form Utilities Suite:**\n\n"
            "• SSC Photo Specs: 3.5cm x 4.5cm (<50KB)\n"
            "• Signature Specs: 10KB - 20KB JPG\n"
            "• PDF Compression & Merger guidance"
        )
        await query.message.reply_text(text, parse_mode="Markdown")

    elif data == "dashboard":
        pts = USER_POINTS.get(user_id, 0)
        notes_cnt = len(USER_NOTES.get(user_id, []))
        refs = USER_REFERRALS.get(user_id, 0)
        lvl = USER_LEVELS.get(user_id, "Beginner Aspirant")
        text = (
            f"📊 **Personal Dashboard:**\n\n"
            f"👤 User: {query.from_user.first_name}\n"
            f"🎖️ Level: `{lvl}`\n"
            f"⭐ Points: `{pts}`\n"
            f"📝 Notes Saved: `{notes_cnt}`\n"
            f"👥 Referrals: `{refs}`"
        )
        await query.message.reply_text(text, parse_mode="Markdown")

    elif data == "main_menu":
        await start(update, context)

# ================= MESSAGE HANDLER =================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    state = USER_STATE.get(user_id)
    text = update.message.text.strip()

    if state == "awaiting_ai_question":
        ans = (
            f"🤖 **AI Exam Tutor Solution:**\n\n"
            f"Regarding: *\"{text}\"*\n\n"
            f"👉 **Key Concept:** This is an important topic for Sarkari exams. "
            f"Always revise fundamental definitions and practice PYQs."
        )
        await update.message.reply_text(ans, parse_mode="Markdown")
        USER_STATE[user_id] = None

# ================= MAIN RUNNER =================

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("timetable", generate_timetable))
    app.add_handler(CommandHandler("eligible", check_eligibility))
    app.add_handler(CommandHandler("notes", add_note))
    app.add_handler(CommandHandler("mynotes", get_notes))
    app.add_handler(CommandHandler("age", age_command))
    app.add_handler(CommandHandler("remind", set_reminder))
    app.add_handler(CommandHandler("shorten", shorten_command))

    # Handlers
    app.add_handler(CallbackQueryHandler(button_click))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 Sarkari Super-Bot Mega Edition is running with Port Binding...")
    app.run_polling()

if __name__ == "__main__":
    main()
