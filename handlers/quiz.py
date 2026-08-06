from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import update_score, get_leaderboard

QUIZ_DATA = {
    "question": "Which Article of the Indian Constitution deals with Fundamental Duties?",
    "options": ["Article 51A", "Article 12-35", "Article 32", "Article 44"],
    "correct": 0
}

async def start_quiz_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = []
    for idx, opt in enumerate(QUIZ_DATA["options"]):
        keyboard.append([InlineKeyboardButton(opt, callback_data=f"ans_{idx}")])
        
    await query.message.edit_text(
        f"❓ **Daily Quiz Question:**\n\n{QUIZ_DATA['question']}",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def quiz_answer_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    ans_idx = int(query.data.split("_")[1])
    user_id = query.from_user.id
    
    if ans_idx == QUIZ_DATA["correct"]:
        await update_score(user_id, 10)
        await query.answer("🎉 Correct Answer! (+10 Points Added)", show_alert=True)
    else:
        await query.answer("❌ Wrong Answer! Try again tomorrow.", show_alert=True)
        
    await query.message.delete()

async def leaderboard_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    leaders = await get_leaderboard()
    
    text = "🏆 **Top 5 Aspirants Leaderboard:**\n\n"
    for idx, (name, score) in enumerate(leaders, start=1):
        text += f"{idx}. **{name}** — {score} Pts\n"
        
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]]
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
