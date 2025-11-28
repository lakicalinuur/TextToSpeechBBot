import os
import tempfile
import uuid
import base64
import wave
import json
import threading
from flask import Flask, request, abort
from google import genai
from google.genai import types
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN environment variable is required")
WEBHOOK_BASE = os.environ.get("WEBHOOK_BASE", "")
if not WEBHOOK_BASE:
    raise RuntimeError("WEBHOOK_BASE environment variable is required")
PORT = int(os.environ.get("PORT", "8080"))
REQUIRED_CHANNEL = os.environ.get("REQUIRED_CHANNEL", "")
USER_SUCCESS_PATH = "user_success.json"
USER_FREE_USES = int(os.environ.get("USER_FREE_USES", "3"))

env_keys = os.environ.get("GOOGLE_API_KEYS")
if env_keys:
    GOOGLE_API_KEYS = [k.strip() for k in env_keys.split(",") if k.strip()]
else:
    single_key = os.environ.get("GOOGLE_API_KEY")
    GOOGLE_API_KEYS = [single_key] if single_key else []
if not GOOGLE_API_KEYS:
    raise RuntimeError("Set GOOGLE_API_KEYS (comma-separated) or GOOGLE_API_KEY in environment")

bot = telebot.TeleBot(TELEGRAM_TOKEN)
user_voice = {}
VOICES = [
    "Zephyr","Puck","Charon","Kore","Fenrir","Leda","Orus","Aoede","Callirrhoe",
    "Autonoe","Enceladus","Iapetus","Umbriel","Algieba","Despina","Erinome",
    "Algenib","Rasalgethi","Laomedeia","Achernar","Alnilam","Schedar","Gacrux",
    "Pulcherrima","Achird","Zubenelgenubi","Vindemiatrix","Sadachbia",
    "Sadalager","Sulafat"
]

user_success = {}
user_success_lock = threading.Lock()

def load_user_success():
    global user_success
    try:
        if os.path.exists(USER_SUCCESS_PATH):
            with open(USER_SUCCESS_PATH, "r") as f:
                content = f.read()
                if content:
                    raw = json.loads(content)
                    user_success = {int(k): int(v) for k, v in raw.items()}
                else:
                    user_success = {}
        else:
            user_success = {}
    except Exception:
        user_success = {}

def save_user_success():
    try:
        with user_success_lock:
            serial = {str(k): v for k, v in user_success.items()}
            with open(USER_SUCCESS_PATH, "w") as f:
                f.write(json.dumps(serial))
    except Exception:
        pass

def increment_user_success(uid: int):
    with user_success_lock:
        count = user_success.get(uid, 0) + 1
        user_success[uid] = count
        try:
            serial = {str(k): v for k, v in user_success.items()}
            with open(USER_SUCCESS_PATH, "w") as f:
                f.write(json.dumps(serial))
        except Exception:
            pass
        return count

def get_user_success(uid: int):
    with user_success_lock:
        return user_success.get(uid, 0)

