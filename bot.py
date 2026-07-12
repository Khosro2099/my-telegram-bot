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

if not all([TELEGRAM_BOT_TOKEN, OLLAMA_API_KEY, RENDER_EXTERNAL_URL]):
    raise ValueError("لطفاً تمام متغیرهای محیطی را تنظیم کنید")

os.environ['OLLAMA_API_KEY'] = OLLAMA_API_KEY

from ollama import chat

# ساخت Flask app
app = Flask(__name__)

# ساخت Telegram Application
application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("سلام! 👋 من ربات هوش مصنوعی هستم.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("هر سوالی داری بپرس!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    logger.info(f"پیام از کاربر: {user_message}")
    
    await update.message.reply_chat_action(action='typing')
    
    try:
        response = chat(
            model='glm-5.2:cloud',
            messages=[{'role': 'user', 'content': user_message}],
        )
        await update.message.reply_text(response.message.content)
    except Exception as e:
        logger.error(f"خطا: {str(e)}")
        await update.message.reply_text("خطایی رخ داد.")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"خطا: {context.error}")

# اضافه کردن Handlerها
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
application.add_error_handler(error_handler)

@app.route('/webhook', methods=['POST'])
def webhook():
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
    return '🤖 ربات فعال است!'

@app.route('/health')
def health():
    return jsonify({"status": "healthy"}), 200

async def setup_webhook_async():
    """تابع async برای تنظیم webhook"""
    webhook_url = f"{RENDER_EXTERNAL_URL}/webhook"
    logger.info(f"در حال تنظیم webhook به آدرس: {webhook_url}")
    
    await application.bot.delete_webhook(drop_pending_updates=True)
    success = await application.bot.set_webhook(webhook_url)
    
    if success:
        logger.info(f"✅ Webhook با موفقیت تنظیم شد: {webhook_url}")
    else:
        logger.error("❌ خطا در تنظیم webhook")

def main():
    # اجرای تابع async برای تنظیم webhook
    asyncio.run(setup_webhook_async())
    
    # اجرای Flask server
    port = int(os.environ.get('PORT', 10000))
    logger.info(f"سرور روی پورت {port} شروع به کار کرد")
    app.run(host='0.0.0.0', port=port, debug=False)

if __name__ == '__main__':
    main()
