import os
import json
import logging
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
        f"Menga **video** yoki **fayl (document)** ko‘rinishidagi kinoni yuboring. Men avtomatik 3 xonali kod biriktiraman va kanalga joylayman.\n"
        f"Agar biror kodni qayta ishlatmoqchi bo‘lsangiz, /reset 007 deb yozing.\n\n"
        f"📊 Ishlatilgan kodlar: {used_codes_count} / 999"
    )

# ==================== KODNI QAYTA ISHLATISH (RESET) ====================
async def reset_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ALLOWED_USERS:
        await update.message.reply_text("❌ Kechirasiz, bu buyruq faqat adminlar uchun.")
        return

    args = context.args
    if not args or len(args) != 1:
        await update.message.reply_text("❌ Iltimos, bitta 3 xonali kod yozing. Masalan: /reset 007")
        return

    code = args[0].strip()
    if not (code.isdigit() and len(code) == 3):
        await update.message.reply_text("❌ Kod 3 xonali son bo‘lishi kerak.")
        return

    used = load_used_codes()
    if code in used:
        used.remove(code)
        save_used_codes(used)
        await update.message.reply_text(f"✅ {code} kodi qayta ishlatish uchun bo‘shatildi.")
    else:
        await update.message.reply_text(f"❌ {code} kodi ishlatilmagan yoki mavjud emas.")

# ==================== VIDEO/FILE QABUL QILISH ====================
async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ALLOWED_USERS:
        return

    video = update.message.video
    document = update.message.document

    # Video yoki document (video fayl) ekanligini tekshirish
    if not video and not (document and document.mime_type and document.mime_type.startswith('video/')):
        await update.message.reply_text("❌ Iltimos, video yoki video fayl yuboring.")
        return

    try:
        code = get_next_code()
    except Exception as e:
        await update.message.reply_text(f"❌ {str(e)}")
        return

    status_msg = await update.message.reply_text("⏳ Kino kanalga joylanmoqda...")

    try:
        # Video yoki document sifatida yuborish
        if video:
            sent = await context.bot.send_video(
                chat_id=CHANNEL_ID,
                video=video.file_id,
                caption=f"Kino: {video.file_name if video.file_name else 'Video'}\nKOD {code}"
            )
        else:  # document (video fayl)
            sent = await context.bot.send_document(
                chat_id=CHANNEL_ID,
                document=document.file_id,
                caption=f"Kino: {document.file_name if document.file_name else 'Video'}\nKOD {code}"
            )

        mark_code_used(code)

        channel_username = "moviysky"
        post_url = f"https://t.me/{channel_username}/{sent.message_id}"
        used_count = len(load_used_codes())
        await update.message.reply_text(
            f"✅ Kino kanalga joylandi!\n\n"
            f"📌 Kod: `{code}`\n"
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
    app.add_handler(CommandHandler("reset", reset_code))
    # Video va video documentlarni qabul qilish
    app.add_handler(MessageHandler(
        filters.VIDEO | filters.Document.VIDEO,
        handle_media
    ))
    print("🤖 Admin bot (video + document) ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()

