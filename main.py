import asyncio
import sqlite3
import time
import os
import aiohttp
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

# ================= কনফিগারেশন =================
BOT_TOKEN = "9272825996:AAHVq8wZ1yX7LEfXO6b1EUnR-RVHnMOPlOA"
OPENROUTER_API_KEY = "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"
OWNER_ID = 8296736080

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ================= ডেটাবেস সেটআপ =================
conn = sqlite3.connect('bot.db', check_same_thread=False)
cursor = conn.cursor()

def init_db():
    cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, points INTEGER DEFAULT 0, referrer_id INTEGER, lang TEXT DEFAULT "en", last_daily INTEGER DEFAULT 0, last_free_key INTEGER DEFAULT 0)')
    cursor.execute('CREATE TABLE IF NOT EXISTS admins (user_id INTEGER PRIMARY KEY)')
    cursor.execute('CREATE TABLE IF NOT EXISTS channels (chat_id TEXT PRIMARY KEY, title TEXT, invite_link TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS custom_files (command TEXT PRIMARY KEY, file_id TEXT, custom_name TEXT, delete_timer INTEGER)')
    cursor.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)')
    
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('key_price', '20')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('ref_bonus', '14')")
    
    cursor.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (OWNER_ID,))
    conn.commit()

init_db()

# ================= ভাষা সেটআপ =================
LANGS = {
    "en": {
        "welcome": "👋 Welcome {name}!\nYour Balance: {points} Points",
        "profile": "👤 **Profile**\n\n🆔 ID: `{id}`\n💰 Balance: {points} Points",
        "refer": "🔗 **Your Referral Link:**\n`{link}`\n\n💰 Total Earnings: {points} Points",
        "deposit": "💳 Select payment method:",
        "wait_key": "⏳ Please wait 3 minutes. Your free key is being generated...",
        "key_ready": "✅ Here is your Free Key:\n`{key}`\n\nCopy it now!",
        "locked": "⏳ You already got a free key recently.\nWait {time} or buy VIP Key.",
        "must_join": "⚠️ You must join our channels to use the bot.",
        "verify_btn": "✅ I Joined",
        "joined": "✅ Verification successful! Welcome.",
        "not_joined": "❌ You haven't joined all channels yet.",
        "trx_received": "✅ TrxID received! Admin will verify and add points.",
        "btn_dep": "💳 Deposit",
        "btn_ref": "🔗 Refer",
        "btn_free": "🎁 Free Key",
        "btn_vip": "👑 VIP Key",
        "btn_lead": "🏆 Leaderboard",
        "btn_prof": "👤 Profile"
    },
    "bn": {
        "welcome": "👋 স্বাগতম {name}!\nআপনার ব্যালেন্স: {points} পয়েন্ট",
        "profile": "👤 **প্রোফাইল**\n\n🆔 আইডি: `{id}`\n💰 ব্যালেন্স: {points} পয়েন্ট",
        "refer": "🔗 **আপনার রেফারেল লিংক:**\n`{link}`\n\n💰 মোট আয়: {points} পয়েন্ট",
        "deposit": "💳 পেমেন্ট মেথড সিলেক্ট করুন:",
        "wait_key": "⏳ অনুগ্রহ করে ৩ মিনিট অপেক্ষা করুন। আপনার ফ্রি কী তৈরি হচ্ছে...",
        "key_ready": "✅ আপনার ফ্রি কী:\n`{key}`\n\nএখনই কপি করুন!",
        "locked": "⏳ আপনি সম্প্রতি একটি ফ্রি কী পেয়েছেন।\nঅপেক্ষা করুন {time} অথবা VIP কী কিনুন।",
        "must_join": "⚠️ বট ব্যবহার করতে আমাদের চ্যানেলে জয়েন করতে হবে।",
        "verify_btn": "✅ আমি জয়েন করেছি",
        "joined": "✅ ভেরিফিকেশন সফল! স্বাগতম।",
        "not_joined": "❌ আপনি এখনো সব চ্যানেলে জয়েন করেননি।",
        "trx_received": "✅ TrxID পাওয়া গেছে! অ্যাডমিন ভেরিফাই করে পয়েন্ট দিবে।",
        "btn_dep": "💳 ডিপোজিট",
        "btn_ref": "🔗 রেফার",
        "btn_free": "🎁 ফ্রি কী",
        "btn_vip": "👑 ভিআইপি কী",
        "btn_lead": "🏆 লিডারবোর্ড",
        "btn_prof": "👤 প্রোফাইল"
    }
}

