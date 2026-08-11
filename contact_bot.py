import asyncio
import os
import sqlite3
from aiohttp import web
from pyrogram import Client, filters
from pyrogram.errors import UserNotParticipant
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

# ----- CONFIGURATION -----
API_ID = int(os.environ.get("API_ID", 12345678))
API_HASH = os.environ.get("API_HASH", "YOUR_API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN")
OWNER_ID = int(os.environ.get("OWNER_ID", 123456789))

# Force Sub Channel (Username like "MyChannel" OR ID like "-100123456789")
FORCE_SUB_CHANNEL = os.environ.get("FORCE_SUB_CHANNEL", None)

app = Client("ContactBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ----- DATABASE SETUP -----
conn = sqlite3.connect("users.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        lang TEXT DEFAULT 'en'
    )
"""
)
conn.commit()


def add_user(user_id):
    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id, lang) VALUES (?, 'en')",
        (user_id,),
    )
    conn.commit()


def set_user_lang(user_id, lang):
    cursor.execute(
        "UPDATE users SET lang = ? WHERE user_id = ?", (lang, user_id)
    )
    conn.commit()


def get_user_lang(user_id):
    cursor.execute("SELECT lang FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    return res[0] if res else "en"


def get_all_users():
    cursor.execute("SELECT user_id FROM users")
    return [row[0] for row in cursor.fetchall()]


# ----- TEXT DICTIONARY -----
TEXTS = {
    "hi": {
        "start": "👋 **नमस्ते!**\n\nआप मुझे जो भी मैसेज यहाँ भेजेंगे, वह सीधे एडमिन तक पहुँच जाएगा।",
        "lang_select": "कृपया अपनी भाषा चुनें / Please select your language:",
        "lang_set": "✅ **भाषा बदलकर 'हिंदी' कर दी गई है!**",
        "sent": "✅ **आपका संदेश एडमिन को भेज दिया गया है!**",
        "replied": "✅ **जवाब सफलतापूर्वक भेज दिया गया!**",
        "err_reply": "⚠️ **त्रुटि:** कृपया यूजर के फॉरवर्ड किए गए मैसेज पर ही 'Reply' करें।",
        "fsub_msg": "⚠️ **आपको बोट का उपयोग करने के लिए हमारे अपडेट चैनल को जॉइन करना होगा।**\n\nकृपया नीचे दिए गए बटन पर क्लिक करके चैनल जॉइन करें और फिर **Try Again** पर क्लिक करें।",
    },
    "en": {
        "start": "👋 **Hello!**\n\nAny message you send here will be forwarded directly to the admin.",
        "lang_select": "Please select your language:",
        "lang_set": "✅ **Language set to 'English'!**",
        "sent": "✅ **Your message has been sent to the admin!**",
        "replied": "✅ **Reply sent successfully!**",
        "err_reply": "⚠️ **Error:** Please 'Reply' directly to the forwarded user message.",
        "fsub_msg": "⚠️ **You must join our Updates Channel to use this bot.**\n\nPlease join using the button below, then click **Try Again**.",
    },
}


# ----- HELPER FUNCTION: FORCE SUB CHECK -----
async def check_force_sub(client: Client, user_id: int):
    if not FORCE_SUB_CHANNEL:
        return True  # If Force Sub is disabled

    try:
        chat_identifier = (
            int(FORCE_SUB_CHANNEL)
            if FORCE_SUB_CHANNEL.replace("-", "").isdigit()
            else FORCE_SUB_CHANNEL
        )
        member = await client.get_chat_member(chat_identifier, user_id)
        if member.status in ["kicked", "banned"]:
            return False
        return True
    except UserNotParticipant:
        return False
    except Exception as e:
        print(f"Force Sub Error: {e}")
        return True  # Bypass if channel not found or bot lacks permission


async def send_force_sub_message(client: Client, message, lang: str):
    channel = FORCE_SUB_CHANNEL.replace("@", "")
    if channel.replace("-", "").isdigit():
        chat = await client.get_chat(int(channel))
        invite_link = chat.invite_link or "https://t.me/"
    else:
        invite_link = f"https://t.me/{channel}"

    buttons = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📢 Join Channel", url=invite_link)],
            [InlineKeyboardButton("🔄 Try Again", callback_data="check_fsub_again")],
        ]
    )
    await message.reply_text(TEXTS[lang]["fsub_msg"], reply_markup=buttons)


# ----- DUMMY WEB SERVER -----
async def handle(request):
    return web.Response(text="Bot is running!")


# ----- COMMANDS & HANDLERS -----


# 1. Start Command
@app.on_message(filters.command("start") & filters.private)
async def start_handler(client: Client, message: Message):
    user_id = message.from_user.id
    add_user(user_id)
    lang = get_user_lang(user_id)

    # Force Sub Check
    if not await check_force_sub(client, user_id):
        await send_force_sub_message(client, message, lang)
        return

    buttons = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🇮🇳 हिंदी", callback_data="set_lang_hi"),
                InlineKeyboardButton("🇬🇧 English", callback_data="set_lang_en"),
            ]
        ]
    )
    await message.reply_text(TEXTS[lang]["start"], reply_markup=buttons)


# 2. Language Select Command
@app.on_message(filters.command("language") & filters.private)
async def language_command(client: Client, message: Message):
    user_id = message.from_user.id
    add_user(user_id)
    lang = get_user_lang(user_id)

    if not await check_force_sub(client, user_id):
        await send_force_sub_message(client, message, lang)
        return

    buttons = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🇮🇳 हिंदी", callback_data="set_lang_hi"),
                InlineKeyboardButton("🇬🇧 English", callback_data="set_lang_en"),
            ]
        ]
    )
    await message.reply_text(TEXTS[lang]["lang_select"], reply_markup=buttons)


# 3. Callback Queries (Language & Force Sub Check)
@app.on_callback_query()
async def callback_handler(client: Client, callback):
    data = callback.data
    user_id = callback.from_user.id
    lang = get_user_lang(user_id)

    if data.startswith("set_lang_"):
        lang_code = data.split("_")[-1]
        set_user_lang(user_id, lang_code)
        await callback.message.edit_text(TEXTS[lang_code]["lang_set"])

    elif data == "check_fsub_again":
        if await check_force_sub(client, user_id):
            await callback.message.delete()
            await callback.message.reply_text(
                "✅ **धन्यवाद! आप अब बोट का उपयोग कर सकते हैं।**\n\n"
                "✅ **Thank you! You can now use the bot.**"
            )
        else:
            await callback.answer(
                "❌ आपने अभी तक चैनल जॉइन नहीं किया है!\n❌ You haven't joined the channel yet!",
                show_alert=True,
            )


# 4. Broadcast Command (Admin Only)
@app.on_message(
    filters.command("broadcast") & filters.user(OWNER_ID) & filters.reply
)
async def broadcast_handler(client: Client, message: Message):
    users = get_all_users()
    reply_msg = message.reply_to_message

    success, failed = 0, 0
    status_msg = await message.reply_text(
        f"⏳ **ब्रॉडकास्ट शुरू हो रहा है...**\nकुल यूजर्स: {len(users)}"
    )

    for user in users:
        try:
            await reply_msg.copy(chat_id=user)
            success += 1
            await asyncio.sleep(0.05)
        except Exception:
            failed += 1

    await status_msg.edit_text(
        f"📢 **ब्रॉडकास्ट पूरा हुआ!**\n\n✅ **सफल:** {success}\n❌ **असफल:** {failed}"
    )


# 5. Forward Message to Admin
@app.on_message(
    filters.private
    & ~filters.user(OWNER_ID)
    & ~filters.command(["start", "language"])
)
async def forward_to_admin(client: Client, message: Message):
    user_id = message.from_user.id
    add_user(user_id)
    lang = get_user_lang(user_id)

    # Force Sub Check
    if not await check_force_sub(client, user_id):
        await send_force_sub_message(client, message, lang)
        return

    await message.forward(chat_id=OWNER_ID)
    await message.reply_text(TEXTS[lang]["sent"])


# 6. Admin Reply to User
@app.on_message(filters.private & filters.user(OWNER_ID) & filters.reply)
async def reply_to_user(client: Client, message: Message):
    if message.reply_to_message.text and message.reply_to_message.text.startswith("📢"):
        return

    if message.reply_to_message.forward_from:
        target_user_id = message.reply_to_message.forward_from.id
        await message.copy(chat_id=target_user_id)
        await message.reply_text(TEXTS["en"]["replied"])
    else:
        await message.reply_text(TEXTS["en"]["err_reply"])


# ----- APP STARTUP -----
async def start_services():
    web_app = web.Application()
    web_app.router.add_get("/", handle)
    runner = web.AppRunner(web_app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    await app.start()
    print("Bot is live with Force Sub, Multi-Language & Broadcast Features!")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(start_services())
    loop.run_forever()
