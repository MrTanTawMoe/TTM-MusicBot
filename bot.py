import os
import logging
import yt_dlp
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

# Logging သတ်မှတ်ခြင်း
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot စတင်သည့်အခါ ပြမည့် Start Command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    welcome_message = (
        f"မင်္ဂလာပါ {user_name}!\n\n"
        "ကျွန်တော်ကတော့ **No-Video Music Bot** ဖြစ်ပါတယ်။ "
        "YouTube သို့မဟုတ် Music လင့်ခ်တစ်ခု ပို့လိုက်ရုံနဲ့ MP3 အသံဖိုင်သက်သက် ပြန်ထုတ်ပေးပါမယ်။"
    )
    await update.message.reply_text(welcome_message, parse_mode="Markdown")

# လင့်ခ်လက်ခံပြီး Audio ပြန်ပို့မည့် Function
async def download_music(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    
    # URL ဟုတ်မဟုတ် စစ်ဆေးခြင်း
    if not url.startswith("http"):
        await update.message.reply_text("ကျေးဇူးပြု၍ မှန်ကန်သော YouTube လင့်ခ် (URL) တစ်ခု ပို့ပေးပါ။")
        return

    msg = await update.message.reply_text("🎵 သီချင်းကို ရှာဖွေနေပါပြီ၊ ခဏစောင့်ပါ...")

    output_template = "song.%(ext)s"
    
    # yt-dlp Configuration (Audio သက်သက် MP3 ဖြင့် Download ရန်)
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
            # Extension ကို mp3 သို့ ပြောင်းရန်
            mp3_file = os.path.splitext(filename)[0] + ".mp3"

        await msg.edit_text("📤 Telegram ဆီသို့ ပို့ဆောင်နေပါပြီ...")

        # Telegram သို့ Audio ပို့ခြင်း
        with open(mp3_file, 'rb') as audio:
            await update.message.reply_audio(
                audio=audio,
                title=info.get('title', 'Unknown Title'),
                performer=info.get('uploader', 'Unknown Artist')
            )

        # ပို့ပြီးပါက Server ပေါ်မှ ဖိုင်ကို ဖျက်ပစ်ရန်
        if os.path.exists(mp3_file):
            os.remove(mp3_file)
            
        await msg.delete()

    except Exception as e:
        logger.error(f"Error: {e}")
        await msg.edit_text("❌ သီချင်းဒေါင်းလုဒ်လုပ်ရာတွင် အမှားအယွင်းရှိသွားပါသည်။ လင့်ခ်မှန်မမှန် ပြန်စစ်ပါ။")

def main():
    # Render Environment Variable မှ Bot Token ကို ယူမည်
    TOKEN = os.environ.get("BOT_TOKEN")
    
    if not TOKEN:
        print("Error: BOT_TOKEN environment variable not set!")
        return

    application = ApplicationBuilder().token(TOKEN).build()

    # Handlers များ ထည့်သွင်းခြင်း
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), download_music))

    print("Bot is running...")
    application.run_polling()

if __name__ == '__main__':
    main()