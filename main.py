import os
import tempfile
import uuid
import base64
from flask import Flask, request, abort
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from google import genai
from google.genai import types

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
WEBHOOK_BASE = os.environ["WEBHOOK_BASE"]
PORT = int(os.environ.get("PORT", "8080"))

env_keys = os.environ.get("GOOGLE_API_KEYS")
if env_keys:
    GOOGLE_API_KEYS = [k.strip() for k in env_keys.split(",") if k.strip()]
else:
    GOOGLE_API_KEYS = []

bot = telebot.TeleBot(TELEGRAM_TOKEN)
app = Flask(__name__)

VOICES = [
    "Leda","Zephyr","Puck","Kore","Fenrir","Aoede",
    "Callirrhoe","Orus","Autonoe","Achernar"
]

user_voice = {}
user_keys = {}
user_free_count = {}
env_key_index = 0

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

def save_bytes_to_file(path, b):
    with open(path, "wb") as f:
        f.write(b)

def try_generate_with_key(key, text, voice):
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
    return base64.b64decode(p) if isinstance(p, str) else bytes(p)

def generate_tts_for_user(user_id, text, voice):
    global env_key_index
    if user_id in user_keys:
        key = user_keys[user_id]
        try:
            return try_generate_with_key(key, text, voice)
        except Exception as e:
            raise e
    free = user_free_count.get(user_id, 0)
    if free < 2 and GOOGLE_API_KEYS:
        key = GOOGLE_API_KEYS[env_key_index % len(GOOGLE_API_KEYS)]
        env_key_index += 1
        try:
            audio = try_generate_with_key(key, text, voice)
            user_free_count[user_id] = free + 1
            return audio
        except Exception:
            pass
    updates = bot.get_updates()
    for u in updates:
        m = None
        if hasattr(u, "message") and u.message:
            m = u.message
        elif hasattr(u, "edited_message") and u.edited_message:
            m = u.edited_message
        if not m:
            continue
        text_found = getattr(m, "text", "") or getattr(m, "caption", "") or ""
        if not text_found:
            continue
        tokens = text_found.strip().split()
        for t in tokens:
            if t.startswith("Alza"):
                user_keys[user_id] = t
                try:
                    return try_generate_with_key(t, text, voice)
                except Exception as e:
                    raise e
    raise RuntimeError("no key available; please send your Gemini key (starts with Alza...)")

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

@bot.message_handler(func=lambda m: isinstance(m.text, str) and m.text.strip().startswith("Alza"))
def receive_key(m):
    key = m.text.strip()
    user_keys[m.from_user.id] = key
    bot.send_message(m.chat.id, "Key-ga waa la diiwaan geliyey oo waa khaas adiga. Lamaa wadaagi doono dadka kale.")

@bot.message_handler(content_types=["text"])
def tts(m):
    if m.text and m.text.strip().startswith("Alza"):
        return
    voice = user_voice.get(m.from_user.id, "Leda")
    bot.send_chat_action(m.chat.id, "upload_audio")
    try:
        pcm = generate_tts_for_user(m.from_user.id, m.text, voice)
    except Exception as e:
        bot.send_message(m.chat.id, "Ma aan helin key ama waxaa jira cilad. Fadlan soo dir key-gaaga Gemini (ku bilaabma Alza...) ama hubi GOOGLE_API_KEYS.")
        return
    path = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4().hex}.wav")
    save_bytes_to_file(path, pcm)
    with open(path, "rb") as f:
        bot.send_audio(m.chat.id, f, caption=f"Voice: {voice}")
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
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_BASE.rstrip("/") + "/webhook")
    app.run(host="0.0.0.0", port=PORT)
