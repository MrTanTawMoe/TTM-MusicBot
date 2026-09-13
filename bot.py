import os
import logging
import asyncio
import threading
from flask import Flask
import yt_dlp
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

# Logging သတ်မှတ်ခြင်း
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 1. UptimeRobot အတွက် Flask Web Server တည်ဆောက်ခြင်း
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is alive and running!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


# 2. Telegram Bot Logic များ
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    welcome_message = (
        f"မင်္ဂလာပါ {user_name}!\n\n"
        "ကျွန်တော်ကတော့ **No-Video Music Bot** ဖြစ်ပါတယ်။ "
        "YouTube သို့မဟုတ် Music လင့်ခ်တစ်ခု ပို့လိုက်ရုံနဲ့ MP3 အသံဖိုင်သက်သက် ပြန်ထုတ်ပေးပါမယ်။"
    )
    await update.message.reply_text(welcome_message, parse_mode="Markdown")

async def download_music(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    
    if not url.startswith("http"):
        await update.message.reply_text("ကျေးဇူးပြု၍ မှန်ကန်သော YouTube လင့်ခ် (URL) တစ်ခု ပို့ပေးပါ။")
        return

    msg = await update.message.reply_text("🎵 သီချင်းကို ရှာဖွေနေပါပြီ၊ ခဏစောင့်ပါ...")
    output_template = "song.%(ext)s"
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': output_template,
        'quiet': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            mp3_file = os.path.splitext(filename)[0] + ".mp3"

        await msg.edit_text("📤 Telegram ဆီသို့ ပို့ဆောင်နေပါပြီ...")

        with open(mp3_file, 'rb') as audio:
            await update.message.reply_audio(
                audio=audio,
                title=info.get('title', 'Unknown Title'),
                performer=info.get('uploader', 'Unknown Artist')
            )

        if os.path.exists(mp3_file):
            os.remove(mp3_file)
            
        await msg.delete()

    except Exception as e:
        logger.error(f"Error: {e}")
        await msg.edit_text("❌ သီချင်းဒေါင်းလုဒ်လုပ်ရာတွင် အမှားအယွင်းရှိသွားပါသည်။ လင့်ခ်မှန်မမှန် ပြန်စစ်ပါ။")

def main():
    TOKEN = os.environ.get("BOT_TOKEN")
    if not TOKEN:
        print("Error: BOT_TOKEN environment variable not set!")
        return

    # Flask ကို Thread သီးသန့်နဲ့ စတင်ရန် (Render က Web Service အတွက် Port တောင်းဆိုလို့ပါ)
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # Telegram Bot ကို စတင်ရန်
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), download_music))

    print("Bot is running with web server...")
    application.run_polling()

if __name__ == '__main__':
    main()
