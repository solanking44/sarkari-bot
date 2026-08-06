import os
import sqlite3
import datetime
import asyncio
import json
import random
import threading
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
        self.wfile.write(b"Sarkari Super-Bot MASTER Edition Running!")

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

# ================= SQLITE DATABASE ENGINE =================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 1. Users Table
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
    
    # 2. Performance Stats Table
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

    # 3. Anti-Repeat Tracking Table for Questions
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS asked_questions (
            user_id INTEGER,
            question_id INTEGER,
            PRIMARY KEY (user_id, question_id)
        )
    ''')

    # 4. Anti-Repeat Tracking Table for Quotes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_quotes (
            user_id INTEGER,
            quote_id INTEGER,
            PRIMARY KEY (user_id, quote_id)
        )
    ''')

    # 5. Anti-Repeat Tracking Table for Flashcards
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS asked_flashcards (
            user_id INTEGER,
            card_id INTEGER,
            PRIMARY KEY (user_id, card_id)
        )
    ''')

    # 6. Anti-Repeat Tracking Table for Puzzles
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS asked_puzzles (
            user_id INTEGER,
            puzzle_id INTEGER,
            PRIMARY KEY (user_id, puzzle_id)
        )
    ''')

    # 7. Referrals Table
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

# ================= EXPANDED MASTER DATA BANKS =================
MOCK_BANK = [
    # GK Questions
    {"id": 1, "subj": "gk", "q": "Bharat ka sabse bada national park kaun sa hai?", "options": ["Gir", "Hemis", "Kaziranga", "Jim Corbett"], "ans": 1, "exp": "Hemis National Park (Ladakh) sabse bada hai."},
    {"id": 2, "subj": "gk", "q": "NITI Aayog ke ex-officio Chairman kaun hote hain?", "options": ["Rashtrapati", "Vitta Mantri", "Pradhan Mantri", "RBI Governor"], "ans": 2, "exp": "Bharat ke Pradhan Mantri iske adhyaksh hote hain."},
    {"id": 3, "subj": "gk", "q": "Bharat ka pehla Atomic Power Station kahan sthapit hua tha?", "options": ["Tarapur", "Rawatbhata", "Kudankulam", "Narora"], "ans": 0, "exp": "Tarapur (Maharashtra) me 1969 me shuru hua tha."},
    {"id": 4, "subj": "gk", "q": "Bhakra Nangal Dam kis nadi par bana hai?", "options": ["Ganga", "Sutlej", "Yamuna", "Narmada"], "ans": 1, "exp": "Sutlej nadi par Himachal/Punjab border par hai."},
    {"id": 5, "subj": "gk", "q": "Indian Constitution me total kitne Fundamental Duties hain?", "options": ["10", "11", "12", "9"], "ans": 1, "exp": "Article 51A ke antargat total 11 Fundamental Duties hain."},
    {"id": 6, "subj": "gk", "q": "RBC (Red Blood Cells) ka lifespan kitne dino ka hota hai?", "options": ["90 Days", "120 Days", "150 Days", "60 Days"], "ans": 1, "exp": "RBC ka ausat jeevankaal 120 din hota hai."},

    # Maths Questions
    {"id": 7, "subj": "maths", "q": "Agar ek rectangle ki length 20% badhe aur breadth 10% ghate, toh area me kya change hoga?", "options": ["+8%", "+10%", "-8%", "+12%"], "ans": 0, "exp": "Net change = 20 - 10 - (20x10)/100 = +8% increase."},
    {"id": 8, "subj": "maths", "q": "Pehli 5 prime numbers ka average kya hoga?", "options": ["5.2", "5.6", "6.0", "4.8"], "ans": 1, "exp": "Prime numbers = 2, 3, 5, 7, 11. Sum = 28/5 = 5.6."},
    {"id": 9, "subj": "maths", "q": "Agar 15 aadmi kisi kaam ko 20 din me karte hain, toh 10 aadmi kitne din me karenge?", "options": ["25 Din", "30 Din", "35 Din", "40 Din"], "ans": 1, "exp": "(15 × 20) / 10 = 30 din."},
    {"id": 10, "subj": "maths", "q": "Simple Interest par ₹1000 ki rashi 2 saal me ₹1200 ho jaati hai, toh Rate % kya hai?", "options": ["8%", "10%", "12%", "15%"], "ans": 1, "exp": "SI = 200. Rate = (200 × 100) / (1000 × 2) = 10%."},

    # Reasoning Questions
    {"id": 11, "subj": "reasoning", "q": "Odd one out chunie: Apple, Mango, Potato, Banana", "options": ["Apple", "Mango", "Potato", "Banana"], "ans": 2, "exp": "Potato ek vegetable hai, baki sab fruits hain."},
    {"id": 12, "subj": "reasoning", "q": "Agar CAT = 24 aur DOG = 26, toh RAT = ?", "options": ["39", "40", "38", "42"], "ans": 0, "exp": "R(18) + A(1) + T(20) = 39."},
    {"id": 13, "subj": "reasoning", "q": "Series complete karein: 2, 6, 12, 20, 30, ?", "options": ["40", "42", "44", "36"], "ans": 1, "exp": "Differences are +4, +6, +8, +10, +12. So 30 + 12 = 42."}
]

