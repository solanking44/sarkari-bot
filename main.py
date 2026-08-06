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

# ================= SQLITE DATABASE ENGINE =================
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

    # Anti-Repeat Tracking Table for Questions
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS asked_questions (
            user_id INTEGER,
            question_id INTEGER,
            PRIMARY KEY (user_id, question_id)
        )
    ''')

    # Anti-Repeat Tracking Table for Quotes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_quotes (
            user_id INTEGER,
            quote_id INTEGER,
            PRIMARY KEY (user_id, quote_id)
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

# ================= LARGE EXPANDED QUESTION BANK =================
MOCK_BANK = [
    # GK Questions (ID 1-6)
    {"id": 1, "subj": "gk", "q": "Bharat ka sabse bada national park kaun sa hai?", "options": ["Gir", "Hemis", "Kaziranga", "Jim Corbett"], "ans": 1, "exp": "Hemis National Park (Ladakh) sabse bada hai."},
    {"id": 2, "subj": "gk", "q": "NITI Aayog ke ex-officio Chairman kaun hote hain?", "options": ["Rashtrapati", "Vitta Mantri", "Pradhan Mantri", "RBI Governor"], "ans": 2, "exp": "Bharat ke Pradhan Mantri iske adhyaksh hote hain."},
    {"id": 3, "subj": "gk", "q": "Bharat ka pehla Atomic Power Station kahan sthapit hua tha?", "options": ["Tarapur", "Rawatbhata", "Kudankulam", "Narora"], "ans": 0, "exp": "Tarapur (Maharashtra) me 1969 me shuru hua tha."},
    {"id": 4, "subj": "gk", "q": "Bhakra Nangal Dam kis nadi par bana hai?", "options": ["Ganga", "Sutlej", "Yamuna", "Narmada"], "ans": 1, "exp": "Sutlej nadi par Himachal/Punjab border par hai."},
    {"id": 5, "subj": "gk", "q": "Indian Constitution me total kitne Fundamental Duties hain?", "options": ["10", "11", "12", "9"], "ans": 1, "exp": "Article 51A ke antargat total 11 Fundamental Duties hain."},
    {"id": 6, "subj": "gk", "q": "RBC (Red Blood Cells) ka lifespan kitne dino ka hota hai?", "options": ["90 Days", "120 Days", "150 Days", "60 Days"], "ans": 1, "exp": "RBC ka ausat jeevankaal 120 din hota hai."},

    # Maths Questions (ID 7-12)
    {"id": 7, "subj": "maths", "q": "Agar ek rectangle ki length 20% badhe aur breadth 10% ghate, toh area me kya change hoga?", "options": ["+8%", "+10%", "-8%", "+12%"], "ans": 0, "exp": "Net change = 20 - 10 - (20x10)/100 = +8% increase."},
    {"id": 8, "subj": "maths", "q": "Pehli 5 prime numbers ka average kya hoga?", "options": ["5.2", "5.6", "6.0", "4.8"], "ans": 1, "exp": "Prime numbers = 2, 3, 5, 7, 11. Sum = 28/5 = 5.6."},
    {"id": 9, "subj": "maths", "q": "Agar 15 aadmi kisi kaam ko 20 din me karte hain, toh 10 aadmi kitne din me karenge?", "options": ["25 Din", "30 Din", "35 Din", "40 Din"], "ans": 1, "exp": "(15 × 20) / 10 = 30 din."},
    {"id": 10, "subj": "maths", "q": "Simple Interest par ₹1000 ki rashi 2 saal me ₹1200 ho jaati hai, toh Rate % kya hai?", "options": ["8%", "10%", "12%", "15%"], "ans": 1, "exp": "SI = 200. Rate = (200 × 100) / (1000 × 2) = 10%."},
    {"id": 11, "subj": "maths", "q": "Cube ka side 4cm hai, uska total surface area kya hoga?", "options": ["64 sq.cm", "96 sq.cm", "48 sq.cm", "32 sq.cm"], "ans": 1, "exp": "TSA = 6 × a² = 6 × 16 = 96 sq.cm."},
    {"id": 12, "subj": "maths", "q": "Agar speed 72 km/h hai, toh m/s me conversion kya hoga?", "options": ["15 m/s", "20 m/s", "25 m/s", "30 m/s"], "ans": 1, "exp": "72 × (5/18) = 20 m/s."},

    # Reasoning Questions (ID 13-18)
    {"id": 13, "subj": "reasoning", "q": "Odd one out chunie: Apple, Mango, Potato, Banana", "options": ["Apple", "Mango", "Potato", "Banana"], "ans": 2, "exp": "Potato ek vegetable hai, baki sab fruits hain."},
    {"id": 14, "subj": "reasoning", "q": "Agar CAT = 24 aur DOG = 26, toh RAT = ?", "options": ["39", "40", "38", "42"], "ans": 0, "exp": "R(18) + A(1) + T(20) = 39."},
    {"id": 15, "subj": "reasoning", "q": "Series complete karein: 2, 6, 12, 20, 30, ?", "options": ["40", "42", "44", "36"], "ans": 1, "exp": "Differences are +4, +6, +8, +10, +12. So 30 + 12 = 42."},
    {"id": 16, "subj": "reasoning", "q": "Agar South-East North ban jaye, toh West kya banega?", "options": ["South-East", "North-East", "South-West", "North-West"], "ans": 0, "exp": "135 degree anti-clockwise shift hota hai."},
    {"id": 17, "subj": "reasoning", "q": "Blood Relation: Mohan ne kaha, 'Wah mere pita ki ekloti beti ka beta hai.' Mohan usse kaise related hai?", "options": ["Maternal Uncle (Mama)", "Father", "Brother", "Grandfather"], "ans": 0, "exp": "Pita ki beti = Behan, Behan ka beta = Bhanja. Mohan uska Mama hai."},
    {"id": 18, "subj": "reasoning", "q": "Clock me 3:00 baje Hour hand aur Minute hand ke beech kitna angle hota hai?", "options": ["60°", "90°", "120°", "45°"], "ans": 1, "exp": "3:00 baje exact 90 degree ka angle banta hai."}
]

MOTIVATIONAL_QUOTES = [
    {"id": 1, "quote": "🔥 *'Mehnat itni khamoshi se karo ki kamyabi shor macha de!'*"},
    {"id": 2, "quote": "💡 *'Every hour you spend studying today brings you closer to your uniform/officer seat.'*"},
    {"id": 3, "quote": "🚀 *'Sarkari Naukri tabhi milegi jab consistency top-notch hogi!'*"},
    {"id": 4, "quote": "🎯 *'Push yourself, because no one else is going to do it for you.'*"},
    {"id": 5, "quote": "🌟 *'Safalta ek din me nahi milti, lekin ek din zaroor milti hai!'*"},
    {"id": 6, "quote": "⚡ *'Sapne wo nahi jo hum sote hue dekhte hain, sapne wo hain jo hame sone nahi dete.'*"},
    {"id": 7, "quote": "🏆 *'Jo aaj dard sehra hai, kal wahi jeet ki khushi manayega!'*"},
    {"id": 8, "quote": "📚 *'Aapki padhai hi aapki sabse badi takat hai. Keep learning daily!'*"}
]

# ================= HELPER FUNCTIONS =================
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

def get_unseen_question(user_id, subject=None):
    """Fetch a question that user has NEVER seen before"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT question_id FROM asked_questions WHERE user_id = ?", (user_id,))
    seen_ids = set(row[0] for row in cursor.fetchall())
    
    available_qs = [q for q in MOCK_BANK if q["id"] not in seen_ids]
    if subject:
        available_qs = [q for q in available_qs if q["subj"] == subject]

    # Agar saare questions khatam ho gaye, toh reset kar do anti-repeat memory for fresh loop
    if not available_qs:
        if subject:
            cursor.execute("DELETE FROM asked_questions WHERE user_id = ? AND question_id IN (SELECT id FROM asked_questions)", (user_id,))
            available_qs = [q for q in MOCK_BANK if q["subj"] == subject]
        else:
            cursor.execute("DELETE FROM asked_questions WHERE user_id = ?", (user_id,))
            available_qs = MOCK_BANK
        conn.commit()

    selected_q = random.choice(available_qs)
    
    # Mark as seen
    cursor.execute("INSERT OR IGNORE INTO asked_questions (user_id, question_id) VALUES (?, ?)", (user_id, selected_q["id"]))
    conn.commit()
    conn.close()
    
    return selected_q

def get_unseen_quote(user_id):
    """Fetch a motivational quote that user has NOT seen recently"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT quote_id FROM user_quotes WHERE user_id = ?", (user_id,))
    seen_ids = set(row[0] for row in cursor.fetchall())
    
    available_quotes = [q for q in MOTIVATIONAL_QUOTES if q["id"] not in seen_ids]
    
    if not available_quotes:
        cursor.execute("DELETE FROM user_quotes WHERE user_id = ?", (user_id,))
        conn.commit()
        available_quotes = MOTIVATIONAL_QUOTES

    selected = random.choice(available_quotes)
    cursor.execute("INSERT OR IGNORE INTO user_quotes (user_id, quote_id) VALUES (?, ?)", (user_id, selected["id"]))
    conn.commit()
    conn.close()
    
    return selected["quote"]

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
        "✨ **India's #1 Anti-Repeat AI Preparation Portal** ✨\n\n"
        "👉 Ab har baar interactive quiz, speed test aur motivational quotes **bilkul naye aur bina repeat hue** milenge!"
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
                new_streak = 1  
                
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

async def speed_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    q = get_unseen_question(user_id) # Fetches strictly fresh question
    
    keyboard = []
    for idx, opt in enumerate(q["options"]):
        keyboard.append([InlineKeyboardButton(f"{chr(65+idx)}. {opt}", callback_data=f"ansmock_{q['id']}_{q['subj']}_{idx}")])
        
    await update.effective_message.reply_text(
        f"⚡ **UNIQUE SPEED TEST ({q['subj'].upper()}):**\n⏱️ *Fast Response Required!*\n\n{q['q']}", 
        reply_markup=InlineKeyboardMarkup(keyboard), 
        parse_mode="Markdown"
    )

async def motivate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    quote = get_unseen_quote(user_id) # Unique quote per click
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
        q_id, subj, ans_idx = int(parts[1]), parts[2], int(parts[3])
        
        # Find exact question from bank
        q = next((item for item in MOCK_BANK if item["id"] == q_id), None)
        
        if q:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            if ans_idx == q["ans"]:
                cursor.execute("UPDATE users SET points = points + 20 WHERE user_id = ?", (user_id,))
                cursor.execute(f"UPDATE stats SET total_quizzes = total_quizzes + 1, correct_answers = correct_answers + 1, {subj}_correct = {subj}_correct + 1 WHERE user_id = ?", (user_id,))
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
    app.add_handler(CommandHandler("speedtest", speed_test))
    app.add_handler(CommandHandler("motivate", motivate))
    app.add_handler(CommandHandler("leaderboard", leaderboard_command))

    # Handlers
    app.add_handler(CallbackQueryHandler(button_click))

    print("🤖 Sarkari Super-Bot PRO (Anti-Repeat Mode) is Running...")
    app.run_polling()

if __name__ == "__main__":
    main()
