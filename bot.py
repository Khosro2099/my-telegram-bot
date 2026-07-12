import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# تنظیم لاگینگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# دریافت توکن‌ها از Environment Variables
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
OLLAMA_API_KEY = os.getenv('OLLAMA_API_KEY')

# بررسی وجود توکن‌ها
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("لطفاً متغیر محیطی TELEGRAM_BOT_TOKEN را تنظیم کنید")
if not OLLAMA_API_KEY:
    raise ValueError("لطفاً متغیر محیطی OLLAMA_API_KEY را تنظیم کنید")

# تنظیم API Key برای Ollama
os.environ['OLLAMA_API_KEY'] = OLLAMA_API_KEY

from ollama import chat

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور /start"""
    await update.message.reply_text(
        "سلام! 👋\n"
        "من یک ربات هوش مصنوعی هستم.\n"
        "هر سوالی داری بپرس، من با استفاده از مدل GLM-5.2 بهت پاسخ میدم!"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور /help"""
    await update.message.reply_text(
        "📝 راهنما:\n\n"
        "• هر پیامی بنویسی، من بهش پاسخ میدم\n"
        "• می‌تونی به فارسی یا انگلیسی سوال بپرسی\n"
        "• برای شروع مجدد از دستور /start استفاده کن"
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
        logger.info(f"پاسخ AI: {ai_response[:100]}...")
        
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
            "یک خطای غیرمنتظره رخ داد. لطفاً بعداً دوباره تلاش کنید."
        )

def main():
    """تابع اصلی اجرای ربات"""
    logger.info("ربات در حال شروع است...")
    
    # ساخت Application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # اضافه کردن Handlerها
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # اضافه کردن error handler
    application.add_error_handler(error_handler)
    
    # شروع ربات
    logger.info("ربات شروع به کار کرد!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()