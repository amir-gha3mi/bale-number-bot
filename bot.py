from aiohttp import web, ClientSession
import datetime
import os
import json
import logging
from supabase import create_client, Client

# توکن ربات بله
TOKEN = "919464485:oQH2OnSnihbXVUBepUf-MpYozwURFQIH7kE"

# لینک دیتابیس Supabase (همون که کپی کردی)
DATABASE_URL = "postgresql://postgres.cocysbrmnfdymaybmbvs:S66b@sfxi4a9@aws-1-eu-north-1.pooler.supabase.com:5432/postgres?sslmode=require"

# تنظیم لاگینگ پیشرفته
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# خواندن از متغیرهای محیطی
TOKEN = os.environ.get("919464485:oQH2OnSnihbXVUBepUf-MpYozwURFQIH7kE", "")
SUPABASE_URL = os.environ.get("https://cocysbrmnfdymaybmbvs.supabase.co", "")
SUPABASE_KEY = os.environ.get("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNvY3lzYnJtbmZkeW1heWJtYnZzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjQ2OTUxODQsImV4cCI6MjA4MDI3MTE4NH0.IURcbaCRjV85H_a6OZ6P_QcxmRADoGQREDjiuH3FQ0A", "")

# ایجاد کلاینت Supabase
supabase: Client = None

async def init_supabase():
    """ایجاد اتصال به Supabase"""
    global supabase
    try:
        from supabase import create_client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # تست اتصال
        test_response = supabase.table("tbl_GetNumberTests").select("*", count="exact").limit(1).execute()
        logger.info(f"✅ Supabase connected successfully. Found {len(test_response.data) if test_response.data else 0} records")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to initialize Supabase: {e}")
        return False

async def handle(request):
    """مدیریت درخواست‌های وب‌هوک"""
    global supabase
    
    logger.info(f"📥 Received request at path: {request.path}")
    
    try:
        data = await request.json()
        logger.info(f"📊 Request data: {json.dumps(data, ensure_ascii=False)[:500]}...")
    except Exception as e:
        logger.error(f"❌ JSON parse error: {e}")
        return web.Response(text="ok")

    if "message" not in data:
        logger.warning("⚠️ No 'message' in data")
        return web.Response(text="ok")

    msg = data["message"]
    chat_id = msg["chat"]["id"]
    user_id = msg["from"]["id"]
    username = msg["from"].get("username", "") or ""
    first_name = msg["from"].get("first_name", "") or ""
    text = msg.get("text", "").strip()
    
    logger.info(f"👤 User {user_id} ({username or first_name}) sent: {text}")

    try:
        # دستور /start
        if text == "/start":
            keyboard = {
                "keyboard": [[{"text": "📝 ثبت عدد جدید"}]],
                "resize_keyboard": True,
                "one_time_keyboard": False,
                "input_field_placeholder": "از دکمه‌ها استفاده کن"
            }
            await send_message(chat_id, f"سلام {first_name or username or 'کاربر'}! 👋\n\nبرای ثبت عدد جدید روی دکمه زیر کلیک کن:", keyboard)
            logger.info(f"✅ Sent start message to {chat_id}")

        # دکمه ثبت عدد جدید
        elif text == "📝 ثبت عدد جدید" or text == "ثبت عدد جدید":
            await send_message(chat_id, "🔢 لطفاً عدد مورد نظرت رو بفرست:\n\nمثال: ۱۲۳", None)
            
            # ذخیره state در Supabase
            try:
                if supabase:
                    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
                    supabase.table("user_states").upsert({
                        "user_id": user_id,
                        "state": "waiting_for_number",
                        "updated_at": now
                    }).execute()
                    logger.info(f"📝 State saved for user {user_id}")
            except Exception as e:
                logger.error(f"❌ Error saving state: {e}")

        # پردازش عدد دریافتی
        elif await get_state(user_id) == "waiting_for_number":
            # حذف فاصله و کاراکترهای غیرعدد فارسی/انگلیسی
            cleaned_text = text.strip()
            
            # تبدیل اعداد فارسی به انگلیسی
            persian_to_english = str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789')
            cleaned_text = cleaned_text.translate(persian_to_english)
            
            # حذف کاراکترهای غیرعدد
            cleaned_text = ''.join(filter(str.isdigit, cleaned_text))
            
            if not cleaned_text:
                await send_message(chat_id, "❌ لطفاً فقط عدد وارد کن!\n\nمثال: ۴۵ یا 123", None)
                return web.Response(text="ok")
            
            try:
                number = int(cleaned_text)
                
                # ثبت در دیتابیس
                if supabase:
                    now = datetime.datetime.now(datetime.timezone.utc)
                    data_to_insert = {
                        "user_id": user_id,
                        "username": username if username else None,
                        "first_name": first_name if first_name else None,
                        "number": number,
                        "created_at": now.isoformat()
                    }
                    
                    response = supabase.table("tbl_GetNumberTests").insert(data_to_insert).execute()
                    
                    if response.data:
                        # نمایش موفقیت با emoji
                        await send_message(chat_id, f"✅ ثبت موفق!\n\n📊 عدد **{number}** ذخیره شد\n👤 کاربر: {first_name or username or user_id}\n🕐 زمان: {now.strftime('%Y/%m/%d %H:%M')}\n\nبرای ثبت عدد جدید دکمه زیر رو بزن:", {
                            "keyboard": [[{"text": "📝 ثبت عدد جدید"}]],
                            "resize_keyboard": True
                        })
                        logger.info(f"✅ Number {number} saved for user {user_id}")
                        
                        # پاک کردن state
                        await clear_state(user_id)
                    else:
                        raise Exception("No data returned from insert")
                        
            except ValueError:
                await send_message(chat_id, "❌ عدد وارد شده معتبر نیست!\nلطفاً یک عدد صحیح وارد کن.", None)
            except Exception as e:
                logger.error(f"❌ DB Error: {e}")
                await send_message(chat_id, "⚠️ خطا در ذخیره اطلاعات!\nلطفاً دوباره امتحان کن.", None)

        # پیام نامشخص
        else:
            keyboard = {
                "keyboard": [[{"text": "📝 ثبت عدد جدید"}]],
                "resize_keyboard": True
            }
            await send_message(chat_id, "🤔 دستور رو متوجه نشدم!\n\nبرای شروع از دکمه زیر استفاده کن:", keyboard)

    except Exception as e:
        logger.error(f"🔥 Handler Error: {e}", exc_info=True)
        await send_message(chat_id, "⛔ خطای سیستمی! لطفاً بعداً تلاش کن.", None)

    return web.Response(text="ok")

