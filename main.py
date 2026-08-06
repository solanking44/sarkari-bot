import os
import sqlite3
import datetime
import asyncio
import json
import random
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
        self.wfile.write(b"Sarkari Super-Bot Pro Edition is Running!")

    def log_message(self, format, *args):
        return

def start_health_check_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

threading.Thread(target=start_health_check_server, daemon=True).start()

# ================= CONFIGURATION =================
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")
GPLINKS_API_KEY = "28f7b134d7e185764342aa508fdb2a43b1e93970"
LOG_CHANNEL_ID = "-1004379498816"
FORCE_JOIN_LINK = "https://t.me/+UYT1dE4cXuA5NTVI"
DB_FILE = "bot_database.db"

# ================= SQLITE DATABASE ENGINE (LOCAL/CLOUD PERSISTENCE) =================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Users Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            first_name TEXT,
            points INTEGER DEFAULT 50,
            streak INTEGER DEFAULT 0,
            last_daily DATE,
            level TEXT DEFAULT 'Beginner Aspirant',
            goal TEXT DEFAULT 'Not Set'
        )
    ''')
    
    # Performance Stats Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stats (
            user_id INTEGER PRIMARY KEY,
            total_quizzes INTEGER DEFAULT 0,
            correct_answers INTEGER DEFAULT 0,
            gk_correct INTEGER DEFAULT 0,
            maths_correct INTEGER DEFAULT 0,
            reasoning_correct INTEGER DEFAULT 0
        )
    ''')
    
    # Notes Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            note_text TEXT
        )
    ''')

    # Referrals Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS referrals (
            referrer_id INTEGER,
            referred_id INTEGER UNIQUE
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()

def get_db_connection():
    return sqlite3.connect(DB_FILE)

# ================= DATA BANKS =================
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

MOTIVATIONAL_QUOTES = [
    "🔥 *'Mehnat itni khamoshi se karo ki kamyabi shor macha de!'*",
    "💡 *'Every hour you spend studying today brings you closer to your uniform/officer seat.'*",
    "🚀 *'Sarkari Naukri tabhi milegi jab consistency top-notch hogi!'*",
    "🎯 *'Push yourself, because no one else is going to do it for you.'*"
]

# ================= HELPER FUNCTIONS =================
def shorten_link(long_url: str) -> str:
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
    try:
        await context.bot.send_message(chat_id=LOG_CHANNEL_ID, text=f"📋 **BOT LOG:**\n{message}", parse_mode="Markdown")
    except Exception as e:
        print(f"Log Error: {e}")

# DB User Register / Update Helper
def register_or_get_user(user_id, first_name):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    if not user:
        cursor.execute("INSERT INTO users (user_id, first_name, points) VALUES (?, ?, ?)", (user_id, first_name, 50))
        cursor.execute("INSERT INTO stats (user_id) VALUES (?)", (user_id,))
        conn.commit()
    conn.close()

# ================= COMMAND HANDLERS =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    register_or_get_user(user_id, user.first_name)

    # Referral Check
    if context.args and context.args[0].startswith("ref_"):
        referrer_id_str = context.args[0].replace("ref_", "")
        if referrer_id_str.isdigit():
            referrer_id = int(referrer_id_str)
            if referrer_id != user_id:
                conn = get_db_connection()
                cursor = conn.cursor()
                try:
                    cursor.execute("INSERT INTO referrals (referrer_id, referred_id) VALUES (?, ?)", (referrer_id, user_id))
                    cursor.execute("UPDATE users SET points = points + 50 WHERE user_id = ?", (referrer_id,))
                    conn.commit()
                    await context.bot.send_message(
                        chat_id=referrer_id,
                        text=f"🎉 **Referral Bonus!** {user.first_name} joined using your link. Earned **+50 Points**!"
                    )
                except sqlite3.IntegrityError:
                    pass
                conn.close()

    await send_log(context, f"User Active: {user.full_name} (`{user_id}`)")

    keyboard = [
        [InlineKeyboardButton("📢 Join Official Channel", url=FORCE_JOIN_LINK)],
        [
            InlineKeyboardButton("🧠 Offline/AI Doubt Solver", callback_data="ai_doubt"),
            InlineKeyboardButton("📊 My Performance Report", callback_data="get_report")
        ],
        [
            InlineKeyboardButton("🔥 Daily Challenge / Streak", callback_data="claim_daily"),
            InlineKeyboardButton("⚡ Speed Test (Rapid Fire)", callback_data="speedtest")
        ],
        [
            InlineKeyboardButton("🎯 Target Study Planner", callback_data="study_planner"),
            InlineKeyboardButton("📚 PYQ Practice Mode", callback_data="pyq_practice")
        ],
        [
            InlineKeyboardButton("🎁 Refer & Earn (+50 Pts)", callback_data="referral"),
            InlineKeyboardButton("🏆 Leaderboard", callback_data="leaderboard")
        ],
        [
            InlineKeyboardButton("💡 Daily Motivation", callback_data="motivate"),
            InlineKeyboardButton("📊 Full Dashboard", callback_data="dashboard")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    msg = (
        f"🚀 **Welcome {user.first_name} to Sarkari Super-Bot PRO!**\n\n"
        "✨ **India's #1 AI & Gamified Preparation Portal** ✨\n\n"
        "👉 Complete daily challenges, solve PYQs, track your goals, and win leaderboard ranks!"
    )
    await update.effective_message.reply_text(msg, reply_markup=reply_markup, parse_mode="Markdown")

async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT total_quizzes, correct_answers, gk_correct, maths_correct, reasoning_correct FROM stats WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row or row[0] == 0:
        await update.effective_message.reply_text("📊 **No performance data found!** Complete mock tests to view your report card.", parse_mode="Markdown")
        return
        
    total, correct, gk, maths, reasoning = row
    acc = round((correct / total) * 100, 1) if total > 0 else 0
    
    scores = {"GK": gk, "Maths": maths, "Reasoning": reasoning}
    strong_subject = max(scores, key=scores.get)
    weak_subject = min(scores, key=scores.get)

    report_msg = (
        f"📊 **PERFORMANCE ANALYTICS DASHBOARD**\n\n"
        f"📝 **Total Questions Attempted:** `{total}`\n"
        f"✅ **Correct Answers:** `{correct}`\n"
        f"📈 **Overall Accuracy:** `{acc}%`\n\n"
        f"🧠 **Strong Area:** `{strong_subject}`\n"
        f"⚠️ **Needs Improvement:** `{weak_subject}`\n\n"
        f"💡 *Tip: Practice 10 questions daily in {weak_subject} to boost accuracy!*"
    )
    await update.effective_message.reply_text(report_msg, parse_mode="Markdown")

async def daily_challenge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    today = datetime.date.today()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT points, streak, last_daily FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    
    if row:
        pts, streak, last_daily_str = row
        last_daily = datetime.datetime.strptime(last_daily_str, "%Y-%m-%d").date() if last_daily_str else None
        
        if last_daily == today:
            msg = f"⏳ **Already Claimed!**\n\nYou have already claimed today's streak reward.\nCurrent Streak: 🔥 **{streak} Days**"
        else:
            if last_daily and (today - last_daily).days == 1:
                new_streak = streak + 1
            else:
                new_streak = 1  # Reset streak if missed
                
            bonus_points = 50 + (new_streak * 10)
            cursor.execute("UPDATE users SET points = points + ?, streak = ?, last_daily = ? WHERE user_id = ?", 
                           (bonus_points, new_streak, today.strftime("%Y-%m-%d"), user_id))
            conn.commit()
            msg = (
                f"🔥 **DAILY STREAK BOOST CLAIMED!**\n\n"
                f"⚡ Current Streak: **{new_streak} Days**\n"
                f"🎁 Points Earned: **+{bonus_points} Pts**"
            )
    else:
        msg = "⚠️ User record not found. Type `/start` first."
        
    conn.close()
    await update.effective_message.reply_text(msg, parse_mode="Markdown")

async def study_plan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.effective_message.reply_text("⚠️ Usage: `/plan <EXAM_NAME> <DAYS>`\nExample: `/plan SSC 60`", parse_mode="Markdown")
        return
    
    exam = context.args[0].upper()
    try:
        days = int(context.args[1])
    except ValueError:
        await update.effective_message.reply_text("⚠️ Days specify karne ke liye valid number enter karein.")
        return

    phase1 = round(days * 0.5)
    phase2 = round(days * 0.3)
    phase3 = days - phase1 - phase2

    plan_text = (
        f"🎯 **SMART STUDY PLAN GENERATOR ({exam} - {days} DAYS)**\n\n"
        f"📌 **Phase 1 (Day 1 - {phase1}): Concept Building**\n"
        f"• Complete Basic to Advanced Syllabus\n"
        f"• Daily 2 Hours Quantitative Aptitude + 2 Hours Reasoning\n\n"
        f"📌 **Phase 2 (Day {phase1+1} - {phase1+phase2}): PYQ & Subject Tests**\n"
        f"• Practice 50 PYQs daily per subject\n"
        f"• Focus on weak areas & speed shortcuts\n\n"
        f"📌 **Phase 3 (Day {phase1+phase2+1} - {days}): Full Mock & Revision**\n"
        f"• Attempt 1 Full Length Mock Test Daily\n"
        f"• Deep analysis of incorrect attempts\n\n"
        f"💡 *All the best for {exam}! Stick to this routine daily.*"
    )
    await update.effective_message.reply_text(plan_text, parse_mode="Markdown")

async def doubt_solver(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = " ".join(context.args).lower()
    if not query:
        await update.effective_message.reply_text("⚠️ Usage: `/doubt <your doubt query>`\nExample: `/doubt integration by parts`", parse_mode="Markdown")
        return

    # Keyword AI Logic (Rule-based Offline Engine)
    if "integration" in query or "calculus" in query:
        ans = "📐 **Integration by Parts Rule:**\n`∫ u v dx = u ∫v dx - ∫ (u' ∫v dx) dx`\nUse **ILATE** priority rule to select `u`."
    elif "rectangle" in query or "area" in query:
        ans = "📐 **Rectangle Formulas:**\n• Area = `Length × Breadth`\n• Perimeter = `2 × (Length + Breadth)`"
    elif "article" in query or "constitution" in query:
        ans = "🏛️ **Important Articles:**\n• Fundamental Rights: Articles 12 to 35\n• Emergency Provisions: Articles 352, 356, 360"
    else:
        ans = f"🤖 **AI Doubt Tutor Response:**\n\nRegarding: *'{query}'*\n👉 **Solution Concept:** Practice foundational standard formulas & solve 5 previous year exam questions on this topic."

    await update.effective_message.reply_text(ans, parse_mode="Markdown")

async def speed_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    subj = random.choice(["gk", "maths", "reasoning"])
    q = random.choice(MOCK_BANK[subj])
    
    keyboard = []
    for idx, opt in enumerate(q["options"]):
        keyboard.append([InlineKeyboardButton(f"{chr(65+idx)}. {opt}", callback_data=f"ansmock_{subj}_{idx}")])
        
    await update.effective_message.reply_text(
        f"⚡ **RAPID FIRE SPEED TEST ({subj.upper()}):**\n⏱️ *Fast Response Required!*\n\n{q['q']}", 
        reply_markup=InlineKeyboardMarkup(keyboard), 
        parse_mode="Markdown"
    )

async def set_goal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    goal_text = " ".join(context.args)
    if not goal_text:
        await update.effective_message.reply_text("⚠️ Usage: `/goal <your exam goal>`\nExample: `/goal Target SSC CGL 2026 Rank under 500`", parse_mode="Markdown")
        return
        
    user_id = update.effective_user.id
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET goal = ? WHERE user_id = ?", (goal_text, user_id))
    conn.commit()
    conn.close()
    
    await update.effective_message.reply_text(f"🎯 **Target Goal Locked!**\n\n`{goal_text}`", parse_mode="Markdown")

async def motivate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    quote = random.choice(MOTIVATIONAL_QUOTES)
    await update.effective_message.reply_text(f"✨ **STUDY MOTIVATION BOOSTER** ✨\n\n{quote}", parse_mode="Markdown")

async def leaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT first_name, points, streak FROM users ORDER BY points DESC LIMIT 5")
    rows = cursor.fetchall()
    conn.close()
    
    text = "🏆 **GLOBAL ASPIRANTS LEADERBOARD** 🏆\n\n"
    badges = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    for idx, row in enumerate(rows):
        name, pts, streak = row
        text += f"{badges[idx]} **{name}** — `{pts} Pts` (🔥 {streak} Streak)\n"
        
    await update.effective_message.reply_text(text, parse_mode="Markdown")

# ================= CALLBACK ROUTER =================

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data == "get_report":
        await report_command(update, context)

    elif data == "claim_daily":
        await daily_challenge(update, context)

    elif data == "speedtest":
        await speed_test(update, context)

    elif data == "study_planner":
        await update.effective_message.reply_text("🎯 Usage: Send `/plan <EXAM_NAME> <DAYS>` in chat to get your day-wise strategy schedule!", parse_mode="Markdown")

    elif data == "pyq_practice":
        await speed_test(update, context)

    elif data == "motivate":
        await motivate(update, context)

    elif data == "ai_doubt":
        await update.effective_message.reply_text("⚡ **AI Doubt Engine Active!**\n\nType `/doubt <your question>` in chat to resolve doubts instantly.", parse_mode="Markdown")

    elif data == "referral":
        bot_info = await context.bot.get_me()
        ref_link = f"https://t.me/{bot_info.username}?start=ref_{user_id}"
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id = ?", (user_id,))
        ref_count = cursor.fetchone()[0]
        cursor.execute("SELECT points FROM users WHERE user_id = ?", (user_id,))
        pts = cursor.fetchone()[0]
        conn.close()

        text = (
            f"🎁 **REFERRAL & VIRAL GROWTH PROGRAM:**\n\n"
            f"Your referral link:\n`{ref_link}`\n\n"
            f"📊 **Stats:** Referrals: `{ref_count}` | Total Points: `{pts}`\n"
            f"💡 *Earn +50 Points for every friend who joins!*"
        )
        await update.effective_message.reply_text(text, parse_mode="Markdown")

    elif data == "leaderboard":
        await leaderboard_command(update, context)

    elif data == "dashboard":
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT points, streak, level, goal FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            pts, streak, lvl, goal = row
            text = (
                f"📊 **PERSONAL PROGRESS CARD**\n\n"
                f"👤 Aspirant: **{query.from_user.first_name}**\n"
                f"🎖️ Status: `{lvl}`\n"
                f"⭐ Points: `{pts}`\n"
                f"🔥 Streak: `{streak} Days`\n"
                f"🎯 Locked Goal: `{goal}`"
            )
        else:
            text = "⚠️ Dashboard data unavailable."
            
        await update.effective_message.reply_text(text, parse_mode="Markdown")

    elif data.startswith("ansmock_"):
        parts = data.split("_")
        subj, ans_idx = parts[1], int(parts[2])
        q = MOCK_BANK[subj][0]
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if ans_idx == q["ans"]:
            cursor.execute("UPDATE users SET points = points + 20 WHERE user_id = ?", (user_id,))
            cursor.execute("UPDATE stats SET total_quizzes = total_quizzes + 1, correct_answers = correct_answers + 1 WHERE user_id = ?", (user_id,))
            res = f"✅ **Correct Answer! (+20 Points)**\n\n💡 **Explanation:** {q['exp']}"
        else:
            cursor.execute("UPDATE stats SET total_quizzes = total_quizzes + 1 WHERE user_id = ?", (user_id,))
            res = f"❌ **Incorrect!**\n\n💡 **Explanation:** {q['exp']}"
            
        conn.commit()
        conn.close()
        
        await update.effective_message.reply_text(res, parse_mode="Markdown")

# ================= MAIN RUNNER =================

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("report", report_command))
    app.add_handler(CommandHandler("daily", daily_challenge))
    app.add_handler(CommandHandler("plan", study_plan_command))
    app.add_handler(CommandHandler("doubt", doubt_solver))
    app.add_handler(CommandHandler("speedtest", speed_test))
    app.add_handler(CommandHandler("goal", set_goal))
    app.add_handler(CommandHandler("motivate", motivate))
    app.add_handler(CommandHandler("leaderboard", leaderboard_command))

    # Handlers
    app.add_handler(CallbackQueryHandler(button_click))

    print("🤖 Sarkari Super-Bot PRO Edition with SQLite is Running...")
    app.run_polling()

if __name__ == "__main__":
    main()
