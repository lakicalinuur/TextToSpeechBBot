import os
import tempfile
import uuid
import base64
import wave
import re
import requests
from flask import Flask, request, abort
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from google import genai
from google.genai import types

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
WEBHOOK_BASE = os.environ.get("WEBHOOK_BASE", "")
PORT = int(os.environ.get("PORT", "8080"))
env_keys = os.environ.get("GOOGLE_API_KEYS")
if env_keys:
    ENV_GOOGLE_API_KEYS = [k.strip() for k in env_keys.split(",") if k.strip()]
else:
    ENV_GOOGLE_API_KEYS = []

bot = telebot.TeleBot(TELEGRAM_TOKEN)
app = Flask(__name__)

VOICES = [
    "Leda","Zephyr","Puck","Kore","Fenrir","Aoede",
    "Callirrhoe","Orus","Autonoe","Achernar"
]

user_voice = {}
user_key_info = {}

def voice_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    row = []
    for v in VOICES:
        row.append(KeyboardButton(v))
        if len(row) == 2:
            kb.add(*row)
            row = []
    if row:
        kb.add(*row)
    return kb

def write_wav(path, pcm, rate=24000):
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(pcm)

def generate_tts_with_key(text, voice, api_key):
    last_error = None
    try_keys = [api_key] if api_key else ENV_GOOGLE_API_KEYS
    for key in try_keys:
        try:
            client = genai.Client(api_key=key)
            r = client.models.generate_content(
                model="gemini-2.5-flash-preview-tts",
                contents=text,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name=voice
                            )
                        )
                    )
                )
            )
            p = r.candidates[0].content.parts[0].inline_data.data
            if isinstance(p, str):
                return base64.b64decode(p)
            else:
                return bytes(p)
        except Exception as e:
            last_error = e
    raise last_error

def extract_key_from_text(text):
    if not text:
        return None
    m = re.search(r"\b(Alza\S+)\b", text, re.IGNORECASE)
    if m:
        return m.group(1)
    return None

def find_key_in_recent_updates(user_id, chat_id):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
        resp = requests.get(url, params={"limit": 100})
        if resp.status_code != 200:
            return None
        data = resp.json()
        if not data.get("ok"):
            return None
        for upd in reversed(data.get("result", [])):
            msg = upd.get("message") or upd.get("edited_message")
            if not msg:
                continue
            from_ = msg.get("from") or {}
            if from_.get("id") != user_id:
                continue
            text = msg.get("text") or msg.get("caption") or ""
            key = extract_key_from_text(text)
            if key:
                return key
        return None
    except Exception:
        return None

@bot.message_handler(commands=["start"])
def start(m):
    bot.send_message(
        m.chat.id,
        "Dooro codka aad rabto kadib ii soo dir qoraal",
        reply_markup=voice_keyboard()
    )

@bot.message_handler(func=lambda m: m.text in VOICES)
def set_voice(m):
    user_voice[m.from_user.id] = m.text
    bot.send_message(m.chat.id, f"Codka waa la beddelay: {m.text}")

@bot.message_handler(func=lambda m: bool(extract_key_from_text(m.text)))
def receive_key_message(m):
    key = extract_key_from_text(m.text)
    if not key:
        bot.send_message(m.chat.id, "Ma helin key sax ah.")
        return
    user_key_info[m.from_user.id] = {"key": key, "uses": 0, "free_limit": 2}
    bot.send_message(m.chat.id, "Key waa la diiwaangeliyey (kaliya kayd xusuus gudaha ah).")

@bot.message_handler(content_types=["text"])
def tts(m):
    if m.text in VOICES:
        return
    uid = m.from_user.id
    info = user_key_info.get(uid)
    if not info:
        key_found = find_key_in_recent_updates(uid, m.chat.id)
        if key_found:
            user_key_info[uid] = {"key": key_found, "uses": 0, "free_limit": 2}
            info = user_key_info[uid]
    if not info:
        bot.send_message(m.chat.id, "Ma haysid key. Fadlan soo dir keygaaga oo ku bilaab Alza...")
        return
    if info.get("uses", 0) >= info.get("free_limit", 2):
        bot.send_message(m.chat.id, "Labo isticmaale oo bilaash ah waa laga gudbay. Mahadsanid.")
        return
    voice = user_voice.get(uid, "Leda")
    bot.send_chat_action(m.chat.id, "upload_audio")
    try:
        pcm = generate_tts_with_key(m.text, voice, api_key=info["key"])
    except Exception as e:
        bot.send_message(m.chat.id, f"Wax dhibaato ah ayaa ka dhacday: {str(e)}")
        return
    path = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4().hex}.wav")
    try:
        write_wav(path, pcm)
        with open(path, "rb") as f:
            bot.send_audio(m.chat.id, f, caption=f"Voice: {voice}")
        info["uses"] = info.get("uses", 0) + 1
    finally:
        try:
            os.remove(path)
        except Exception:
            pass

@app.route("/", methods=["GET"])
def home():
    return "ok", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    if request.headers.get("content-type") == "application/json":
        update = telebot.types.Update.de_json(request.data.decode("utf-8"))
        bot.process_new_updates([update])
        return "", 200
    abort(403)

if __name__ == "__main__":
    try:
        bot.remove_webhook()
    except Exception:
        pass
    if WEBHOOK_BASE:
        bot.set_webhook(url=WEBHOOK_BASE.rstrip("/") + "/webhook")
        app.run(host="0.0.0.0", port=PORT)
    else:
        bot.infinity_polling()