def t(user_id, key, **kwargs):
    cursor.execute("SELECT lang FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    lang = res[0] if res else "en"
    text = LANGS.get(lang, LANGS["en"]).get(key, "Text missing")
    return text.format(**kwargs)

# ================= হেল্পার ফাংশন =================
def is_admin(user_id):
    cursor.execute("SELECT * FROM admins WHERE user_id = ?", (user_id,))
    return cursor.fetchone() is not None

def get_points(user_id):
    cursor.execute("SELECT points FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    return res[0] if res else 0

def add_points(user_id, amount):
    cursor.execute("INSERT INTO users (user_id, points) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET points = points + ?", (user_id, amount, amount))
    conn.commit()

def generate_key(prefix="S-"):
    chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    return f"{prefix}{''.join(random.choices(chars, k=4))}-{''.join(random.choices(chars, k=4))}"

def get_main_menu(user_id):
    builder = ReplyKeyboardBuilder()
    builder.button(text=t(user_id, "btn_dep"))
    builder.button(text=t(user_id, "btn_ref"))
    builder.button(text=t(user_id, "btn_free"))
    builder.button(text=t(user_id, "btn_vip"))
    builder.button(text=t(user_id, "btn_lead"))
    builder.button(text=t(user_id, "btn_prof"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

# ================= ফোর্স জয়েন চেক =================
async def check_channels(user_id):
    cursor.execute("SELECT chat_id FROM channels")
    channels = cursor.fetchall()
    if not channels: return True, []
    
    not_joined = []
    for (chat_id,) in channels:
        try:
            member = await bot.get_chat_member(chat_id, user_id)
            if member.status in ["left", "kicked"]:
                not_joined.append(chat_id)
        except Exception:
            pass
    return len(not_joined) == 0, not_joined

async def send_join_prompt(message: types.Message, channels: list, user_id):
    builder = InlineKeyboardBuilder()
    for chat_id in channels:
        cursor.execute("SELECT title, invite_link FROM channels WHERE chat_id = ?", (chat_id,))
        title, invite_link = cursor.fetchone()
        builder.button(text=f"Join {title}", url=invite_link)
    builder.button(text=t(user_id, "verify_btn"), callback_data="verify_join")
    builder.adjust(1)
    await message.answer(t(user_id, "must_join"), reply_markup=builder.as_markup())

# ================= স্টার্ট ও ল্যাঙ্গুয়েজ =================
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    
    # ইউজার ডেটাবেসে না থাকলে তৈরি
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()
        
        # রেফারেল চেক
        args = message.text.split()
        if len(args) > 1 and args[1].startswith("ref_"):
            referrer_id = int(args[1].replace("ref_", ""))
            if referrer_id != user_id:
                cursor.execute("UPDATE users SET referrer_id = ? WHERE user_id = ?", (referrer_id, user_id))
                conn.commit()
                add_points(referrer_id, 14)

    # চ্যানেল চেক
    joined, not_joined = await check_channels(user_id)
    if not joined:
        await send_join_prompt(message, not_joined, user_id)
        return

    # ল্যাঙ্গুয়েজ সিলেকশন
    builder = InlineKeyboardBuilder()
    builder.button(text="English 🇬🇧", callback_data="setlang_en")
    builder.button(text="বাংলা 🇧🇩", callback_data="setlang_bn")
    await message.answer("Please select your language / আপনার ভাষা নির্বাচন করুন:", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("setlang_"))
async def set_lang(callback: types.CallbackQuery):
    lang = callback.data.split("_")[1]
    user_id = callback.from_user.id
    cursor.execute("UPDATE users SET lang = ? WHERE user_id = ?", (lang, user_id))
    conn.commit()
    await callback.message.delete()
    await callback.message.answer(t(user_id, "welcome", name=callback.from_user.first_name, points=get_points(user_id)), reply_markup=get_main_menu(user_id))

@dp.callback_query(F.data == "verify_join")
async def verify_join(callback: types.CallbackQuery):
    joined, not_joined = await check_channels(callback.from_user.id)
    if joined:
        await callback.message.edit_text(t(callback.from_user.id, "joined"))
        await callback.message.answer(t(callback.from_user.id, "welcome", name=callback.from_user.first_name, points=get_points(callback.from_user.id)), reply_markup=get_main_menu(callback.from_user.id))
    else:
        await callback.answer(t(callback.from_user.id, "not_joined"), show_alert=True)

# ================= ইউজার কমান্ড =================
@dp.message(F.text == LANGS["en"]["btn_prof"])
@dp.message(F.text == LANGS["bn"]["btn_prof"])
async def profile_cmd(message: types.Message):
    user_id = message.from_user.id
    pts = get_points(user_id)
    await message.answer(t(user_id, "profile", id=user_id, points=pts), parse_mode="Markdown")

@dp.message(F.text == LANGS["en"]["btn_ref"])
@dp.message(F.text == LANGS["bn"]["btn_ref"])
async def refer_cmd(message: types.Message):
    user_id = message.from_user.id
    link = f"https://t.me/{(await bot.get_me()).username}?start=ref_{user_id}"
    await message.answer(t(user_id, "refer", link=link, points=get_points(user_id)), parse_mode="Markdown")

@dp.message(F.text == LANGS["en"]["btn_free"])
@dp.message(F.text == LANGS["bn"]["btn_free"])
async def free_key_cmd(message: types.Message):
    user_id = message.from_user.id
    now = int(time.time())
    
    cursor.execute("SELECT last_free_key FROM users WHERE user_id = ?", (user_id,))
    last_key = cursor.fetchone()[0]
    
    if now - last_key < 72000:
        remaining = 72000 - (now - last_key)
        time_str = f"{remaining // 3600}h {(remaining % 3600) // 60}m"
        await message.answer(t(user_id, "locked", time=time_str))
        return

    await message.answer(t(user_id, "wait_key"))
    asyncio.create_task(deliver_free_key(user_id, message.chat.id))

async def deliver_free_key(user_id, chat_id):
    await asyncio.sleep(180) 
    key = generate_key()
    cursor.execute("UPDATE users SET last_free_key = ? WHERE user_id = ?", (int(time.time()), user_id))
    conn.commit()
    try:
        await bot.send_message(chat_id, t(user_id, "key_ready", key=key), parse_mode="Markdown")
    except: pass

# ================= অ্যাডমিন প্যানেল (চ্যানেল অ্যাড) =================
@dp.message(Command("admin"))
async def admin_cmd(message: types.Message):
    if not is_admin(message.from_user.id): return
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Add Channel", callback_data="admin_addchannel")
    builder.button(text="📋 List Channels", callback_data="admin_listchannels")
    await message.answer("⚙️ Admin Panel", reply_markup=builder.as_markup())

@dp.callback_query(F.data == "admin_addchannel")
async def admin_addchannel(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id): return
    await callback.message.edit_text("Send channel info in this format:\n`@channel_username | Channel Title | https://t.me/...`\n\nMake sure the bot is an admin in that channel!")

@dp.message(F.text.contains("|"))
async def process_add_channel(message: types.Message):
    if not is_admin(message.from_user.id): return
    parts = [p.strip() for p in message.text.split("|")]
    if len(parts) != 3:
        await message.answer("Invalid format.")
        return
    
    chat_id, title, link = parts
    cursor.execute("INSERT OR REPLACE INTO channels (chat_id, title, invite_link) VALUES (?, ?, ?)", (chat_id, title, link))
    conn.commit()
    await message.answer(f"✅ Channel '{title}' added successfully!")

# ================= রান =================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
