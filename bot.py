from aiohttp import web, ClientSession
import datetime
import os
import asyncio
from supabase import create_client, Client
import logging

# توکن ربات بله
TOKEN = "919464485:oQH2OnSnihbXVUBepUf-MpYozwURFQIH7kE"

# لینک دیتابیس Supabase (همون که کپی کردی)
DATABASE_URL = "postgresql://postgres.cocysbrmnfdymaybmbvs:S66b@sfxi4a9@aws-1-eu-north-1.pooler.supabase.com:5432/postgres?sslmode=require"

# تنظیم لاگینگ
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# اطلاعات Supabase
SUPABASE_URL = "https://cocysbrmnfdymaybmbvs.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNvY3lzYnJtbmZkeW1heWJtYnZzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjQ2OTUxODQsImV4cCI6MjA4MDI3MTE4NH0.IURcbaCRjV85H_a6OZ6P_QcxmRADoGQREDjiuH3FQ0A"  # کلید Service Role یا Anon

# ایجاد کلاینت Supabase
supabase: Client = None

async def init_supabase():
    """ایجاد اتصال به Supabase"""
    global supabase
    try:
        from supabase import create_client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info("Supabase client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Supabase: {e}")

async def handle(request):
    global supabase
    
    try:
        data = await request.json()
    except:
        return web.Response(text="ok")

    if "message" not in data:
        return web.Response(text="ok")

    msg = data["message"]
    chat_id = msg["chat"]["id"]
    user_id = msg["from"]["id"]
    username = msg["from"].get("username", "") or ""
    text = msg.get("text", "").strip()

    try:
        if text == "/start":
            keyboard = {
                "keyboard": [[{"text": "ثبت عدد جدید"}]],
                "resize_keyboard": True,
                "one_time_keyboard": False
            }
            await send_message(chat_id, "سلام! برای ثبت عدد دکمه زیر رو بزن", keyboard)

        elif text == "ثبت عدد جدید":
            await send_message(chat_id, "عدد مورد نظر رو بفرست (مثلاً ۴۵):")
            # ذخیره state در Supabase
            await save_state(user_id, "waiting")

        elif await get_state(user_id) == "waiting":
            if not text.isdigit():
                await send_message(chat_id, "لطفاً فقط عدد بفرست")
                return web.Response(text="ok")

            # ثبت در Supabase
            try:
                # زمان فعلی با تایم‌زون
                now = datetime.datetime.now(datetime.timezone.utc)
                
                # درج داده در جدول
                data_to_insert = {
                    "user_id": user_id,
                    "username": username if username else None,
                    "number": int(text),
                    "created_at": now.isoformat()
                }
                
                response = supabase.table("tbl_GetNumberTests").insert(data_to_insert).execute()
                
                if response.data:
                    await send_message(chat_id, f"عدد {text} با موفقیت ثبت شد!")
                    logger.info(f"Number {text} saved for user {user_id}")
                else:
                    raise Exception("No data returned from insert")
                    
            except Exception as e:
                logger.error(f"DB Error: {e}")
                await send_message(chat_id, "خطا در ثبت به دیتابیس. دوباره امتحان کن.")
            
            # پاک کردن state
            await clear_state(user_id)

    except Exception as e:
        logger.error(f"Handler Error: {e}")
        await send_message(chat_id, "یک خطای غیرمنتظره رخ داد.")

    return web.Response(text="ok")

async def send_message(chat_id, text, reply_markup=None):
    url = f"https://tapi.bale.ai/bot{TOKEN}/sendMessage"
    data = {"chat_id": chat_id, "text": text}
    if reply_markup: 
        data["reply_markup"] = reply_markup
    
    try:
        async with ClientSession() as session:
            async with session.post(url, json=data, timeout=10) as response:
                if response.status != 200:
                    logger.error(f"Failed to send message: {response.status}")
    except Exception as e:
        logger.error(f"Error in send_message: {e}")

# توابع مدیریت state در Supabase
async def save_state(user_id, state):
    """ذخیره state در Supabase"""
    try:
        data = {
            "user_id": user_id,
            "state": state,
            "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        # بررسی وجود رکورد
        existing = supabase.table("user_states").select("*").eq("user_id", user_id).execute()
        
        if existing.data:
            # آپدیت state موجود
            supabase.table("user_states").update({"state": state}).eq("user_id", user_id).execute()
        else:
            # درج رکورد جدید
            supabase.table("user_states").insert(data).execute()
    except Exception as e:
        logger.error(f"Error saving state: {e}")

async def get_state(user_id):
    """دریافت state از Supabase"""
    try:
        response = supabase.table("user_states").select("state").eq("user_id", user_id).execute()
        if response.data:
            return response.data[0]["state"]
        return None
    except Exception as e:
        logger.error(f"Error getting state: {e}")
        return None

async def clear_state(user_id):
    """پاک کردن state از Supabase"""
    try:
        supabase.table("user_states").delete().eq("user_id", user_id).execute()
    except Exception as e:
        logger.error(f"Error clearing state: {e}")

# تابع شروع اپلیکیشن
async def on_startup(app):
    """عملیات هنگام راه‌اندازی"""
    await init_supabase()

app = web.Application()
app.on_startup.append(on_startup)
app.router.add_post(f'/{TOKEN}', handle)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    web.run_app(app, host="0.0.0.0", port=port)
