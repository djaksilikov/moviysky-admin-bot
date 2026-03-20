import os
import json
import logging
import subprocess
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, CommandHandler, ContextTypes
import yt_dlp

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

# ==================== VIDEO FORMATINI ANIQLASH ====================
def get_video_resolution(filepath):
    """ffprobe yordamida video balandligini (height) qaytaradi"""
    try:
        cmd = [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=height", "-of", "default=noprint_wrappers=1:nokey=1",
            filepath
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        height = result.stdout.strip()
        if height.isdigit():
            return f"{height}p"
        else:
            return "unknown"
    except Exception as e:
        logger.error(f"Format aniqlashda xatolik: {e}")
        return "unknown"

# ==================== VIDEO YUKLAB OLISH (SIQMASDAN) ====================
async def download_video(url):
    ydl_opts = {
        'format': 'best',                         # Eng yaxshi sifat (siqilmaydi)
        'outtmpl': 'downloads/%(title)s.%(ext)s', # Saqlash joyi
        'merge_output_format': 'mp4',              # MP4 formatida birlashtirish
        'quiet': True,
        'no_warnings': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            return filename, info.get('title', 'Video')
    except Exception as e:
        logger.error(f"Yuklab olishda xatolik: {e}")
        return None, str(e)

# ==================== START KOMANDASI ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ALLOWED_USERS:
        await update.message.reply_text("❌ Kechirasiz, bu bot faqat ruxsat etilgan adminlar uchun.")
        return
    used_codes_count = len(load_used_codes())
    await update.message.reply_text(
        f"👋 Xush kelibsiz, admin!\n\n"
        f"Menga **video** (havola yoki fayl) yuboring. Men:\n"
        f"1️⃣ Videoni eng yaxshi sifatda yuklab olaman\n"
        f"2️⃣ Takrorlanmas 3 xonali kod biriktiraman (001-999)\n"
        f"3️⃣ Video formatini avtomatik aniqlayman (480p, 720p …)\n"
        f"4️⃣ Kinoni kanalga joylayman\n\n"
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

# ==================== VIDEO/HAVOLANI QABUL QILISH ====================
async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ALLOWED_USERS:
        return

    # 1. Agar havola bo‘lsa
    if update.message.text and update.message.text.startswith(('http://', 'https://')):
        url = update.message.text.strip()
        status_msg = await update.message.reply_text("⏳ Video yuklab olinmoqda...")

        filepath, title = await download_video(url)
        if not filepath:
            await status_msg.edit_text(f"❌ Yuklab olishda xatolik: {title}")
            return

        await status_msg.edit_text("✅ Video yuklab olindi. Kanalga joylanmoqda...")

        # Format aniqlash
        resolution = get_video_resolution(filepath)

        # Yangi kod olish
        try:
            code = get_next_code()
        except Exception as e:
            await update.message.reply_text(f"❌ {str(e)}")
            # vaqtinchalik faylni o‘chirish
            if os.path.exists(filepath):
                os.remove(filepath)
            return

        # Kanalga document sifatida yuborish (2 GB gacha, sifat saqlanadi)
        try:
            with open(filepath, 'rb') as f:
                sent = await context.bot.send_document(
                    chat_id=CHANNEL_ID,
                    document=f,
                    caption=f"Kino: {title}\nKOD {code} ({resolution})"
                )

            mark_code_used(code)

            channel_username = "moviysky"
            post_url = f"https://t.me/{channel_username}/{sent.message_id}"
            used_count = len(load_used_codes())
            await update.message.reply_text(
                f"✅ Kino kanalga joylandi!\n\n"
                f"📌 Kod: `{code}`\n"
                f"🎚 Sifat: {resolution}\n"
                f"📊 Ishlatilgan kodlar: {used_count} / 999\n\n"
                f"🔗 Post: {post_url}",
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Kanalga joylashda xatolik: {e}")
            await update.message.reply_text(f"❌ Xatolik yuz berdi: {e}")
        finally:
            # Vaqtinchalik faylni o‘chirish
            if os.path.exists(filepath):
                os.remove(filepath)

        return

    # 2. Agar video fayl bo‘lsa
    video = update.message.video
    document = update.message.document
    if not video and not (document and document.mime_type and document.mime_type.startswith('video/')):
        await update.message.reply_text("❌ Iltimos, video havolasi yoki video fayl yuboring.")
        return

    # Video fayldan kod olish
    try:
        code = get_next_code()
    except Exception as e:
        await update.message.reply_text(f"❌ {str(e)}")
        return

    # Faylni qabul qilish
    file = video or document
    file_id = file.file_id
    file_name = getattr(file, 'file_name', 'video.mp4')

    status_msg = await update.message.reply_text("⏳ Kanalga joylanmoqda...")

    try:
        # Faylni vaqtinchalik yuklab olib, formatni aniqlash uchun (ixtiyoriy, lekin aniqroq)
        # Agar format aniqlash kerak bo‘lmasa, to‘g‘ridan-to‘g‘ri yuborish mumkin.
        # Bu yerda oddiyroq usul – formatni aniqlash uchun faylni yuklab olmaymiz.
        # Lekin formatni aniqlash uchun faylni yuklab olish kerak. 
        # Soddalik uchun formatni "unknown" qoldiramiz yoki fayldan olish mumkin.
        # Quyida faylni yuklab olib, formatni aniqlaymiz.

        # Faylni vaqtinchalik yuklab olish
        new_file = await context.bot.get_file(file_id)
        file_path = f"downloads/{file_name}"
        await new_file.download_to_drive(file_path)

        # Format aniqlash
        resolution = get_video_resolution(file_path)

        # Kanalga document sifatida yuborish
        with open(file_path, 'rb') as f:
            sent = await context.bot.send_document(
                chat_id=CHANNEL_ID,
                document=f,
                caption=f"Kino: {file_name}\nKOD {code} ({resolution})"
            )

        mark_code_used(code)

        channel_username = "moviysky"
        post_url = f"https://t.me/{channel_username}/{sent.message_id}"
        used_count = len(load_used_codes())
        await update.message.reply_text(
            f"✅ Kino kanalga joylandi!\n\n"
            f"📌 Kod: `{code}`\n"
            f"🎚 Sifat: {resolution}\n"
            f"📊 Ishlatilgan kodlar: {used_count} / 999\n\n"
            f"🔗 Post: {post_url}",
            parse_mode="Markdown"
        )

        # Vaqtinchalik faylni o‘chirish
        if os.path.exists(file_path):
            os.remove(file_path)

    except Exception as e:
        logger.error(f"Kanalga joylashda xatolik: {e}")
        await update.message.reply_text(f"❌ Xatolik yuz berdi: {e}")

# ==================== ASOSIY ====================
def main():
    # Yuklab olish papkasini yaratish
    os.makedirs("downloads", exist_ok=True)

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset_code))
    # Havolalar (matn) va video/documentlarni qabul qilish
    app.add_handler(MessageHandler(
        filters.TEXT | filters.VIDEO | filters.Document.VIDEO,
        handle_media
    ))
    print("🤖 Admin bot (siqilmaydi, format aniqlanadi) ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()

