import os
import json
import math
import time
import asyncio
import tempfile
import aiohttp

from telethon import TelegramClient, events, Button

# =========================
# تنظیمات ربات و پشتیبانی
# =========================

BOT_TOKEN = "8853938117:AAEw9F4sX18hHeRcpqON9vRsFBkMDf8ocbA"
API_ID = 36808151
API_HASH = "aed077fef573b693fee8f86884c15066"

# ⚠️ آیدی عددی تلگرام ادمین (حتما آیدی عددی خود را وارد کنید)
ADMIN_ID =  8383843385 

# ⚠️ آیدی پشتیبانی بدون @
SUPPORT_USERNAME = "pe_she"

# فایل ذخیره‌سازی کاربران و تنظیمات
USERS_FILE = "users.json"
SETTINGS_FILE = "settings.json"

bot = TelegramClient("file_link_bot", API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# وضعیت متغیرهای همگانی
USER_STATES = {}


# =========================
# توابع مدیریت فایل‌ها و داده‌ها
# =========================

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=4)

def add_user(user_id):
    users = load_users()
    if user_id not in users:
        users.append(user_id)
        save_users(users)

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"force_channel": ""}

def save_settings(settings):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=4)

def humanbytes(size):
    if not size:
        return "0 B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(size, 1024)))
    p = math.pow(1024, i)
    s = round(size / p, 2)
    return f"{s} {size_name[i]}"

async def check_joined(user_id):
    settings = load_settings()
    channel = settings.get("force_channel")
    if not channel:
        return True
    try:
        participant = await bot.get_permissions(channel, user_id)
        return participant.is_participant
    except Exception:
        return True


# =========================
# دستور /start
# =========================

@bot.on(events.NewMessage(pattern="/start"))
async def start_handler(event):
    user_id = event.sender_id
    add_user(user_id)

    if not await check_joined(user_id):
        settings = load_settings()
        channel = settings.get("force_channel")
        buttons = [[Button.url("📢 عضویت در کانال", f"https://t.me/{channel.replace('@', '')}")]]
        await event.respond("⚠️ جهت استفاده از ربات، ابتدا باید در کانال ما عضو شوید:", buttons=buttons)
        return

    text = (
        "سلام 👋 به ربات تبدیل فایل به لینک خوش آمدید!\n\n"
        "📁 هر نوع فایلی (عکس، ویدیو، سند، ویس و...) را ارسال کنید تا لینک دانلود مستقیم آن را تحویل بگیرید.\n\n"
        "💡 برای راهنمایی بیشتر دستور /help را ارسال کنید."
    )
    
    buttons = [
        [Button.inline("❓ راهنما", data="help_btn"), Button.url("💬 پشتیبانی", f"https://t.me/{SUPPORT_USERNAME}")],
    ]
    
    if user_id == ADMIN_ID:
        buttons.append([Button.inline("⚙️ پنل مدیریت", data="admin_panel")])

    await event.respond(text, buttons=buttons)


# =========================
# پنل مدیریت (ادمین)
# =========================

@bot.on(events.NewMessage(pattern="/admin"))
async def admin_cmd(event):
    if event.sender_id != ADMIN_ID:
        return
    await show_admin_panel(event)

async def show_admin_panel(event_or_query):
    buttons = [
        [Button.inline("📊 آمار ربات", data="admin_stats")],
        [Button.inline("📢 پیام همگانی", data="admin_bc"), Button.inline("🔄 فوروارد همگانی", data="admin_fwd")],
        [Button.inline("📢 تنظیم کانال جوین اجباری", data="admin_set_channel")],
        [Button.inline("❌ بستن پنل", data="close_admin")]
    ]
    text = "🛠 **به پنل مدیریت خوش آمدید.** لطفا یک گزینه را انتخاب کنید:"
    
    if isinstance(event_or_query, events.CallbackQuery.Event):
        await event_or_query.edit(text, buttons=buttons)
    else:
        await event_or_query.respond(text, buttons=buttons)


@bot.on(events.CallbackQuery)
async def callback_query_handler(event):
    data = event.data.decode("utf-8")
    user_id = event.sender_id

    if data == "help_btn":
        help_text = "📖 **راهنمای سریع:**\n\nکافیست هر فایلی را مستقیماً برای ربات بفرستید تا لینک دانلود آن ساخته شود."
        await event.answer(help_text, alert=True)
        return

    # کنترل‌های پنل مدیریت
    if user_id != ADMIN_ID:
        return

    if data == "admin_panel":
        await show_admin_panel(event)

    elif data == "admin_stats":
        users = load_users()
        await event.answer(f"📊 تعداد کاربران کل ربات: {len(users)} نفر", alert=True)

    elif data == "admin_bc":
        USER_STATES[user_id] = "send_bc"
        await event.edit("📝 **لطفا پیامی که می‌خواهید به همگی ارسال شود را بفرستید:**\n(میتواند متن، عکس، یا... باشد)\n\nجهت انصراف /cancel را بفرستید.")

    elif data == "admin_fwd":
        USER_STATES[user_id] = "send_fwd"
        await event.edit("🔄 **لطفا پیام مورد نظر جهت فوروارد را ارسال کنید:**\n\nجهت انصراف /cancel را بفرستید.")

    elif data == "admin_set_channel":
        USER_STATES[user_id] = "set_channel"
        settings = load_settings()
        curr = settings.get("force_channel", "تنظیم نشده")
        await event.edit(f"📢 **کانال فعلی:** `{curr}`\n\nلطفاً آیدی کانال را به همراه @ ارسال کنید (مثال: `@MyChannel`).\nبرای حذف جوین اجباری کلمه `off` را بفرستید.\n\nجهت انصراف /cancel را بفرستید.")

    elif data == "close_admin":
        await event.delete()


