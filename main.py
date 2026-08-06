import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
)
from config import BOT_TOKEN
from database import init_db
from handlers.force_sub import force_sub_middleware
from handlers.menus import send_main_menu, menu_callback_handler
from handlers.tools import handle_photo_upload, convert_to_pdf_callback, calculate_age, USER_STATE
from handlers.quiz import start_quiz_handler, quiz_answer_handler, leaderboard_handler
from handlers.admin import broadcast_command, add_job_command

logging.basicConfig(level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await force_sub_middleware(update, context):
        return
    await send_main_menu(update, context)

async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    mode = USER_STATE.get(user_id)
    
    if mode == "awaiting_age_input":
        text = update.message.text.strip()
        try:
            dob_str, cutoff_str = [x.strip() for x in text.split("|")]
            years, months, days = await calculate_age(dob_str, cutoff_str)
            
            res_text = (
                f"🎂 **Age Calculation Result:**\n\n"
                f"• **DOB:** {dob_str}\n"
                f"• **Age as on {cutoff_str}:**\n"
                f"👉 **{years} Years, {months} Months, {days} Days**"
            )
            await update.message.reply_text(res_text, parse_mode="Markdown")
            USER_STATE[user_id] = None
        except Exception:
            await update.message.reply_text("❌ Invalid Format! Please send in format: `DD-MM-YYYY | DD-MM-YYYY`", parse_mode="Markdown")

async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    if not await force_sub_middleware(update, context):
        return

    if data in ["check_subscription", "main_menu"]:
        await send_main_menu(update, context)
    elif data == "set_age_calc":
        USER_STATE[query.from_user.id] = "awaiting_age_input"
        await query.message.reply_text(
            "🎂 **Sarkari Age Calculator**\n\nApni Date of Birth aur Form Cutoff Date is format me bhejein:\n\n`DD-MM-YYYY | DD-MM-YYYY`\n\n*Example:* `15-08-2000 | 01-01-2026`",
            parse_mode="Markdown"
        )
    elif data.startswith("set_"):
        mode = data.replace("set_", "")
        USER_STATE[query.from_user.id] = mode
        msg = "📸 **Send your photo now.**" if mode == "photo_50" else "✍️ **Send your signature image.**"
        if mode == "img_pdf":
            msg = "📄 **Send images one by one** for PDF conversion."
        await query.message.reply_text(msg, parse_mode="Markdown")
    elif data == "make_pdf":
        await convert_to_pdf_callback(update, context)
    elif data == "start_quiz":
        await start_quiz_handler(update, context)
    elif data.startswith("ans_"):
        await quiz_answer_handler(update, context)
    elif data == "show_leaderboard":
        await leaderboard_handler(update, context)
    else:
        await menu_callback_handler(update, context)

async def post_init(application):
    await init_db()

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("broadcast", broadcast_command))
    app.add_handler(CommandHandler("add_job", add_job_command))
    
    app.add_handler(CallbackQueryHandler(callback_router))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo_upload))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_handler))

    print("🤖 Sarkari Bot is up & running...")
    app.run_polling()
