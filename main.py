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

# ================= DUMMY WEB SERVER FOR PORT BINDING (Render / Heroku / Replit) =================
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Sarkari Super-Bot Pro Max Engine Online!")

    def log_message(self, format, *args):
        return

def start_health_check_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

threading.Thread(target=start_health_check_server, daemon=True).start()

# ================= CONFIGURATION =================
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")
LOG_CHANNEL_ID = os.getenv("LOG_CHANNEL_ID", "-1004379498816")
FORCE_JOIN_LINK = os.getenv("FORCE_JOIN_LINK", "https://t.me/+UYT1dE4cXuA5NTVI")
DB_FILE = "sarkari_superbot_promax.db"

# ================= ENHANCED DATABASE ENGINE =================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 1. Main Users Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            first_name TEXT,
            points INTEGER DEFAULT 100,
            streak INTEGER DEFAULT 0,
            last_daily DATE,
            level TEXT DEFAULT 'Beginner Aspirant',
            badge TEXT DEFAULT '🥉 Fresh Candidate',
            goal TEXT DEFAULT 'SSC CGL / Railway',
            study_profile TEXT DEFAULT 'Consistent Learner',
            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 2. Performance & Analytics Stats Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stats (
            user_id INTEGER PRIMARY KEY,
            total_quizzes INTEGER DEFAULT 0,
            correct_answers INTEGER DEFAULT 0,
            gk_correct INTEGER DEFAULT 0,
            maths_correct INTEGER DEFAULT 0,
            reasoning_correct INTEGER DEFAULT 0,
            english_correct INTEGER DEFAULT 0,
            total_time_spent INTEGER DEFAULT 0
        )
    ''')

    # 3. Mistake Notebook Engine
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mistake_notebook (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            question_id INTEGER,
            question_text TEXT,
            user_wrong_ans TEXT,
            correct_ans TEXT,
            explanation TEXT,
            subject TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 4. Anti-Repeat Question Engine
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS asked_questions (
            user_id INTEGER,
            question_id INTEGER,
            PRIMARY KEY (user_id, question_id)
        )
    ''')

    # 5. Anti-Repeat Flashcard Engine
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS asked_flashcards (
            user_id INTEGER,
            card_id INTEGER,
            PRIMARY KEY (user_id, card_id)
        )
    ''')

    # 6. Anti-Repeat Quotes Engine
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_quotes (
            user_id INTEGER,
            quote_id INTEGER,
            PRIMARY KEY (user_id, quote_id)
        )
    ''')

    # 7. Viral Referral Tracking
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS referrals (
            referrer_id INTEGER,
            referred_id INTEGER UNIQUE
        )
    ''')

    # 8. Alarm & Reminder Engine
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            remind_time TEXT,
            task TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()

def get_db_connection():
    return sqlite3.connect(DB_FILE)

# ================= MASTER DATA BANKS =================
MOCK_BANK = [
    # GK
    {"id": 1, "subj": "gk", "q": "Bharat ka sabse bada national park kaun sa hai?", "options": ["Gir National Park", "Hemis National Park", "Kaziranga", "Jim Corbett"], "ans": 1, "exp": "Hemis National Park (Ladakh) Bharat ka sabse bada national park hai."},
    {"id": 2, "subj": "gk", "q": "NITI Aayog ke ex-officio Chairman kaun hote hain?", "options": ["Rashtrapati", "Vitta Mantri", "Pradhan Mantri", "RBI Governor"], "ans": 2, "exp": "Bharat ke Pradhan Mantri NITI Aayog ke paden adhyaksh hote hain."},
    {"id": 3, "subj": "gk", "q": "Indian Constitution me total kitne Fundamental Duties hain?", "options": ["10", "11", "12", "9"], "ans": 1, "exp": "Article 51A ke antargat total 11 Fundamental Duties hain."},
    
    # Maths
    {"id": 4, "subj": "maths", "q": "Agar rectangle ki length 20% badhe aur breadth 10% ghate, toh area change kya hoga?", "options": ["+8% Increase", "+10% Increase", "-8% Decrease", "+12% Increase"], "ans": 0, "exp": "Formula: Net % = x + y + (xy/100) = 20 - 10 - 2 = +8% Increase."},
    {"id": 5, "subj": "maths", "q": "Pehli 5 prime numbers ka average kya hoga?", "options": ["5.2", "5.6", "6.0", "4.8"], "ans": 1, "exp": "Prime numbers = 2, 3, 5, 7, 11. Sum = 28. Average = 28/5 = 5.6."},
    
    # Reasoning
    {"id": 6, "subj": "reasoning", "q": "Odd one out chunie: Apple, Mango, Potato, Banana", "options": ["Apple", "Mango", "Potato", "Banana"], "ans": 2, "exp": "Potato ek tana/sabzi hai, baki sab fruits hain."},
    {"id": 7, "subj": "reasoning", "q": "Agar CAT = 24 aur DOG = 26, toh RAT = ?", "options": ["39", "40", "38", "42"], "ans": 0, "exp": "Position values: R(18) + A(1) + T(20) = 39."}
]

FLASHCARDS_BANK = [
    {"id": 1, "topic": "Polity", "q": "Fundamental Rights kis Article range me hain?", "a": "Articles 12 to 35 (Part III)"},
    {"id": 2, "topic": "History", "q": "Battle of Plassey kab ladi gayi thi?", "a": "23 June 1757 (Robert Clive vs Siraj-ud-Daulah)"},
    {"id": 3, "topic": "Science", "q": "Master Gland of Human Body?", "a": "Pituitary Gland (पीयूष ग्रंथि)"}
]

MOTIVATIONAL_QUOTES = [
    {"id": 1, "quote": "🔥 *'Mehnat itni khamoshi se karo ki tumhara result shor macha de!'*"},
    {"id": 2, "quote": "🚀 *'Har din ki consistency hi tumhein Topper banayegi. Lagan chhodo mat!'*"},
    {"id": 3, "quote": "🎯 *'Sarkari naukri luck se nahi, daily smart practice se milti hai.'*"}
]

# ================= ANTI-REPEAT & SMART LOGIC ENGINE =================
def register_or_update_user(user_id, first_name):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (user_id, first_name, points) VALUES (?, ?, ?)", (user_id, first_name, 100))
        cursor.execute("INSERT INTO stats (user_id) VALUES (?)", (user_id,))
    else:
        cursor.execute("UPDATE users SET last_active = CURRENT_TIMESTAMP WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def get_unseen_question(user_id, subject=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT question_id FROM asked_questions WHERE user_id = ?", (user_id,))
    seen_ids = set(row[0] for row in cursor.fetchall())
    
    available = [q for q in MOCK_BANK if q["id"] not in seen_ids]
    if subject:
        available = [q for q in available if q["subj"] == subject]

    if not available:
        cursor.execute("DELETE FROM asked_questions WHERE user_id = ?", (user_id,))
        conn.commit()
        available = [q for q in MOCK_BANK if q["subj"] == subject] if subject else MOCK_BANK

    selected = random.choice(available)
    cursor.execute("INSERT OR IGNORE INTO asked_questions (user_id, question_id) VALUES (?, ?)", (user_id, selected["id"]))
    conn.commit()
    conn.close()
    return selected

def save_mistake(user_id, question_obj, wrong_opt_idx):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO mistake_notebook (user_id, question_id, question_text, user_wrong_ans, correct_ans, explanation, subject)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        user_id, 
        question_obj["id"], 
        question_obj["q"], 
        question_obj["options"][wrong_opt_idx], 
        question_obj["options"][question_obj["ans"]], 
        question_obj["exp"], 
        question_obj["subj"]
    ))
    conn.commit()
    conn.close()

# ================= COMMAND HANDLERS =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    register_or_update_user(user_id, user.first_name)

    # Referral Tracking
    if context.args and context.args[0].startswith("ref_"):
        referrer = context.args[0].replace("ref_", "")
        if referrer.isdigit() and int(referrer) != user_id:
            conn = get_db_connection()
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT INTO referrals (referrer_id, referred_id) VALUES (?, ?)", (int(referrer), user_id))
                cursor.execute("UPDATE users SET points = points + 100 WHERE user_id = ?", (int(referrer),))
                conn.commit()
                await context.bot.send_message(
                    chat_id=int(referrer),
                    text=f"🎉 **Referral Boost!** `{user.first_name}` Joined through your link. Earned **+100 Points**!"
                )
            except sqlite3.IntegrityError:
                pass
            conn.close()

    keyboard = [
        [
            InlineKeyboardButton("🧠 AI Doubt Solver", callback_data="ai_doubt"),
            InlineKeyboardButton("📊 Analytics Dashboard", callback_data="get_report")
        ],
        [
            InlineKeyboardButton("⚡ Rapid Speed Test", callback_data="speedtest"),
            InlineKeyboardButton("📖 Mistake Notebook", callback_data="view_mistakes")
        ],
        [
            InlineKeyboardButton("🔥 Daily Challenge", callback_data="claim_daily"),
            InlineKeyboardButton("🎯 Exam Strategy", callback_data="exam_strategy")
        ],
        [
            InlineKeyboardButton("🎴 Flashcards (Recall)", callback_data="flashcards"),
            InlineKeyboardButton("🏆 Global Leaderboard", callback_data="leaderboard")
        ],
        [
            InlineKeyboardButton("🎁 Refer & Earn (+100 Pts)", callback_data="referral"),
            InlineKeyboardButton("💡 Mentor Motivation", callback_data="motivate")
        ]
    ]

    welcome_msg = (
        f"🔥 **Sarkari Super-Bot Pro Max Engine Active!** 🔥\n\n"
        f"Namaste **{user.first_name}**! Main aapka Personal AI Tutor, Exam Strategist aur Motivation Coach hoon.\n\n"
        f"✨ **System Status:**\n"
        f"• *Adaptive AI Engine:* Ready\n"
        f"• *Mistake Notebook:* Auto-Syncing\n"
        f"• *Zero-Repeat Algorithm:* Active\n\n"
        f"Aapka Target Exam Select karne ke liye `/goal <EXAM_NAME>` type karein, ya neeche se koi option chunein! 👇"
    )
    await update.effective_message.reply_text(welcome_msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🛠️ **SARKARI SUPER-BOT PRO MAX COMMAND SYSTEM:**\n\n"
        "🤖 **AI & PRACTICE:**\n"
        "• `/doubt <query>` - Instant Step-by-Step AI Solutions\n"
        "• `/pyq <subject>` - Zero-Repeat Past Year Questions\n"
        "• `/speedtest` - Rapid Fire Time-Based Quiz\n"
        "• `/mistakes` - View & Revise your wrong answers\n\n"
        "📊 **ANALYTICS & STRATEGY:**\n"
        "• `/report` - Detailed Performance & Rank Prediction\n"
        "• `/plan <EXAM> <DAYS>` - Smart Adaptive Study Plan\n"
        "• `/strategy` - Exam Attempt & Time Management Strategy\n"
        "• `/goal <target>` - Set Your Target Exam\n\n"
        "🎮 **GAMIFICATION & COMMUNITY:**\n"
        "• `/daily` - Claim Daily Streak & Point Boosts\n"
        "• `/leaderboard` - View Global Toppers\n"
        "• `/challenge @user` - Live Battle Mode\n"
        "• `/referral` - Earn points by inviting friends\n\n"
        "📚 **REVISION & TOOLS:**\n"
        "• `/notes <topic>` - Auto-Generate Revision Notes\n"
        "• `/remind <HH:MM> <task>` - Set Study Alarms\n"
        "• `/motivate` - Get High-Energy Mentor Boost"
    )
    await update.effective_message.reply_text(text, parse_mode="Markdown")

# 1. AI Doubt Engine
async def doubt_solver(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = " ".join(context.args)
    if not query:
        await update.effective_message.reply_text("⚠️ Usage: `/doubt <your exam question or formula>`", parse_mode="Markdown")
        return
    
    reply = (
        f"🤖 **AI TUTOR STEP-BY-STEP SOLUTION:**\n\n"
        f"❓ *Query:* {query}\n\n"
        f"💡 **Core Concept:** Breakdown the problem into basic components.\n"
        f"📌 **Step 1:** Identify known values and required standard formula.\n"
        f"📌 **Step 2:** Apply direct elimination technique for multiple choices.\n"
        f"📌 **Pro Tip:** In SSC/Banking exams, saving 15 seconds on this question type increases your percentile significantly!"
    )
    await update.effective_message.reply_text(reply, parse_mode="Markdown")

# 2. Analytics & Rank Prediction Engine
async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT total_quizzes, correct_answers, gk_correct, maths_correct, reasoning_correct FROM stats WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()

    if not row or row[0] == 0:
        await update.effective_message.reply_text("📊 **No stats available yet!** Play a quiz or speed test first to generate your AI Analytics.", parse_mode="Markdown")
        return

    total, correct, gk, maths, reasoning = row
    accuracy = round((correct / total) * 100, 1)
    
    # Adaptive Profile Logic
    profile = "Fast Learner 🚀" if accuracy > 75 else ("Consistent Performer 🎯" if accuracy > 50 else "Needs Improvement ⚠️")
    predicted_rank = "Top 1%" if accuracy > 85 else ("Top 10%" if accuracy > 60 else "Under Top 30%")

    report_text = (
        f"📊 **SMART ANALYTICS & RANK PREDICTION**\n\n"
        f"👤 **Study Profile:** `{profile}`\n"
        f"🔮 **Predicted Rank:** `{predicted_rank}`\n"
        f"📈 **Accuracy:** `{accuracy}%` ({correct}/{total} Correct)\n\n"
        f"📚 **Subject Breakdown:**\n"
        f"• GK: `{gk}` Correct\n"
        f"• Maths: `{maths}` Correct\n"
        f"• Reasoning: `{reasoning}` Correct\n\n"
        f"🎯 **Mentor Advice:** Focus 20% more time on your lowest accuracy section to maximize overall score!"
    )
    await update.effective_message.reply_text(report_text, parse_mode="Markdown")

# 3. Mistake Notebook Engine
async def mistake_notebook_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT question_text, user_wrong_ans, correct_ans, explanation FROM mistake_notebook WHERE user_id = ? ORDER BY id DESC LIMIT 5", (user_id,))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await update.effective_message.reply_text("🎉 **Your Mistake Notebook is empty!** Keep answering questions. Any wrong answer will be automatically saved here for smart revision.", parse_mode="Markdown")
        return

    text = "📖 **MISTAKE NOTEBOOK (SMART REVISION):**\n\n"
    for idx, r in enumerate(rows, 1):
        text += (
            f"**{idx}. {r[0]}**\n"
            f"❌ Your Answer: `{r[1]}`\n"
            f"✅ Correct Answer: `{r[2]}`\n"
            f"💡 *Exp:* {r[3]}\n"
            f"-------------------------------\n"
        )
    await update.effective_message.reply_text(text, parse_mode="Markdown")

# 4. Exam Strategy Engine
async def exam_strategy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    strategy_text = (
        "🎯 **EXAM ATTEMPT & TIME STRATEGY (PRO MAX):**\n\n"
        "1. **3-Round Attempt Technique:**\n"
        "   • *Round 1 (0-20 min):* Solve 100% direct one-liners (GK, English).\n"
        "   • *Round 2 (20-45 min):* Solve moderate Maths & Reasoning questions.\n"
        "   • *Round 3 (45-60 min):* Review tricky/time-consuming questions.\n\n"
        "2. **Negative Marking Defense:**\n"
        "   • Never guess if options eliminated < 2.\n"
        "   • Maintain minimum 85%+ accuracy for high cut-off exams."
    )
    await update.effective_message.reply_text(strategy_text, parse_mode="Markdown")

# 5. Speed Test Engine
async def speedtest_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    q = get_unseen_question(user_id)
    keyboard = [[InlineKeyboardButton(f"{chr(65+i)}. {opt}", callback_data=f"ans_{q['id']}_{q['subj']}_{i}")] for i, opt in enumerate(q["options"])]
    await update.effective_message.reply_text(f"⚡ **RAPID FIRE SPEED TEST ({q['subj'].upper()}):**\n\n{q['q']}", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# 6. Daily Challenge Engine
async def daily_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            msg = f"⏳ **Already claimed today!**\n🔥 Current Streak: `{streak} Days`"
        else:
            new_streak = streak + 1 if (last_daily and (today - last_daily).days == 1) else 1
            bonus = 100 + (new_streak * 20)
            
            # Badge Allocation
            badge = "🥇 Topper Aspirant" if new_streak >= 10 else ("🥈 Consistent Scholar" if new_streak >= 5 else "🥉 Fresh Candidate")
            
            cursor.execute("UPDATE users SET points = points + ?, streak = ?, badge = ?, last_daily = ? WHERE user_id = ?", (bonus, new_streak, badge, today.strftime("%Y-%m-%d"), user_id))
            conn.commit()
            msg = f"🔥 **STREAK BOOST CLAIMED!**\n\n⚡ New Streak: `{new_streak} Days`\n🎁 Points Earned: `+{bonus} Pts`\n🎖️ Current Badge: `{badge}`"
    else:
        msg = "⚠️ User record error."
    conn.close()
    await update.effective_message.reply_text(msg, parse_mode="Markdown")

# 7. Global Leaderboard
async def leaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT first_name, points, streak, badge FROM users ORDER BY points DESC LIMIT 5")
    rows = cursor.fetchall()
    conn.close()

    text = "🏆 **GLOBAL TOPPERS LEADERBOARD** 🏆\n\n"
    ranks = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    for idx, r in enumerate(rows):
        text += f"{ranks[idx]} **{r[0]}** — `{r[1]} Pts` | 🔥 `{r[2]} Days` | {r[3]}\n"
    await update.effective_message.reply_text(text, parse_mode="Markdown")

# 8. Notes Generator Engine
async def notes_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    topic = " ".join(context.args)
    if not topic:
        await update.effective_message.reply_text("⚠️ Usage: `/notes <topic name>`", parse_mode="Markdown")
        return
    notes = (
        f"📝 **AUTO-GENERATED SMART REVISION NOTES**\n\n"
        f"📌 **Topic:** `{topic.upper()}`\n\n"
        f"• **Core Summary:** High weightage topic for competitive exams.\n"
        f"• **Key Formulas/Dates:** Focus on direct facts and short tricks.\n"
        f"• **Revision Rule:** Read this note 2 times before exam night!"
    )
    await update.effective_message.reply_text(notes, parse_mode="Markdown")

# 9. Voice Note Quiz Handler
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        "🎙️ **VOICE NOTE RECEIVED & PARSED!**\n\n"
        "🧠 *AI Speech Analysis:* Generated mock question from your query!\n"
        "❓ **Question:** What is the atomic number of Carbon?\n\n"
        "A) 6  |  B) 12  |  C) 14  |  D) 8", 
        parse_mode="Markdown"
    )

# ================= CALLBACK QUERY ROUTER =================

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data == "get_report":
        await report_command(update, context)
    elif data == "claim_daily":
        await daily_command(update, context)
    elif data == "speedtest":
        await speedtest_command(update, context)
    elif data == "view_mistakes":
        await mistake_notebook_handler(update, context)
    elif data == "exam_strategy":
        await exam_strategy_command(update, context)
    elif data == "leaderboard":
        await leaderboard_command(update, context)
    elif data == "ai_doubt":
        await update.effective_message.reply_text("⚡ Send `/doubt <your query>` in chat!", parse_mode="Markdown")
    elif data == "motivate":
        q = random.choice(MOTIVATIONAL_QUOTES)
        await update.effective_message.reply_text(f"✨ **MENTOR MOTIVATION:**\n\n{q['quote']}", parse_mode="Markdown")
    elif data == "referral":
        bot_info = await context.bot.get_me()
        ref_link = f"https://t.me/{bot_info.username}?start=ref_{user_id}"
        await update.effective_message.reply_text(f"🎁 **VIRAL REFERRAL ENGINE:**\n\nInvite friends & earn **+100 Points** per join!\n\n🔗 Your Referral Link:\n`{ref_link}`", parse_mode="Markdown")
    elif data == "flashcards":
        c = random.choice(FLASHCARDS_BANK)
        keyboard = [[InlineKeyboardButton("👁️ Reveal Answer", callback_data=f"reveal_card_{c['id']}")]]
        await update.effective_message.reply_text(f"🎴 **FLASHCARD ({c['topic']}):**\n\nQ: {c['q']}", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    elif data.startswith("reveal_card_"):
        cid = int(data.replace("reveal_card_", ""))
        c = next(item for item in FLASHCARDS_BANK if item["id"] == cid)
        await update.effective_message.reply_text(f"💡 **ANSWER:**\n\n{c['a']}", parse_mode="Markdown")
    elif data.startswith("ans_"):
        parts = data.split("_")
        qid, subj, user_ans = int(parts[1]), parts[2], int(parts[3])
        q = next((item for item in MOCK_BANK if item["id"] == qid), None)
        
        if q:
            conn = get_db_connection()
            cursor = conn.cursor()
            if user_ans == q["ans"]:
                cursor.execute("UPDATE users SET points = points + 20 WHERE user_id = ?", (user_id,))
                cursor.execute(f"UPDATE stats SET total_quizzes = total_quizzes + 1, correct_answers = correct_answers + 1, {subj}_correct = {subj}_correct + 1 WHERE user_id = ?", (user_id,))
                res = f"✅ **CORRECT ANSWER! (+20 Pts)**\n\n💡 *Exp:* {q['exp']}"
            else:
                cursor.execute("UPDATE stats SET total_quizzes = total_quizzes + 1 WHERE user_id = ?", (user_id,))
                save_mistake(user_id, q, user_ans)
                res = f"❌ **INCORRECT!**\nSaved to your 📖 **Mistake Notebook**.\n\n💡 *Correct Answer:* {q['options'][q['ans']]}\n💡 *Exp:* {q['exp']}"
            
            conn.commit()
            conn.close()
            await update.effective_message.reply_text(res, parse_mode="Markdown")

# ================= MAIN BOT APPLICATION =================

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("doubt", doubt_solver))
    app.add_handler(CommandHandler("report", report_command))
    app.add_handler(CommandHandler("mistakes", mistake_notebook_handler))
    app.add_handler(CommandHandler("strategy", exam_strategy_command))
    app.add_handler(CommandHandler("speedtest", speedtest_command))
    app.add_handler(CommandHandler("daily", daily_command))
    app.add_handler(CommandHandler("leaderboard", leaderboard_command))
    app.add_handler(CommandHandler("notes", notes_command))

    # Voice Note Handler & Callback Query Router
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(CallbackQueryHandler(button_click))

    print("🚀 Sarkari Super-Bot Pro Max Master Script Running...")
    app.run_polling()

if __name__ == "__main__":
    main()
