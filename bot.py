import telebot
import os
import time
import threading

# دریافت توکن از تنظیمات رندر
TOKEN = os.environ.get('BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)

# آیدی عددی کاربر هدف
TARGET_USER_ID = 8807702626

# تابع ارسال پیام هر ۲۰ دقیقه
def send_periodic_message():
    while True:
        try:
            bot.send_message(TARGET_USER_ID, "🔔 سلام! این پیام هر ۲۰ دقیقه برای شما ارسال می‌شود.")
            print("✅ پیام ارسال شد.")
        except Exception as e:
            print(f"❌ خطا: {e}")
        time.sleep(1200) # ۱۲۰۰ ثانیه = ۲۰ دقیقه

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "ربات روشن است! 🤖")

if __name__ == '__main__':
    threading.Thread(target=send_periodic_message, daemon=True).start()
    bot.infinity_polling()