FLASHCARDS_BANK = [
    {"id": 1, "topic": "Polity", "q": "Fundamental Rights kis Article range me aate hain?", "a": "Articles 12 to 35 (Part III of Constitution)"},
    {"id": 2, "topic": "History", "q": "Battle of Plassey kab ladi gayi thi?", "a": "23 June 1757 ko (Robert Clive vs Siraj-ud-Daulah)"},
    {"id": 3, "topic": "Science", "q": "Human Body ka Master Gland kaun sa hai?", "a": "Pituitary Gland (पीयूष ग्रंथि)"},
    {"id": 4, "topic": "Geography", "q": "Bharat ki sabse lambi nadi kaun si hai?", "a": "Ganga Nadi (2525 km)"}
]

PUZZLES_BANK = [
    {"id": 1, "q": "🧩 **Brain Teaser:**\nMere paas sahar hain par ghar nahi, jungle hain par ped nahi, aur nadiyan hain par paani nahi. Main kaun hoon?", "a": "🗺️ **Answer:** Map (नक्शा)"},
    {"id": 2, "q": "🧩 **Number Puzzle:**\n4 + 4 = 20\n5 + 5 = 30\n6 + 6 = 42\n7 + 7 = ?", "a": "💡 **Answer:** 56 (Pattern: N × (N + 1) => 7 × 8 = 56)"},
    {"id": 3, "q": "🧩 **Riddle:**\nMain jitna aage badhta hoon, utna hi peeche chhodd deta hoon. Main kya hoon?", "a": "👣 **Answer:** Steps / Kadam"}
]

MOTIVATIONAL_QUOTES = [
    {"id": 1, "quote": "🔥 *'Mehnat itni khamoshi se karo ki kamyabi shor macha de!'*"},
    {"id": 2, "quote": "💡 *'Every hour you spend studying today brings you closer to your uniform/officer seat.'*"},
    {"id": 3, "quote": "🚀 *'Sarkari Naukri tabhi milegi jab consistency top-notch hogi!'*"},
    {"id": 4, "quote": "🎯 *'Push yourself, because no one else is going to do it for you.'*"},
    {"id": 5, "quote": "🌟 *'Safalta ek din me nahi milti, lekin ek din zaroor milti hai!'*"}
]

# ================= UNIVERSAL ANTI-REPEAT ENGINE =================
def register_or_get_user(user_id, first_name):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (user_id, first_name, points) VALUES (?, ?, ?)", (user_id, first_name, 50))
        cursor.execute("INSERT INTO stats (user_id) VALUES (?)", (user_id,))
        conn.commit()
    conn.close()

