from aiohttp import web, ClientSession
import asyncpg
import datetime
from dateutil import tz
import os

# توکن ربات بله
TOKEN = "919464485:oQH2OnSnihbXVUBepUf-MpYozwURFQIH7kE"

# لینک دیتابیس Supabase (همون که کپی کردی)
DATABASE_URL = "postgresql://postgres.cocysbrmnfdymaybmbvs:S66b@sfxi4a9@aws-1-eu-north-1.pooler.supabase.com:5432/postgres?sslmode=require"

async def handle(request):
    try:
        data = await request.json()
    except:
        return web.Response(text="ok")  # اگر json خراب بود

    if "message" not in data:
        return web.Response(text="ok")

    msg = data["message"]
    chat_id = msg["chat"]["id"]
    user_id = msg["from"]["id"]
    username = msg["from"].get("username", "") or ""
    text = msg.get("text", "").strip()

    try:
        if text == "/start":
            keyboard = {"keyboard": [[{"text": "ثبت عدد جدید"}]], "resize_keyboard": True}
            await send_message(chat_id, "سلام! برای ثبت عدد دکمه زیر رو بزن", keyboard)

        elif text == "ثبت عدد جدید":
            await send_message(chat_id, "عدد مورد نظر رو بفرست (مثلاً ۴۵):")
            save_state(user_id, "waiting")

        elif get_state(user_id) == "waiting":
            if not text.isdigit():
                await send_message(chat_id, "لطفاً فقط عدد بفرست")
                return web.Response(text="ok")

            # ثبت در Supabase
            success = False
            try:
                conn = await asyncpg.connect(DATABASE_URL)
                await conn.execute(
                    "INSERT INTO tbl_GetNumberTests (user_id, username, created_at) VALUES ($1, $2, $3)",
                    user_id, username or None, datetime.datetime.now(datetime.timezone.utc)
                )
                await conn.close()
                success = True
            except Exception as e:
                print("DB Error:", e)

            if success:
                await send_message(chat_id, f"عدد {text} با موفقیت ثبت شد!")
            else:
                await send_message(chat_id, "خطا در ثبت به دیتابیس. دوباره امتحان کن.")
            clear_state(user_id)

    except Exception as e:
        print("Handler Error:", e)  # برای لاگ

    return web.Response(text="ok")

# بقیه توابع بدون تغییر
async def send_message(chat_id, text, reply_markup=None):
    url = f"https://tapi.bale.ai/bot{TOKEN}/sendMessage"
    data = {"chat_id": chat_id, "text": text}
    if reply_markup: data["reply_markup"] = reply_markup
    async with ClientSession() as session:
        async with session.post(url, json=data):
            pass

STATE = {}
def save_state(u, s): STATE[u] = s
def get_state(u): return STATE.get(u)
def clear_state(u): STATE.pop(u, None)

app = web.Application()
app.router.add_post(f'/{TOKEN}', handle)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    web.run_app(app, host="0.0.0.0", port=port)