def write_wav(path, pcm_bytes, channels=1, rate=24000, sample_width=2):
    with wave.open(path, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(pcm_bytes)

def make_voice_keyboard():
    markup = InlineKeyboardMarkup(row_width=3)
    buttons = []
    for v in VOICES:
        buttons.append(InlineKeyboardButton(v, callback_data=f"select_voice|{v}"))
    for i in range(0, len(buttons), 3):
        row = buttons[i:i+3]
        markup.add(*row)
    return markup

def clean_channel_username():
    return REQUIRED_CHANNEL.lstrip("@").strip()

def send_join_prompt(chat_id):
    clean = clean_channel_username()
    kb = InlineKeyboardMarkup()
    if clean:
        kb.add(InlineKeyboardButton("🔗 Join Channel", url=f"https://t.me/{clean}"))
    text = f"🚫 Please join our channel {REQUIRED_CHANNEL} to continue using this bot\n\nAfter joining, send the text again"
    try:
        bot.send_message(chat_id, text, reply_markup=kb)
    except Exception:
        try:
            bot.send_message(chat_id, "🚫 Please join the channel to continue.")
        except Exception:
            pass

def is_user_in_channel(user_id: int):
    if not REQUIRED_CHANNEL:
        return True
    clean = clean_channel_username()
    target = f"@{clean}" if clean and not clean.startswith("@") else clean
    try:
        member = bot.get_chat_member(target, user_id)
        status = getattr(member, "status", None)
        return status in ("member", "administrator", "creator", "restricted")
    except Exception:
        return False

def ensure_joined(user_id: int, chat_id: int):
    try:
        free_count = get_user_success(user_id)
        if free_count < USER_FREE_USES:
            return True
    except Exception:
        pass
    try:
        if is_user_in_channel(user_id):
            return True
    except Exception:
        pass
    try:
        send_join_prompt(chat_id)
    except Exception:
        try:
            bot.send_message(chat_id, "🚫 Please join the channel to continue.")
        except Exception:
            pass
    return False

def generate_audio_pcm_with_key_rotation(text, voice):
    last_exception = None
    for key in GOOGLE_API_KEYS:
        try:
            client = genai.Client(api_key=key)
            response = client.models.generate_content(
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
            if not response or not getattr(response, "candidates", None):
                raise Exception("empty response or no candidates")
            candidate = response.candidates[0]
            part = candidate.content.parts[0]
            data = part.inline_data.data
            if isinstance(data, str):
                pcm = base64.b64decode(data)
            else:
                pcm = bytes(data)
            return pcm
        except Exception as e:
            last_exception = e
            continue
    raise last_exception if last_exception is not None else Exception("failed to generate audio")

@bot.callback_query_handler(func=lambda call: call.data and call.data.startswith("select_voice|"))
def on_select_voice(call):
    try:
        _, v = call.data.split("|", 1)
        user_voice[call.from_user.id] = v
        try:
            bot.answer_callback_query(call.id)
        except Exception:
            pass
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass
    except Exception:
        try:
            bot.answer_callback_query(call.id)
        except Exception:
            pass

@bot.message_handler(commands=["start"])
def send_welcome(message):
    bot.send_message(message.chat.id, "Choose a voice from the buttons below:", reply_markup=make_voice_keyboard())

@bot.message_handler(func=lambda m: True, content_types=["text"])
def tts_handler(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    text = message.text.strip()
    if not text:
        bot.send_message(chat_id, "Please write some text.")
        return
    if not ensure_joined(user_id, chat_id):
        return
    voice = user_voice.get(user_id, "Kore")
    try:
        bot.send_chat_action(chat_id, "upload_audio")
        pcm = generate_audio_pcm_with_key_rotation(text, voice)
        tmp_dir = tempfile.gettempdir()
        unique_id = uuid.uuid4().hex[:8]
        fname = f"{voice}_{unique_id}.wav"
        path = os.path.join(tmp_dir, fname)
        write_wav(path, pcm)
        with open(path, "rb") as audio_file:
            bot.send_audio(chat_id, audio_file, caption=f"your Voice: {voice} 😝")
        try:
            os.remove(path)
        except Exception:
            pass
        try:
            new_count = increment_user_success(user_id)
        except Exception:
            pass
    except Exception as e:
        try:
            bot.send_message(chat_id, f"Error: {e}")
        except Exception:
            pass

flask_app = Flask(__name__)
WEBHOOK_PATH = "/bot_webhook"
WEBHOOK_URL = WEBHOOK_BASE.rstrip("/") + WEBHOOK_PATH

@flask_app.route("/", methods=["GET", "POST", "HEAD"])
def keep_alive():
    return "Bot is alive", 200

@flask_app.route(WEBHOOK_PATH, methods=["GET", "POST", "HEAD"])
def webhook():
    if request.method == "GET" or request.method == "HEAD":
        return "ok", 200
    if request.headers.get('content-type') == 'application/json':
        try:
            update = telebot.types.Update.de_json(request.data.decode('utf-8'))
            bot.process_new_updates([update])
            return '', 200
        except Exception:
            abort(400)
    else:
        abort(403)

@flask_app.route("/set_webhook", methods=["GET"])
def set_wh():
    try:
        bot.remove_webhook()
    except Exception:
        pass
    try:
        bot.set_webhook(url=WEBHOOK_URL)
        return f"ok {WEBHOOK_URL}", 200
    except Exception:
        return "error", 500

@flask_app.route("/delete_webhook", methods=["GET"])
def del_wh():
    try:
        bot.delete_webhook()
        return "deleted", 200
    except Exception:
        return "error", 500

if __name__ == "__main__":
    load_user_success()
    try:
        bot.set_webhook(url=WEBHOOK_URL)
    except Exception:
        pass
    flask_app.run(host="0.0.0.0", port=PORT)
