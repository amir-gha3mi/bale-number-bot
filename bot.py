from aiohttp import web, ClientSession
import asyncpg
import datetime
from dateutil import tz
import os

# توکن ربات بله
TOKEN = "919464485:oQH2OnSnihbXVUBepUf-MpYozwURFQIH7kE"

# لینک دیتابیس Supabase (همون که کپی کردی)
DATABASE_URL = "postgresql://postgres:S66b@sfxi4a9@db.cocysbrmnfdymaybmbvs.supabase.co:5432/postgres"

# اتصال به دیتابیس (یک بار موقع استارت)
pool = None

async def connect_db(app):
    global pool
    pool = await asyncpg.create_pool(DATABASE_URL)

async def close_db(app):
    if pool:
        await pool.close()

async def handle(request):
    data = await request.json()
    
    if "message" in data:
        msg = data["message"]
        chat_id = msg["chat"]["id"]
        user_id = msg["from"]["id"]
        username = msg["from"].get("username", "")
        text = msg.get("text", "").strip()

        if text == "/start":
            keyboard = {
                "keyboard": [[{"text": "ثبت عدد جدید"}]],
                "resize_keyboard": True
            }
            await send_message(chat_id, "سلام! برای ثبت عدد دکمه زیر رو بزن 👇", keyboard)

        elif text == "ثبت عدد جدید":
            await send_message(chat_id, "عدد مورد نظر رو بفرست (مثلاً ۴۵):")
            save_state(user_id, "waiting")

        elif get_state(user_id) == "waiting":
            if text.isdigit():
                # ثبت در Supabase
                async with pool.acquire() as conn:
                    await conn.execute(
                        """INSERT INTO tbl_GetNumberTests (user_id, username, created_at) 
                           VALUES ($1, $2, $3)""",
                        user_id, username or None, datetime.datetime.now(tz.gettz('Asia/Tehran'))
                    )
                await send_message(chat_id, f"عدد {text} با موفقیت ثبت شد! ✅")
                clear_state(user_id)
            else:
                await send_message(chat_id, "لطفاً فقط عدد بفرست (مثلاً ۱۲۳)")

    return web.Response(text="ok")

async def send_message(chat_id, text, reply_markup=None):
    url = f"https://tapi.bale.ai/bot{TOKEN}/sendMessage"
    data = {"chat_id": chat_id, "text": text}
    if reply_markup:
        data["reply_markup"] = reply_markup
    async with ClientSession() as session:
        async with session.post(url, json=data):
            pass

# ذخیره وضعیت موقت (فقط برای این که بدونه منتظر عدده)
STATE = {}
def save_state(uid, state): STATE[uid] = state
def get_state(uid): return STATE.get(uid)
def clear_state(uid): STATE.pop(uid, None)

app = web.Application()
app.on_startup.append(connect_db)
app.on_cleanup.append(close_db)
app.router.add_post(f'/{TOKEN}', handle)

if __name__ == "__main__":
    web.run_app(app, port=8080)
