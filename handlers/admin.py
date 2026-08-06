import asyncio
from telegram import Update
from telegram.ext import ContextTypes
from config import ADMIN_ID
from database import get_all_users, save_job
from handlers.tools import shorten_link

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    
    msg_text = " ".join(context.args)
    if not msg_text:
        await update.message.reply_text("Usage: `/broadcast Your message here`", parse_mode="Markdown")
        return

    users = await get_all_users()
    count = 0
    await update.message.reply_text(f"🚀 Broadcasting message to {len(users)} users...")
    
    for uid in users:
        try:
            await context.bot.send_message(chat_id=uid, text=msg_text, parse_mode="Markdown")
            count += 1
            await asyncio.sleep(0.05)
        except Exception:
            pass

    await update.message.reply_text(f"✅ Broadcast sent successfully to {count} users!")

async def add_job_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
        
    full_text = " ".join(context.args)
    try:
        title, date, link = [x.strip() for x in full_text.split("|")]
        
        # Monetize link automatically via GPLinks API
        monetized_link = await shorten_link(link)
        await save_job(title, date, monetized_link)
        
        users = await get_all_users()
        job_msg = f"🔔 **NEW JOB ALERT!**\n\n📌 **Post:** {title}\n📅 **Last Date:** {date}\n🔗 **Apply Link:** {monetized_link}"
        
        for uid in users:
            try:
                await context.bot.send_message(chat_id=uid, text=job_msg, parse_mode="Markdown")
            except Exception:
                pass
                
        await update.message.reply_text("✅ Job alert added & broadcasted with GPLink successfully!")
    except ValueError:
        await update.message.reply_text("❌ Format: `/add_job Title | Last Date | Apply Link`", parse_mode="Markdown")
