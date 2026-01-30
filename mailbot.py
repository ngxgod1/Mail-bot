import imaplib
import email
import re
import threading
import time
import random

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ---------------- CONFIG ----------------

API_ID = 35453559
API_HASH = "780f66f0990d6f791d7fa5384480e60"
BOT_TOKEN = "8517596492:AAFRG7XaV9QzJbClCT0DCLg8NtfQfhHggY0"

IMAP_SERVER = "imap.gmail.com"

CHANNEL_LINK = "https://t.me/TeamOFDark1"

app = Client(
    "mailotpbot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

users = {}
joined_users = set()

# ---------------- BUTTONS ----------------

def join_buttons():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔔 Must Join", url=CHANNEL_LINK)],
        [InlineKeyboardButton("✅ I Joined", callback_data="checkjoin")]
    ])

def main_buttons():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📩 Get Code", callback_data="get")],
        [
            InlineKeyboardButton("▶ Start OTP", callback_data="startotp"),
            InlineKeyboardButton("🛑 Stop OTP", callback_data="stop")
        ],
        [InlineKeyboardButton("✉ Generate Case-Email", callback_data="gen")],
        [InlineKeyboardButton("🔁 Change Email", callback_data="change")]
    ])

# ---------------- START ----------------

@app.on_message(filters.command("start"))
def start(client, message):
    uid = message.from_user.id

    if uid not in joined_users:
        message.reply(
            "❌ You must join our channel first!",
            reply_markup=join_buttons()
        )
        return

    users.pop(uid, None)
    message.reply("📧 Send your EMAIL address:")

# ---------------- RECEIVE ----------------

@app.on_message(filters.text & ~filters.command(["start"]))
def receive(client, message):
    uid = message.from_user.id

    if uid not in joined_users:
        message.reply(
            "❌ You must join our channel first!",
            reply_markup=join_buttons()
        )
        return

    text = message.text.strip()

    if uid not in users:
        users[uid] = {
            "email": text,
            "running": False,
            "last_otp": None
        }
        message.reply("🔑 Send EMAIL APP PASSWORD:")
        return

    if "password" not in users[uid]:
        users[uid]["password"] = text
        message.reply("✅ Email saved!", reply_markup=main_buttons())

# ---------------- MAIL CONNECT ----------------

def connect_mail(uid):
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(users[uid]["email"], users[uid]["password"])
    mail.select("inbox")
    return mail

# ---------------- FETCH OTP ----------------

def fetch_otp(mail):
    status, data = mail.search(None, '(FROM "noreply@telegram.org")')
    ids = data[0].split()
    if not ids:
        return None

    latest = ids[-1]
    status, msg_data = mail.fetch(latest, "(RFC822)")
    msg = email.message_from_bytes(msg_data[0][1])

    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                body = part.get_payload(decode=True).decode(errors="ignore")
    else:
        body = msg.get_payload(decode=True).decode(errors="ignore")

    m = re.search(r"\b\d{5,6}\b", body)
    return m.group() if m else None

# ---------------- LISTENER ----------------

def listen_mail(uid):
    try:
        mail = connect_mail(uid)
        app.send_message(uid, "📬 Connected to mailbox!")
    except:
        app.send_message(uid, "❌ Email login failed")
        return

    while users.get(uid, {}).get("running"):
        try:
            otp = fetch_otp(mail)
            if otp and otp != users[uid]["last_otp"]:
                users[uid]["last_otp"] = otp
                app.send_message(uid, f"🔐 OTP: {otp}")
        except:
            pass
        time.sleep(3)

# ---------------- CALLBACKS ----------------

@app.on_callback_query()
def callbacks(client, callback):
    uid = callback.from_user.id

    # I JOINED BUTTON
    if callback.data == "checkjoin":
        joined_users.add(uid)
        callback.message.reply_text("✅ Verified! Now send /start")
        return

    if uid not in joined_users:
        callback.message.reply_text(
            "❌ You must join our channel first!",
            reply_markup=join_buttons()
        )
        return

    if uid not in users:
        callback.message.reply_text("⚠️ Send /start first")
        return

    if callback.data == "startotp":
        users[uid]["running"] = True
        threading.Thread(
            target=listen_mail,
            args=(uid,),
            daemon=True
        ).start()
        callback.message.reply_text("▶ OTP Listener Started")

    elif callback.data == "stop":
        users[uid]["running"] = False
        callback.message.reply_text("🛑 OTP Listener Stopped")

    elif callback.data == "change":
        users.pop(uid, None)
        callback.message.reply_text("📧 Send new EMAIL:")

    elif callback.data == "gen":
        base = users[uid]["email"]
        name, domain = base.split("@")
        newname = "".join(
            random.choice([c.upper(), c.lower()]) for c in name
        )
        callback.message.reply_text(
            f"Generated Email:\n{newname}@{domain}"
        )

    elif callback.data == "get":
        try:
            mail = connect_mail(uid)
            otp = fetch_otp(mail)
            if otp:
                callback.message.reply_text(f"🔐 OTP: {otp}")
            else:
                callback.message.reply_text("❌ No OTP found")
        except:
            callback.message.reply_text("❌ Mail error")

# ---------------- RUN ----------------

app.run()