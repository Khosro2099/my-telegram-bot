import os
import logging
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from flask import Flask, request, jsonify

# ۱. تنظیمات لاگینگ برای دیدن جزئیات خطاها
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ۲. دریافت متغیرهای محیطی
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
OLLAMA_API_KEY = os.getenv('OLLAMA_API_KEY')
RENDER_EXTERNAL_URL = os.getenv('RENDER_EXTERNAL_URL')

if not all([TELEGRAM_BOT_TOKEN, OLLAMA_API_KEY, RENDER_EXTERNAL_URL]):
    raise ValueError("لطفاً متغیرهای TELEGRAM_BOT_TOKEN, OLLAMA_API_KEY و RENDER_EXTERNAL_URL را در Render تنظیم کنید.")

# تنظیم کلید API برای کتابخانه Ollama
os.environ['OLLAMA_API_KEY'] = OLLAMA_API_KEY

from ollama import chat

# ۳. ساخت اپلیکیشن‌ها
app = Flask(__name__)
application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

# ۴. هندلرهای ربات
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("سلام! 👋 من ربات هوش مصنوعی هستم. چطور می‌تونم کمکت کنم؟")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("هر متنی بنویسی، من با هوش مصنوعی بهت پاسخ میدم.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    logger.info(f"🔵 پیام دریافت شد از کاربر {update.message.from_user.id}: {user_message}")
    
    try:
        # نمایش وضعیت تایپ کردن
        await update.message.reply_chat_action(action='typing')
        
        # فراخوانی مدل هوش مصنوعی
        # نکته: اگر مدل glm-5.2:cloud کار نکرد، نام مدل را از داکیومنت Ollama چک کن
        logger.info("⏳ در حال ارسال درخواست به Ollama...")
        
        response = chat(
            model='glm-5.2:cloud', 
            messages=[{'role': 'user', 'content': user_message}],
        )
        
        ai_response = response.message.content
        logger.info(f"🟢 پاسخ دریافت شد: {ai_response[:100]}...")
        
        # ارسال پاسخ به کاربر
        await update.message.reply_text(ai_response)
        
    except Exception as e:
        logger.error(f"🔴 خطای رخ داده: {type(e).__name__} - {str(e)}", exc_info=True)
        await update.message.reply_text("متأسفانه خطایی در برقراری ارتباط با هوش مصنوعی رخ داد.")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"خطای کلی در ربات: {context.error}")

# اضافه کردن هندلرها به اپلیکیشن
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
application.add_error_handler(error_handler)

# ۵. اندپوینت‌های Flask
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        update = Update.de_json(request.get_json(force=True), application.bot)
        asyncio.run(application.process_update(update))
        return jsonify({"status": "ok"})
    except Exception as e:
        logger.error(f"خطا در پردازش وب‌هوک: {e}")
        return jsonify({"status": "error"}), 500

@app.route('/')
def home():
    return '🤖 ربات تلگرام با هوش مصنوعی فعال است!'

@app.route('/health')
def health():
    return jsonify({"status": "healthy"}), 200

# ۶. تابع اصلی راه‌اندازی
async def setup_and_run():
    # مقداردهی اولیه اجباری برای نسخه‌های جدید python-telegram-bot
    await application.initialize()
    
    webhook_url = f"{RENDER_EXTERNAL_URL}/webhook"
    logger.info(f"در حال تنظیم Webhook روی آدرس: {webhook_url}")
    
    # حذف وب‌هوک قبلی و تنظیم جدید
    await application.bot.delete_webhook(drop_pending_updates=True)
    success = await application.bot.set_webhook(webhook_url)
    
    if success:
        logger.info("✅ Webhook با موفقیت ست شد.")
    else:
        logger.error("❌ خطا در تنظیم Webhook")

    # اجرای سرور Flask
    port = int(os.environ.get('PORT', 10000))
    logger.info(f"🚀 سرور روی پورت {port} اجرا شد.")
    app.run(host='0.0.0.0', port=port, debug=False)

if __name__ == '__main__':
    asyncio.run(setup_and_run())
