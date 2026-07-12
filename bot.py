import os
import logging
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from flask import Flask, request, jsonify

# تنظیم لاگینگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# دریافت توکن‌ها از Environment Variables
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
OLLAMA_API_KEY = os.getenv('OLLAMA_API_KEY')
RENDER_EXTERNAL_URL = os.getenv('RENDER_EXTERNAL_URL')

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("لطفاً متغیر محیطی TELEGRAM_BOT_TOKEN را تنظیم کنید")
if not OLLAMA_API_KEY:
    raise ValueError("لطفاً متغیر محیطی OLLAMA_API_KEY را تنظیم کنید")
if not RENDER_EXTERNAL_URL:
    raise ValueError("لطفاً متغیر محیطی RENDER_EXTERNAL_URL را تنظیم کنید")

# تنظیم API Key برای Ollama
os.environ['OLLAMA_API_KEY'] = OLLAMA_API_KEY

from ollama import chat

# ساخت Flask app
app = Flask(__name__)

# ساخت Telegram Application
application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور /start"""
    await update.message.reply_text(
        "سلام! 👋\n"
        "من یک ربات هوش مصنوعی هستم.\n"
        "هر سوالی داری بپرس!"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور /help"""
    await update.message.reply_text(
        "📝 راهنما:\n\n"
        "• هر پیامی بنویسی، من بهش پاسخ میدم\n"
        "• می‌تونی به فارسی یا انگلیسی سوال بپرسی"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پردازش پیام‌های متنی"""
    user_message = update.message.text
    user_id = update.message.from_user.id
    
    logger.info(f"پیام از کاربر {user_id}: {user_message}")
    
    # ارسال پیام "در حال تایپ..."
    await update.message.reply_chat_action(action='typing')
    
    try:
        # فراخوانی API Ollama
        response = chat(
            model='glm-5.2:cloud',
            messages=[{'role': 'user', 'content': user_message}],
        )
        
        ai_response = response.message.content
        logger.info(f"پاسخ AI دریافت شد")
        
        # ارسال پاسخ
        await update.message.reply_text(ai_response)
        
    except Exception as e:
        logger.error(f"خطا در پردازش پیام: {str(e)}")
        await update.message.reply_text(
            "متأسفانه خطایی رخ داد. لطفاً دوباره تلاش کنید."
        )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت خطاها"""
    logger.error(f"خطا: {context.error}")
    if update and update.message:
        await update.message.reply_text(
            "یک خطای غیرمنتظره رخ داد."
        )

# اضافه کردن Handlerها
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
application.add_error_handler(error_handler)

@app.route('/webhook', methods=['POST'])
def webhook():
    """Endpoint برای دریافت webhook از تلگرام"""
    try:
        update = Update.de_json(request.get_json(force=True), application.bot)
        # اجرای async در synchronous context
        asyncio.run(application.process_update(update))
        return jsonify({"status": "ok"})
    except Exception as e:
        logger.error(f"خطا در webhook: {str(e)}")
        return jsonify({"status": "error"}), 500

@app.route('/')
def home():
    """صفحه اصلی برای بررسی وضعیت ربات"""
    return '🤖 ربات تلگرام با هوش مصنوعی فعال است!'

@app.route('/health')
def health():
    """بررسی سلامت سرویس"""
    return jsonify({"status": "healthy"}), 200

def set_webhook():
    """تنظیم webhook روی سرور تلگرام"""
    webhook_url = f"{RENDER_EXTERNAL_URL}/webhook"
    logger.info(f"در حال تنظیم webhook به آدرس: {webhook_url}")
    
    # حذف webhook قبلی اگر وجود داشته باشه
    application.bot.delete_webhook(drop_pending_updates=True)
    
    # تنظیم webhook جدید
    success = application.bot.set_webhook(webhook_url)
    
    if success:
        logger.info(f"✅ Webhook با موفقیت تنظیم شد: {webhook_url}")
    else:
        logger.error("❌ خطا در تنظیم webhook")

if __name__ == '__main__':
    # تنظیم webhook
    set_webhook()
    
    # اجرای Flask server
    port = int(os.environ.get('PORT', 10000))
    logger.info(f"سرور روی پورت {port} شروع به کار کرد")
    app.run(host='0.0.0.0', port=port, debug=False)