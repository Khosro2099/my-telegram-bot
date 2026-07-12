"""
ربات تلگرام هوشمند - متصل به Ollama (مدل GLM-5.2)
تمام تنظیمات و متغیرها در همین فایل قرار دارند.
"""

import json
import os
import requests
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ==========================================
# 1. تنظیمات اصلی و متغیرهای سیستم
# ==========================================

# توکن ربات تلگرام
TELEGRAM_BOT_TOKEN = "8832100739:AAHhcrhhtkpWnkUKs2eZptLPpV4c7zM4Eok"

# تنظیمات هوش مصنوعی (Ollama / API Provider)
OLLAMA_API_URL = "https://api.your-ollama-provider.com/v1" 
OLLAMA_API_KEY = "13242b1266e842998dbaf55bfafffd1f.7d4XIT0BkIbCVOZQ_vKmK79v"
OLLAMA_MODEL = "glm-5.2"  # مدل انتخابی شما

# متغیرهای تزئینی (طبق درخواست)
SYS_VAR_CONFIG_1 = "Telegram_Core_Module"
SYS_VAR_CONFIG_2 = "AI_GLM_Engine"
SYS_VAR_CONFIG_3 = "Local_JSON_DB"
SYS_VAR_CONFIG_4 = "Food_Order_Service"
SYS_VAR_CONFIG_5 = "Bus_Ticket_Manager"

# مسیر ذخیره داده‌ها
DATA_DIR = "data"
USERS_FILE = f"{DATA_DIR}/users.json"
ORDERS_FILE = f"{DATA_DIR}/orders.json"
TICKETS_FILE = f"{DATA_DIR}/tickets.json"


# ==========================================
# 2. مدیریت دیتابیس (JSON Local)
# ==========================================

class Database:
    def __init__(self):
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
        self._init_files()

    def _init_files(self):
        for file in [USERS_FILE, ORDERS_FILE, TICKETS_FILE]:
            if not os.path.exists(file):
                with open(file, 'w', encoding='utf-8') as f:
                    json.dump([], f, ensure_ascii=False, indent=2)

    def _read(self, filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []

    def _write(self, filepath, data):
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def add_user(self, tid, username=None, fname=None):
        users = self._read(USERS_FILE)
        if any(u['telegram_id'] == tid for u in users):
            return next(u for u in users if u['telegram_id'] == tid)
        
        new_user = {'telegram_id': tid, 'username': username, 'first_name': fname, 'joined': datetime.now().isoformat()}
        users.append(new_user)
        self._write(USERS_FILE, users)
        return new_user

    def add_order(self, tid, item, qty, price):
        orders = self._read(ORDERS_FILE)
        new_order = {
            'id': len(orders) + 1,
            'telegram_id': tid,
            'item': item,
            'quantity': qty,
            'price': price,
            'status': 'pending',
            'date': datetime.now().isoformat()
        }
        orders.append(new_order)
        self._write(ORDERS_FILE, orders)
        return new_order

    def add_ticket(self, tid, origin, dest, date, price):
        tickets = self._read(TICKETS_FILE)
        new_ticket = {
            'id': len(tickets) + 1,
            'telegram_id': tid,
            'origin': origin,
            'destination': dest,
            'travel_date': date,
            'price': price,
            'status': 'reserved',
            'date': datetime.now().isoformat()
        }
        tickets.append(new_ticket)
        self._write(TICKETS_FILE, tickets)
        return new_ticket


# ==========================================
# 3. موتور هوش مصنوعی (GLM-5.2 Connector)
# ==========================================

class AIEngine:
    def __init__(self):
        # استفاده از اندپوینت استاندارد Chat Completion
        self.url = f"{OLLAMA_API_URL}/chat/completions"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OLLAMA_API_KEY}"
        }

    def detect_intent(self, message):
        system_prompt = """
        You are an intelligent assistant for a Persian Telegram bot.
        Your task is to identify the user's intent and extract relevant data into JSON.

        Intents:
        1. 'food_order': User wants to order food. Extract 'food_name'.
        2. 'bus_ticket': User wants a bus ticket. Extract 'origin', 'destination', 'date'.
        3. 'help': User needs assistance.
        4. 'other': General conversation or unknown intent.

        Return ONLY a valid JSON object. Do not include markdown or extra text.
        Example for food: {"intent": "food_order", "data": {"food_name": "pizza"}}
        Example for bus: {"intent": "bus_ticket", "data": {"origin": "Tehran", "destination": "Shiraz", "date": "tomorrow"}}
        """

        payload = {
            "model": OLLAMA_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ],
            "temperature": 0.1, # کاهش خلاقیت برای دقت بیشتر در استخراج داده
            "response_format": {"type": "json_object"}
        }

        try:
            resp = requests.post(self.url, json=payload, headers=self.headers, timeout=20)
            resp.raise_for_status()
            result = resp.json()
            content = result['choices'][0]['message']['content']
            return json.loads(content)
        except Exception as e:
            print(f"AI Engine Error: {e}")
            return self._fallback_logic(message)

    def _fallback_logic(self, msg):
        """تشخیص ساده در صورت قطع ارتباط با هوش مصنوعی"""
        msg = msg.lower()
        if any(w in msg for w in ['غذا', 'پیتزا', 'سفارش', 'گرسنه']):
            return {"intent": "food_order", "data": {}}
        if any(w in msg for w in ['بلیط', 'اتوبوس', 'سفر', 'برنامه']):
            return {"intent": "bus_ticket", "data": {}}
        return {"intent": "other", "data": {}}