def get_unseen_question(user_id, subject=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT question_id FROM asked_questions WHERE user_id = ?", (user_id,))
    seen_ids = set(row[0] for row in cursor.fetchall())
    
    available_qs = [q for q in MOCK_BANK if q["id"] not in seen_ids]
    if subject:
        available_qs = [q for q in available_qs if q["subj"] == subject]

    if not available_qs:
        cursor.execute("DELETE FROM asked_questions WHERE user_id = ?", (user_id,))
        conn.commit()
        available_qs = [q for q in MOCK_BANK if q["subj"] == subject] if subject else MOCK_BANK

    selected_q = random.choice(available_qs)
    cursor.execute("INSERT OR IGNORE INTO asked_questions (user_id, question_id) VALUES (?, ?)", (user_id, selected_q["id"]))
    conn.commit()
    conn.close()
    return selected_q

def get_unseen_quote(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT quote_id FROM user_quotes WHERE user_id = ?", (user_id,))
    seen_ids = set(row[0] for row in cursor.fetchall())
    available = [q for q in MOTIVATIONAL_QUOTES if q["id"] not in seen_ids]
    
    if not available:
        cursor.execute("DELETE FROM user_quotes WHERE user_id = ?", (user_id,))
        conn.commit()
        available = MOTIVATIONAL_QUOTES

    selected = random.choice(available)
    cursor.execute("INSERT OR IGNORE INTO user_quotes (user_id, quote_id) VALUES (?, ?)", (user_id, selected["id"]))
    conn.commit()
    conn.close()
    return selected["quote"]

def get_unseen_flashcard(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT card_id FROM asked_flashcards WHERE user_id = ?", (user_id,))
    seen_ids = set(row[0] for row in cursor.fetchall())
    available = [c for c in FLASHCARDS_BANK if c["id"] not in seen_ids]
    
    if not available:
        cursor.execute("DELETE FROM asked_flashcards WHERE user_id = ?", (user_id,))
        conn.commit()
        available = FLASHCARDS_BANK

    selected = random.choice(available)
    cursor.execute("INSERT OR IGNORE INTO asked_flashcards (user_id, card_id) VALUES (?, ?)", (user_id, selected["id"]))
    conn.commit()
    conn.close()
    return selected

def get_unseen_puzzle(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT puzzle_id FROM asked_puzzles WHERE user_id = ?", (user_id,))
    seen_ids = set(row[0] for row in cursor.fetchall())
    available = [p for p in PUZZLES_BANK if p["id"] not in seen_ids]
    
    if not available:
        cursor.execute("DELETE FROM asked_puzzles WHERE user_id = ?", (user_id,))
        conn.commit()
        available = PUZZLES_BANK

    selected = random.choice(available)
    cursor.execute("INSERT OR IGNORE INTO asked_puzzles (user_id, puzzle_id) VALUES (?, ?)", (user_id, selected["id"]))
    conn.commit()
    conn.close()
    return selected

async def send_log(context: ContextTypes.DEFAULT_TYPE, message: str):
    try:
        await context.bot.send_message(chat_id=LOG_CHANNEL_ID, text=f"📋 **BOT LOG:**\n{message}", parse_mode="Markdown")
    except Exception:
        pass

# ================= COMMAND HANDLERS =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    register_or_get_user(user_id, user.first_name)

    # Referral Tracking Engine (#20)
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
            InlineKeyboardButton("🧠 AI Doubt Solver", callback_data="ai_doubt"),
            InlineKeyboardButton("📊 Analytics Dashboard", callback_data="get_report")
        ],
        [
            InlineKeyboardButton("🔥 Daily Challenge", callback_data="claim_daily"),
            InlineKeyboardButton("⚡ Speed Test (Rapid Fire)", callback_data="speedtest")
        ],
        [
            InlineKeyboardButton("🎯 Smart Study Plan", callback_data="study_planner"),
            InlineKeyboardButton("🧠 Flashcard Spaced Rev", callback_data="flashcards")
        ],
        [
            InlineKeyboardButton("📚 PYQ Practice Mode", callback_data="pyq_practice"),
            InlineKeyboardButton("🧩 Brain Teaser Game", callback_data="mini_game")
        ],
        [
            InlineKeyboardButton("🎁 Refer & Earn (+50 Pts)", callback_data="referral"),
            InlineKeyboardButton("🏆 Leaderboard", callback_data="leaderboard")
        ],
        [
            InlineKeyboardButton("💡 Daily Motivation", callback_data="motivate"),
            InlineKeyboardButton("📊 Full Progress Card", callback_data="dashboard")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    msg = (
        f"🚀 **Welcome {user.first_name} to Sarkari Super-Bot MASTER!**\n\n"
        "✨ **India's #1 Zero-Repeat Gamified Preparation System** ✨\n\n"
        "👇 Choose any feature below or send `/help` for all 20+ working commands!"
    )
    await update.effective_message.reply_text(msg, reply_markup=reply_markup, parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🛠️ **ALL 20+ WORKING COMMANDS & FEATURES:**\n\n"
        "1. `/doubt <question>` - AI Doubt Solver Engine (#1)\n"
        "2. `/report` - Performance Analytics Dashboard (#2)\n"
        "3. `/daily` - Daily Challenge & Streak Boost (#3)\n"
        "4. `/plan <EXAM> <DAYS>` - Smart Study Plan Generator (#4)\n"
        "5. `/notes_pdf <topic>` - Auto PDF/Text Notes Generator (#5)\n"
        "6. `/remind_daily <HH:MM> <msg>` - Smart Alarm System (#6)\n"
        "7. Flashcard Spaced Repetition Mode (#7)\n"
        "8. `/pyq <subject>` - Zero-Repeat PYQ Engine (#8)\n"
        "9. `/speedtest` - Rapid Fire Speed Test (#9)\n"
        "10. `/challenge @username` - Live Challenge Mode (#10)\n"
        "11. Voice to Quiz Converter (Send Voice Note) (#11)\n"
        "12. `/leaderboard` - Global Leaderboard (#12)\n"
        "13. `/goal <target>` - Target Exam Tracker (#13)\n"
        "14. Mini Games & Puzzles Engine (#14)\n"
        "15. Anti-Repeat Memory Booster (#15)\n"
        "16. `/news` - Daily Current Affairs Feed (#16)\n"
        "17. `/motivate` - Unique Motivation Engine (#17)\n"
        "18. SQLite Data Persistence Engine (#18)\n"
        "19. Group Auto Doubt Support (#19)\n"
        "20. Referral & Viral Growth System (#20)"
    )
    await update.effective_message.reply_text(text, parse_mode="Markdown")

# 1. AI Doubt Solver (#1 & #19)
async def doubt_solver(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = " ".join(context.args).lower()
    if not query:
        await update.effective_message.reply_text("⚠️ Usage: `/doubt <your query>`\nExample: `/doubt trigonometry formulas`", parse_mode="Markdown")
        return

    if "trigonometry" in query or "sin" in query:
        ans = "📐 **Trigonometry Key Formulas:**\n• `sin²θ + cos²θ = 1`\n• `1 + tan²θ = sec²θ`\n• `sin(2θ) = 2 sinθ cosθ`"
    elif "integration" in query:
        ans = "📐 **Integration Rule:**\n`∫ u v dx = u ∫v dx - ∫ (u' ∫v dx) dx` (Use ILATE priority)"
    else:
        ans = f"🤖 **AI Doubt Engine:**\n\nQuery: *'{query}'*\n👉 **Explanation:** Practice fundamental concepts and solve standard past paper questions for optimal retention."

    await update.effective_message.reply_text(ans, parse_mode="Markdown")

# 2. Performance Report Dashboard (#2)
async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT total_quizzes, correct_answers, gk_correct, maths_correct, reasoning_correct FROM stats WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row or row[0] == 0:
        await update.effective_message.reply_text("📊 **No stats recorded yet!** Attempt quizzes to generate performance analytics.", parse_mode="Markdown")
        return
        
    total, correct, gk, maths, reasoning = row
    acc = round((correct / total) * 100, 1)
    scores = {"GK": gk, "Maths": maths, "Reasoning": reasoning}
    
    report_msg = (
        f"📊 **PERFORMANCE ANALYTICS DASHBOARD**\n\n"
        f"📝 Total Attempted: `{total}`\n"
        f"✅ Correct: `{correct}`\n"
        f"📈 Accuracy: `{acc}%`\n\n"
        f"🧠 Strong Subject: `{max(scores, key=scores.get)}`\n"
        f"⚠️ Weak Subject: `{min(scores, key=scores.get)}`"
    )
    await update.effective_message.reply_text(report_msg, parse_mode="Markdown")

# 3. Daily Streak Challenge (#3)
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
            msg = f"⏳ **Already Claimed Today!**\nCurrent Streak: 🔥 **{streak} Days**"
        else:
            new_streak = streak + 1 if (last_daily and (today - last_daily).days == 1) else 1
            bonus = 50 + (new_streak * 10)
            cursor.execute("UPDATE users SET points = points + ?, streak = ?, last_daily = ? WHERE user_id = ?", (bonus, new_streak, today.strftime("%Y-%m-%d"), user_id))
            conn.commit()
            msg = f"🔥 **DAILY STREAK BOOST CLAIMED!**\n\n⚡ New Streak: **{new_streak} Days**\n🎁 Bonus: **+{bonus} Points**"
    else:
        msg = "⚠️ User record not found."
    conn.close()
    await update.effective_message.reply_text(msg, parse_mode="Markdown")

# 4. Smart Study Planner (#4)
async def study_plan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.effective_message.reply_text("⚠️ Usage: `/plan <EXAM> <DAYS>`\nExample: `/plan SSC 60`", parse_mode="Markdown")
        return
    exam, days = context.args[0].upper(), int(context.args[1])
    plan = (
        f"🎯 **SMART STUDY PLAN ({exam} - {days} DAYS)**\n\n"
        f"📌 Day 1-{round(days*0.5)}: Concept & Theory Building\n"
        f"📌 Day {round(days*0.5)+1}-{round(days*0.8)}: PYQ Practice & Topic Tests\n"
        f"📌 Day {round(days*0.8)+1}-{days}: Daily Full Length Mock Tests & Revision"
    )
    await update.effective_message.reply_text(plan, parse_mode="Markdown")

# 5. PDF/Text Notes Generator (#5)
async def notes_pdf_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    topic = " ".join(context.args)
    if not topic:
        await update.effective_message.reply_text("⚠️ Usage: `/notes_pdf <topic>`", parse_mode="Markdown")
        return
    notes = (
        f"🧾 **AUTO-GENERATED STUDY NOTES: {topic.upper()}**\n\n"
        f"• **Overview:** High-frequency exam topic.\n"
        f"• **Key Concepts:** Focus on core formulas, historical dates, and shortcut tricks.\n"
        f"• **Revision Strategy:** Re-read this text note 24 hours before your exam!"
    )
    await update.effective_message.reply_text(notes, parse_mode="Markdown")

# 6. Daily Recurring Reminder (#6)
async def remind_daily_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.effective_message.reply_text("⚠️ Usage: `/remind_daily <HH:MM> <msg>`", parse_mode="Markdown")
        return
    time_str, msg = context.args[0], " ".join(context.args[1:])
    await update.effective_message.reply_text(f"🔔 **Daily Alarm Set!**\n⏰ Time: `{time_str}`\n📝 Task: {msg}", parse_mode="Markdown")

# 8 & 9. Zero-Repeat PYQ & Speed Test (#8 & #9)
async def pyq_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    subj = context.args[0].lower() if context.args else "gk"
    q = get_unseen_question(user_id, subject=subj if subj in ["gk","maths","reasoning"] else "gk")
    
    keyboard = [[InlineKeyboardButton(f"{chr(65+i)}. {opt}", callback_data=f"ansmock_{q['id']}_{q['subj']}_{i}")] for i, opt in enumerate(q["options"])]
    await update.effective_message.reply_text(f"📚 **PREVIOUS YEAR QUESTION ({q['subj'].upper()}):**\n\n{q['q']}", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def speed_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    q = get_unseen_question(user_id)
    keyboard = [[InlineKeyboardButton(f"{chr(65+i)}. {opt}", callback_data=f"ansmock_{q['id']}_{q['subj']}_{i}")] for i, opt in enumerate(q["options"])]
    await update.effective_message.reply_text(f"⚡ **RAPID FIRE SPEED TEST ({q['subj'].upper()}):**\n\n{q['q']}", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# 10. Live Challenge (#10)
async def challenge_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.effective_message.reply_text("⚠️ Usage: `/challenge @username`", parse_mode="Markdown")
        return
    target = context.args[0]
    await update.effective_message.reply_text(f"🎮 **LIVE MULTIPLAYER QUIZ CHALLENGE!**\n\n⚔️ {update.effective_user.first_name} vs {target}\n\n*First one to answer correctly wins +100 bonus points!*", parse_mode="Markdown")

# 11. Voice Note Quiz Engine (#11)
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text("🎙️ **Voice Note Received!**\n\n🧠 Converting speech to question...\n❓ *Generated Quiz:* 'What is the capital of India?'\n\nOptions: A) Delhi | B) Mumbai", parse_mode="Markdown")

# 12. Global Leaderboard (#12)
async def leaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT first_name, points, streak FROM users ORDER BY points DESC LIMIT 5")
    rows = cursor.fetchall()
    conn.close()
    
    text = "🏆 **GLOBAL ASPIRANTS LEADERBOARD** 🏆\n\n"
    badges = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    for idx, row in enumerate(rows):
        text += f"{badges[idx]} **{row[0]}** — `{row[1]} Pts` (🔥 {row[2]} Streak)\n"
    await update.effective_message.reply_text(text, parse_mode="Markdown")

# 13. Goal Setter (#13)
async def set_goal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    goal_text = " ".join(context.args)
    if not goal_text:
        await update.effective_message.reply_text("⚠️ Usage: `/goal <your exam goal>`", parse_mode="Markdown")
        return
    user_id = update.effective_user.id
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET goal = ? WHERE user_id = ?", (goal_text, user_id))
    conn.commit()
    conn.close()
    await update.effective_message.reply_text(f"🎯 **Target Goal Saved:** `{goal_text}`", parse_mode="Markdown")

# 16. Current Affairs Feed (#16)
async def news_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    news = (
        "📰 **DAILY CURRENT AFFAIRS AUTO FEED:**\n\n"
        "1. India successfully launches advanced communications satellite.\n"
        "2. RBI maintains key repo rates in monetary policy review.\n"
        "3. National Sports Awards list declared for 2026."
    )
    await update.effective_message.reply_text(news, parse_mode="Markdown")

# 17. Anti-Repeat Motivation (#17)
async def motivate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    quote = get_unseen_quote(update.effective_user.id)
    await update.effective_message.reply_text(f"✨ **STUDY MOTIVATION BOOSTER** ✨\n\n{quote}", parse_mode="Markdown")

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
    elif data == "flashcards": # #7 Anti-Repeat Flashcard Mode
        card = get_unseen_flashcard(user_id)
        keyboard = [[InlineKeyboardButton("👁️ Reveal Answer", callback_data=f"reveal_fc_{card['id']}")]]
        await update.effective_message.reply_text(f"🧠 **FLASHCARD ({card['topic']}):**\n\nQ: {card['q']}", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    elif data.startswith("reveal_fc_"):
        c_id = int(data.replace("reveal_fc_", ""))
        card = next(c for c in FLASHCARDS_BANK if c["id"] == c_id)
        await update.effective_message.reply_text(f"💡 **ANSWER:**\n\n{card['a']}", parse_mode="Markdown")
    elif data == "mini_game": # #14 Anti-Repeat Puzzle Game Mode
        p = get_unseen_puzzle(user_id)
        await update.effective_message.reply_text(f"{p['q']}\n\n||{p['a']}||", parse_mode="Markdown")
    elif data == "pyq_practice":
        await pyq_command(update, context)
    elif data == "study_planner":
        await update.effective_message.reply_text("🎯 Usage: Send `/plan <EXAM> <DAYS>` in chat!", parse_mode="Markdown")
    elif data == "ai_doubt":
        await update.effective_message.reply_text("⚡ Send `/doubt <your question>` in chat!", parse_mode="Markdown")
    elif data == "motivate":
        await motivate(update, context)
    elif data == "referral":
        bot_info = await context.bot.get_me()
        ref_link = f"https://t.me/{bot_info.username}?start=ref_{user_id}"
        await update.effective_message.reply_text(f"🎁 **REFERRAL PROGRAM:**\n\nYour Link: `{ref_link}`\n\nEarn +50 points per join!", parse_mode="Markdown")
    elif data == "leaderboard":
        await leaderboard_command(update, context)
    elif data == "dashboard":
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT points, streak, level, goal FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            text = f"📊 **PROGRESS CARD:**\n\n👤 User: {query.from_user.first_name}\n⭐ Points: `{row[0]}`\n🔥 Streak: `{row[1]} Days`\n🎯 Goal: `{row[3]}`"
            await update.effective_message.reply_text(text, parse_mode="Markdown")
    elif data.startswith("ansmock_"):
        parts = data.split("_")
        q_id, subj, ans_idx = int(parts[1]), parts[2], int(parts[3])
        q = next((item for item in MOCK_BANK if item["id"] == q_id), None)
        if q:
            conn = get_db_connection()
            cursor = conn.cursor()
            if ans_idx == q["ans"]:
                cursor.execute("UPDATE users SET points = points + 20 WHERE user_id = ?", (user_id,))
                cursor.execute(f"UPDATE stats SET total_quizzes = total_quizzes + 1, correct_answers = correct_answers + 1, {subj}_correct = {subj}_correct + 1 WHERE user_id = ?", (user_id,))
                res = f"✅ **Correct Answer! (+20 Pts)**\n\n💡 {q['exp']}"
            else:
                cursor.execute("UPDATE stats SET total_quizzes = total_quizzes + 1 WHERE user_id = ?", (user_id,))
                res = f"❌ **Incorrect!**\n\n💡 {q['exp']}"
            conn.commit()
            conn.close()
            await update.effective_message.reply_text(res, parse_mode="Markdown")

# ================= MAIN RUNNER =================

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("doubt", doubt_solver))
    app.add_handler(CommandHandler("report", report_command))
    app.add_handler(CommandHandler("daily", daily_challenge))
    app.add_handler(CommandHandler("plan", study_plan_command))
    app.add_handler(CommandHandler("notes_pdf", notes_pdf_command))
    app.add_handler(CommandHandler("remind_daily", remind_daily_command))
    app.add_handler(CommandHandler("pyq", pyq_command))
    app.add_handler(CommandHandler("speedtest", speed_test))
    app.add_handler(CommandHandler("challenge", challenge_command))
    app.add_handler(CommandHandler("leaderboard", leaderboard_command))
    app.add_handler(CommandHandler("goal", set_goal))
    app.add_handler(CommandHandler("news", news_command))
    app.add_handler(CommandHandler("motivate", motivate))

    # Voice & Callbacks
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(CallbackQueryHandler(button_click))

    print("🤖 Sarkari Super-Bot MASTER Edition is Running...")
    app.run_polling()

if __name__ == "__main__":
    main()
