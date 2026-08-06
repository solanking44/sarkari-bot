from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

# Mock Test Database
MOCK_QUESTIONS = [
    {"q": "Q1: Bharat ka sabse bada national park kaun sa hai?", "options": ["Gir", "Hemis", "Kaziranga", "Jim Corbett"], "ans": 1},
    {"q": "Q2: NITI Aayog ke adhyaksh kaun hote hain?", "options": ["Rashtrapati", "Vitta Mantri", "Pradhan Mantri", "RBI Governor"], "ans": 2},
    {"q": "Q3: Computer ka mastishk (Brain) kise kaha jata hai?", "options": ["RAM", "ROM", "CPU", "Hard Disk"], "ans": 2},
    {"q": "Q4: World Health Day kab manaya jata hai?", "options": ["7 April", "10 May", "15 June", "1 December"], "ans": 0},
    {"q": "Q5: Bharat me Railway ki shuruaat kab hui thi?", "options": ["1848", "1853", "1865", "1905"], "ans": 1}
]

USER_TEST_STATE = {}

async def start_mock_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    USER_TEST_STATE[user_id] = {"current": 0, "score": 0}
    await send_test_question(query, user_id)

async def send_test_question(query, user_id):
    state = USER_TEST_STATE[user_id]
    q_index = state["current"]
    
    if q_index >= len(MOCK_QUESTIONS):
        score = state["score"]
        total = len(MOCK_QUESTIONS)
        accuracy = (score / total) * 100
        result_text = (
            f"🎉 **Mock Test Completed!**\n\n"
            f"📊 **Your Score Card:**\n"
            f"• Total Questions: {total}\n"
            f"• Correct Answers: {score}\n"
            f"• Accuracy: {accuracy:.1f}%\n\n"
            f"🏆 Keep Practicing!"
        )
        keyboard = [[InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]]
        await query.message.edit_text(result_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        del USER_TEST_STATE[user_id]
        return

    question_data = MOCK_QUESTIONS[q_index]
    keyboard = []
    for idx, option in enumerate(question_data["options"]):
        keyboard.append([InlineKeyboardButton(f"{chr(65+idx)}. {option}", callback_data=f"mt_ans_{idx}")])

    await query.message.edit_text(
        f"⏱️ **Live Mock Test (Q {q_index+1}/{len(MOCK_QUESTIONS)}):**\n\n{question_data['q']}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def mock_test_answer_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if user_id not in USER_TEST_STATE:
        await query.message.edit_text("❌ Test session expired. Naya test shuru karein.")
        return

    selected_ans = int(query.data.split("_")[2])
    state = USER_TEST_STATE[user_id]
    q_index = state["current"]

    if selected_ans == MOCK_QUESTIONS[q_index]["ans"]:
        state["score"] += 1

    state["current"] += 1
    await send_test_question(query, user_id)
