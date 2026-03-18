import os
import json
import logging
import re
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, CommandHandler, ContextTypes

# ==================== SOZLAMALAR ====================
BOT_TOKEN = "8257415857:AAE9_vt6SpFFgVPr60eU0ab7jtwd5eXtK1I"
CHANNEL_ID = -1003706461270
ALLOWED_USERS = [
    824355333,
    999656577,
]
COUNTER_FILE = "code_counter.json"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== KOD HISOBLAGICH ====================
def load_used_codes():
    try:
        with open(COUNTER_FILE, "r") as f:
            return set(json.load(f))
    except FileNotFoundError:
        return set()

def save_used_codes(codes):
    with open(COUNTER_FILE, "w") as f:
        json.dump(list(codes), f)

def get_next_code():
    used = load_used_codes()
    for i in range(1, 1000):
        code = f"{i:03d}"
        if code not in used:
            return code
    raise Exception("❌ Barcha 999 ta kod ishlatilgan! Yangi kino qo'shib bo'lmaydi.")

def mark_code_used(code):
    used = load_used_codes()
    used.add(code)
    save_used_codes(used)

# ==================== START KOMANDASI ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ALLOWED_USERS:
        await update.message.reply_text("❌ Kechirasiz, bu bot faqat ruxsat etilgan adminlar uchun.")
        return
    used_codes_count = len(load_used_codes())
    await update.message.reply_text(
        f"👋 Xush kelibsiz, admin!\n\n"
        f"Menga **video fayl** yuboring. Men:\n"
        f"1️⃣ Video faylni qabul qilaman\n"
        f"2️⃣ Takrorlanmas 3 xonali kod biriktiraman (001-999)\n"
        f"3️⃣ Videoni kanalga **fayl (document)** sifatida joylayman (2 GB gacha)\n\n"
        f"📊 Ishlatilgan kodlar: {used_codes_count} / 999"
    )

# ==================== VIDEO FAYLNI QABUL QILISH ====================
async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ALLOWED_USERS:
        return

    # Video yoki hujjat kelganini tekshirish
    video = update.message.video
    document = update.message.document
    if not video and not document:
        await update.message.reply_text("❌ Iltimos, video fayl yuboring.")
        return

    # 1. Yangi kod olish
    try:
        code = get_next_code()
    except Exception as e:
        await update.message.reply_text(f"❌ {str(e)}")
        return

    # 2. Kanalga joylash uchun faylni olish
    status_msg = await update.message.reply_text("⏳ Video kanalga joylanmoqda...")

    try:
        if video:
            # Video faylni olish
            file_id = video.file_id
            sent = await context.bot.send_video(
                chat_id=CHANNEL_ID,
                video=file_id,
                caption=f"Kino: {video.file_name if hasattr(video, 'file_name') else 'Video'}\nKOD {code}"
            )
        elif document and document.mime_type and document.mime_type.startswith('video/'):
            # Video hujjat sifatida kelgan bo'lsa
            file_id = document.file_id
            sent = await context.bot.send_document(
                chat_id=CHANNEL_ID,
                document=file_id,
                caption=f"Kino: {document.file_name}\nKOD {code}"
            )
        else:
            await update.message.reply_text("❌ Bu video fayl emas.")
            return

        # Kodni ishlatilgan deb belgilash
        mark_code_used(code)

        # Admin ga xabar
        channel_username = "moviysky"
        post_url = f"https://t.me/{channel_username}/{sent.message_id}"
        used_count = len(load_used_codes())
        await update.message.reply_text(
            f"✅ Kino kanalga joylandi!\n\n"
            f"📌 Kod: `{code}` (takrorlanmas)\n"
            f"📊 Ishlatilgan kodlar: {used_count} / 999\n\n"
            f"🔗 Post: {post_url}",
            parse_mode="Markdown"
        )

    except Exception as e:
        logger.error(f"Kanalga joylashda xatolik: {e}")
        await update.message.reply_text(f"❌ Xatolik yuz berdi: {e}")

# ==================== ASOSIY ====================
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    # Faqat video va video hujjatlarini qabul qilish
    app.add_handler(MessageHandler(
        filters.VIDEO | filters.Document.VIDEO,
        handle_video
    ))
    print("🤖 Admin bot (faqat video qabul qiladi) ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()