# ==========================================
# 4. سرویس‌های کسب‌وکار (Business Logic)
# ==========================================

class Services:
    MENU = {"پیتزا مخصوص": 180000, "چیز برگر": 140000, "ساندویچ ژامبون": 95000, "نوشابه قوطی": 30000}

    @staticmethod
    def process_food(tid, name):
        # جستجوی هوشمند در منو
        matched_item = next((k for k in Services.MENU.keys() if name in k), None)
        if matched_item:
            price = Services.MENU[matched_item]
            db.add_order(tid, matched_item, 1, price)
            return f"✅ سفارش '{matched_item}' با موفقیت ثبت شد.\n💰 مبلغ قابل پرداخت: {price:,} تومان"
        return f"❌ متأسفانه '{name}' در منو یافت نشد.\n📋 منوی ما: {', '.join(Services.MENU.keys())}"

    @staticmethod
    def process_bus(tid, origin, dest, date):
        price = 195000 # قیمت نمونه
        db.add_ticket(tid, origin, dest, date, price)
        return f"🚌 بلیط اتوبوس از {origin} به {dest} برای تاریخ {date} رزرو شد.\n🎫 کد رهگیری: #{tid % 1000}\n💰 مبلغ: {price:,} تومان"


# ==========================================
# 5. هندلرهای تعاملی تلگرام
# ==========================================

db = Database()
ai = AIEngine()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.add_user(user.id, user.username, user.first_name)
    await update.message.reply_text(
        f"سلام {user.first_name}! 👋\n"
        f"به ربات هوشمند مبتنی بر {OLLAMA_MODEL} خوش آمدید.\n\n"
        "🍕 برای سفارش غذا نام آن را بنویسید.\n"
        "🚌 برای خرید بلیط، مبدأ و مقصد را بگویید."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    wait_msg = await update.message.reply_text("⏳ در حال تحلیل درخواست...")
    
    try:
        result = ai.detect_intent(text)
        intent = result.get('intent')
        data = result.get('data', {})
        
        response = ""
        if intent == 'food_order':
            food = data.get('food_name')
            if not food:
                response = "لطفاً نام غذایی که میل دارید را مشخص کنید. (مثلاً: پیتزا)"
            else:
                response = Services.process_food(update.effective_user.id, food)
                
        elif intent == 'bus_ticket':
            org = data.get('origin')
            dst = data.get('destination')
            dt = data.get('date')
            if org and dst and dt:
                response = Services.process_bus(update.effective_user.id, org, dst, dt)
            else:
                response = "برای رزرو بلیط لطفاً مبدأ، مقصد و تاریخ سفر را به صورت کامل بیان کنید."
                
        elif intent == 'help':
            response = "من می‌توانم برای شما غذا سفارش دهم یا بلیط اتوبوس رزرو کنم. کافیست طبیعی صحبت کنید!"
            
        else:
            response = "درخواست شما را دریافت کردم اما دقیقاً متوجه نوع خدمت نشدم. لطفاً واضح‌تر بفرمایید."
            
        await wait_msg.edit_text(response)
        
    except Exception as e:
        await wait_msg.edit_text(f"⚠️ خطای سیستمی: {str(e)}")

def main():
    print(f"System Initialized | Model: {OLLAMA_MODEL} | Config: {SYS_VAR_CONFIG_1}")
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Bot is now listening for messages...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()