# =========================
# دستور cancellation و پردازش حالات مدیریت
# =========================

@bot.on(events.NewMessage)
async def state_and_file_handler(event):
    user_id = event.sender_id
    text = event.text or ""

    if text == "/cancel" and user_id in USER_STATES:
        del USER_STATES[user_id]
        await event.respond("❌ عملیات لغو شد.")
        return

    # پردازش حالت‌های مدیریت
    if user_id in USER_STATES:
        state = USER_STATES[user_id]
        del USER_STATES[user_id]

        if state == "set_channel":
            if text.lower() == "off":
                save_settings({"force_channel": ""})
                await event.respond("✅ قفل کانال با موفقیت غیرفعال شد.")
            else:
                save_settings({"force_channel": text.strip()})
                await event.respond(f"✅ کانال جوین اجباری روی `{text.strip()}` تنظیم شد.\n⚠️ ربات باید در کانال ادمین باشد!")
            return

        elif state in ["send_bc", "send_fwd"]:
            users = load_users()
            status_msg = await event.respond("⏳ در حال ارسال پیام به تمامی کاربران...")
            success, count = 0, 0

            for u in users:
                try:
                    if state == "send_bc":
                        await bot.send_message(u, event.message)
                    else:
                        await bot.forward_messages(u, event.message)
                    success += 1
                except Exception:
                    pass
                count += 1
                if count % 20 == 0:
                    await asyncio.sleep(1)

            await status_msg.edit(f"✅ ارسال همگانی با موفقیت پایان یافت.\n\n📤 **ارسال شده:** {success} از {len(users)}")
            return

    # اگر دستور سیستم باشد اجرا نشود
    if text.startswith("/"):
        return

    # checking force join
    if not await check_joined(user_id):
        settings = load_settings()
        channel = settings.get("force_channel")
        buttons = [[Button.url("📢 عضویت در کانال", f"https://t.me/{channel.replace('@', '')}")]]
        await event.respond("⚠️ برای استفاده از ربات باید در کانال عضو باشید:", buttons=buttons)
        return

    # دریافت و آپلود فایل
    if not event.media:
        return

    status = await event.respond("📥 در حال آماده‌سازی برای دریافت...")

    file_name = "file"
    if event.file and event.file.name:
        file_name = os.path.basename(event.file.name)
    elif event.file and event.file.ext:
        file_name = f"file_{event.message.id}{event.file.ext}"
    else:
        file_name = f"media_{event.message.id}.jpg"

    temp_dir = tempfile.mkdtemp(prefix="filebot_")
    file_path = os.path.join(temp_dir, file_name)

    last_update_time = 0

    async def download_progress_callback(current, total):
        nonlocal last_update_time
        now = time.time()
        if now - last_update_time > 2.5 or current == total:
            last_update_time = now
            percentage = (current / total) * 100
            try:
                await status.edit(
                    f"📥 **در حال دانلود از تلگرام...**\n\n"
                    f"📊 پیشرفت: `{percentage:.1f}%`\n"
                    f"💾 حجم: `{humanbytes(current)}` از `{humanbytes(total)}`"
                )
            except Exception:
                pass

    try:
        downloaded_path = await bot.download_media(
            event.message,
            file=file_path,
            progress_callback=download_progress_callback
        )

        file_size = os.path.getsize(downloaded_path)

        await status.edit("📤 در حال اتصال به سرور GoFile...")

        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.gofile.io/servers") as server_res:
                server_data = await server_res.json()
                
                if server_data.get("status") != "ok" or not server_data.get("data", {}).get("servers"):
                    await status.edit("❌ خطا در دریافت سرور آپلود.")
                    return
                
                best_server = server_data["data"]["servers"][0]["name"]
                upload_url = f"https://{best_server}.gofile.io/contents/uploadfile"

            await status.edit("📤 در حال ارسال و آپلود فایل...")

            with open(downloaded_path, "rb") as f:
                form = aiohttp.FormData()
                form.add_field(
                    "file",
                    f,
                    filename=file_name,
                    content_type="application/octet-stream"
                )

                async with session.post(upload_url, data=form) as response:
                    result = await response.json()

        if result.get("status") != "ok":
            await status.edit("❌ آپلود فایل ناموفق بود.")
            return

        data = result.get("data", {})
        download_url = data.get("downloadPage")

        if not download_url:
            await status.edit("❌ لینک دانلود دریافت نشد.")
            return

        buttons = [
            [Button.url("🌐 باز کردن لینک دانلود", download_url)],
            [Button.url("💬 پشتیبانی", f"https://t.me/{SUPPORT_USERNAME}")]
        ]

        await status.edit(
            f"✅ **فایل با موفقیت آپلود شد!**\n\n"
            f"📁 **نام فایل:**\n`{file_name}`\n"
            f"📦 **حجم فایل:** `{humanbytes(file_size)}`\n\n"
            f"🔗 **لینک دانلود:**\n{download_url}",
            buttons=buttons
        )

    except Exception as e:
        await status.edit(f"❌ خطا:\n\n`{str(e)}`")

    finally:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
            if os.path.exists(temp_dir):
                os.rmdir(temp_dir)
        except Exception:
            pass


# =========================
# اجرای ربات
# =========================

print("🤖 Bot is running with Admin Panel...")
bot.run_until_disconnected()

