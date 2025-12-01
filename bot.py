from aiohttp import web, ClientSession
from dateutil import tz
import datetime
import os
import datetime
import os

# توکن رباتت را اینجا بگذار (همون که BotFather داد)
TOKEN = "919464485:oQH2OnSnihbXVUBepUf-MpYozwURFQIH7kE"

FILE_NAME = "numbers.txt"

# ساخت فایل اگر نبود
if not os.path.exists(FILE_NAME):
    with open(FILE_NAME, "w", encoding="utf-8") as f:
        f.write("ثبت اعداد کاربران:\n\n")

async def handle(request):
    data = await request.json()
    
    if "message" in data:
        msg = data["message"]
        chat_id = msg["chat"]["id"]
        text = msg.get("text", "")
        user_id = msg["from"]["id"]
        
        if text == "/start":
            keyboard = {
                "keyboard": [[{"text": "ثبت عدد جدید"}]],
                "resize_keyboard": True,
                "one_time_keyboard": False
            }
            await send_message(chat_id, "سلام! برای ثبت عدد دکمه زیر رو بزن 👇", keyboard)
            
        elif text == "ثبت عدد جدید":
            await send_message(chat_id, "عدد مورد نظر رو بفرست (مثلاً ۴۵):")
            save_user_state(user_id, "waiting")
            
        elif is_user_waiting(user_id):
            if text.strip().isdigit():
                now = datetime.datetime.now(tz.gettz('Asia/Tehran'))
                date_str = now.strftime("%Y/%m/%d - %H:%M:%S")
                line = f"کاربر {user_id} | عدد: {text} | زمان: {date_str}\n"
                
                with open(FILE_NAME, "a", encoding="utf-8") as f:
                    f.write(line)
                    
                await send_message(chat_id, f"عدد {text} با موفقیت ثبت شد!\n\nتاریخ: {date_str}\n\nدوباره می‌تونی عدد جدید بفرستی یا /start بزنی.")
                clear_user_state(user_id)
            else:
                await send_message(chat_id, "فقط عدد بفرست لطفاً (مثلاً ۱۲۳)")
    
    return web.Response(text="ok")

async def send_message(chat_id, text, reply_markup=None):
    url = f"https://tapi.bale.ai/bot{TOKEN}/sendMessage"
    data = {"chat_id": chat_id, "text": text}
    if reply_markup:
        data["reply_markup"] = reply_markup
    async with web_session.post(url, json=data) as resp:
        pass

# وضعیت کاربر (ساده)
STATE_FILE = "state.txt"
def save_user_state(user_id, state):
    with open(STATE_FILE, "w") as f:
        f.write(f"{user_id}:{state}")

def is_user_waiting(user_id):
    if not os.path.exists(STATE_FILE):
        return False
    with open(STATE_FILE, "r") as f:
        content = f.read().strip()
        return content == f"{user_id}:waiting"

def clear_user_state(user_id):
    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)

app = web.Application()
app.router.add_post(f'/{TOKEN}', handle)

# ایجاد session داخل استارت‌آپ
async def on_startup(app):
    app['websession'] = ClientSession()

async def on_cleanup(app):
    await app['websession'].close()

app.on_startup.append(on_startup)
app.on_cleanup.append(on_cleanup)

# تابع ارسال پیام رو هم کمی تغییر دادیم که از session داخل app استفاده کنه
async def send_message(chat_id, text, reply_markup=None):
    session = app['websession']  # اینجا از session داخل app استفاده می‌کنیم
    url = f"https://tapi.bale.ai/bot{TOKEN}/sendMessage"
    data = {"chat_id": chat_id, "text": text}
    if reply_markup:
        data["reply_markup"] = reply_markup
    async with session.post(url, json=data):
        pass

if __name__ == "__main__":
    print("ربات در حال اجراست... (برای بستن Ctrl+C بزن)")
    web.run_app(app, host="0.0.0.0", port=8080)