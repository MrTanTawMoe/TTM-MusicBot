import os
import logging
import threading
from flask import Flask
import yt_dlp
from telegram import Update, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, InlineQueryHandler, filters

# Logging သတ်မှတ်ခြင်း
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 1. UptimeRobot အတွက် Flask Web Server
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
        "ဒီဘော့က SoundCloud ကနေ သီချင်းနာမည်ရိုက်ထည့်ပြီး ရှာဖွေ MP3 ယူနိုင်ပါပြီ။\n\n"
        "🔎 **အသုံးပြုပုံ:**\n"
        "• Chat ထဲမှာ သီချင်းနာမည် (သို့) SoundCloud လင့်ခ် တိုက်ရိုက်ပို့နိုင်ပါတယ်။"
    )
    await update.message.reply_text(welcome_message, parse_mode="Markdown")

# Inline Search (SoundCloud ဖြင့် ရှာရန် scsearch သုံးထားသည်)
async def inline_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query
    if not query:
        return

    results = []
    ydl_opts = {
        'default_search': 'scsearch5',
        'quiet': True,
        'extract_flat': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            search_results = ydl.extract_info(query, download=False)
            if 'entries' in search_results:
                for idx, entry in enumerate(search_results['entries']):
                    track_url = entry.get('url') or f"https://soundcloud.com/{entry.get('id')}"
                    title = entry.get('title', 'Unknown Title')
                    duration = entry.get('duration', 0)
                    thumbnail = entry.get('thumbnail', '')

                    results.append(
                        InlineQueryResultArticle(
                            id=str(idx),
                            title=title,
                            description=pformat_duration(duration),
                            thumbnail_url=thumbnail,
                            input_message_content=InputTextMessageContent(track_url)
                        )
                    )
        await update.inline_query.answer(results, cache_time=1)
    except Exception as e:
        logger.error(f"Inline search error: {e}")

def pformat_duration(seconds):
    if not seconds:
        return ""
    m, s = divmod(seconds, 60)
    return f"Duration: {m}:{s:02d}"

# မက်ဆေ့ခ်ျ လက်ခံပြီး SoundCloud မှ သီချင်းဒေါင်းရန်
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    
    if text.startswith("http"):
        url = text
    else:
        url = f"scsearch1:{text}"

    msg = await update.message.reply_text("🎵 SoundCloud မှ သီချင်းကို ရှာဖွေနေပါပြီ၊ ခဏစောင့်ပါ...")

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
            if 'entries' in info:
                info = info['entries'][0]
            
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
        await msg.edit_text("❌ သီချင်းဒေါင်းလုဒ်လုပ်ရာတွင် အမှားအယွင်းရှိသွားပါသည်။ နာမည် သို့မဟုတ် လင့်ခ်မှန်မမှန် ပြန်စစ်ပါ။")

def main():
    TOKEN = os.environ.get("BOT_TOKEN")
    if not TOKEN:
        print("Error: BOT_TOKEN environment variable not set!")
        return

    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    application = ApplicationBuilder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(InlineQueryHandler(inline_search))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    print("Bot is running with SoundCloud backend...")
    application.run_polling()

if __name__ == '__main__':
    main()