async def send_message(chat_id, text, reply_markup=None):
    """ارسال پیام به کاربر"""
    url = f"https://tapi.bale.ai/bot{TOKEN}/sendMessage"
    
    # ساخت بدنه پیام
    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    
    if reply_markup:
        data["reply_markup"] = reply_markup
    
    try:
        logger.info(f"📤 Sending message to {chat_id}: {text[:50]}...")
        
        timeout = aiohttp.ClientTimeout(total=30)
        async with ClientSession(timeout=timeout) as session:
            async with session.post(url, json=data) as response:
                response_text = await response.text()
                
                if response.status == 200:
                    logger.info(f"✅ Message sent successfully to {chat_id}")
                else:
                    logger.error(f"❌ Failed to send message: Status {response.status}, Response: {response_text}")
                    
    except asyncio.TimeoutError:
        logger.error(f"⏰ Timeout while sending message to {chat_id}")
    except Exception as e:
        logger.error(f"🔥 Error in send_message: {e}", exc_info=True)

async def get_state(user_id):
    """دریافت state از Supabase"""
    try:
        if supabase:
            response = supabase.table("user_states").select("state").eq("user_id", user_id).execute()
            if response.data:
                return response.data[0]["state"]
    except Exception as e:
        logger.error(f"❌ Error getting state: {e}")
    return None

async def clear_state(user_id):
    """پاک کردن state از Supabase"""
    try:
        if supabase:
            supabase.table("user_states").delete().eq("user_id", user_id).execute()
            logger.info(f"🗑️ State cleared for user {user_id}")
    except Exception as e:
        logger.error(f"❌ Error clearing state: {e}")

# تابع شروع اپلیکیشن
async def on_startup(app):
    """عملیات هنگام راه‌اندازی"""
    logger.info("🚀 Bot is starting up...")
    
    # تست توکن
    if not TOKEN:
        logger.error("❌ TOKEN is not set!")
    else:
        logger.info(f"✅ Bot token: {TOKEN[:10]}...")
    
    # اتصال به Supabase
    if await init_supabase():
        logger.info("✅ All services initialized successfully")
    else:
        logger.error("❌ Failed to initialize some services")

app = web.Application()
app.on_startup.append(on_startup)
app.router.add_post(f'/{TOKEN}', handle)

# روت سلامت
async def health_check(request):
    return web.Response(text="🤖 Bot is running!")

app.router.add_get('/health', health_check)
app.router.add_get('/', health_check)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"🌐 Starting server on port {port}")
    web.run_app(app, host="0.0.0.0", port=port, access_log=logger)
