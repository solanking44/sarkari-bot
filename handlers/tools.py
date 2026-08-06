import io
import urllib.parse
import httpx
from datetime import datetime
from PIL import Image
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import GPLINKS_API

USER_STATE = {}
USER_IMAGES = {}

async def shorten_link(url: str) -> str:
    if not GPLINKS_API:
        return url
    try:
        api_url = f"https://gplinks.in/api?api={GPLINKS_API}&url={urllib.parse.quote(url)}"
        async with httpx.AsyncClient() as client:
            res = await client.get(api_url)
            data = res.json()
            if data.get("status") == "success":
                return data.get("shortenedUrl", url)
    except Exception:
        pass
    return url

async def compress_image(image_bytes: bytes, target_kb: int) -> io.BytesIO:
    img = Image.open(io.BytesIO(image_bytes))
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    quality = 90
    output = io.BytesIO()
    max_dim = 1000 if target_kb == 50 else 600
    img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
    
    while quality > 10:
        output.seek(0)
        output.truncate()
        img.save(output, format='JPEG', quality=quality, optimize=True)
        if output.tell() <= target_kb * 1024:
            break
        quality -= 5
        
    output.seek(0)
    return output

async def calculate_age(dob_str: str, cutoff_str: str):
    dob = datetime.strptime(dob_str, "%d-%m-%Y")
    cutoff = datetime.strptime(cutoff_str, "%d-%m-%Y")
    
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

async def handle_photo_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    mode = USER_STATE.get(user_id)
    
    if not mode:
        return

    photo_file = await update.message.photo[-1].get_file()
    img_bytes = await photo_file.download_as_bytearray()

    if mode in ['photo_50', 'sig_20']:
        target_kb = 50 if mode == 'photo_50' else 20
        status_msg = await update.message.reply_text("⏳ Compressing image...")
        
        compressed_io = await compress_image(img_bytes, target_kb)
        filename = "photo_compressed.jpg" if mode == 'photo_50' else "signature_compressed.jpg"
        
        await update.message.reply_document(
            document=compressed_io,
            filename=filename,
            caption=f"✅ Compressed successfully (<{target_kb}KB)"
        )
        await status_msg.delete()
        USER_STATE[user_id] = None

    elif mode == 'img_to_pdf':
        if user_id not in USER_IMAGES:
            USER_IMAGES[user_id] = []
        
        img = Image.open(io.BytesIO(img_bytes)).convert('RGB')
        USER_IMAGES[user_id].append(img)
        
        keyboard = [[InlineKeyboardButton("📄 Convert to PDF Now", callback_data="make_pdf")]]
        await update.message.reply_text(
            f"📸 Image {len(USER_IMAGES[user_id])} received! Aur images bhejein ya PDF banayein.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def convert_to_pdf_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    images = USER_IMAGES.get(user_id, [])
    if not images:
        await query.message.reply_text("❌ Koi image upload nahi hui!")
        return

    pdf_io = io.BytesIO()
    images[0].save(pdf_io, format='PDF', save_all=True, append_images=images[1:])
    pdf_io.seek(0)
    
    await context.bot.send_document(
        chat_id=user_id,
        document=pdf_io,
        filename="Converted_Document.pdf",
        caption="✅ Complete PDF Ready!"
    )
    USER_IMAGES[user_id] = []
    USER_STATE[user_id] = None
