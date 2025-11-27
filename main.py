import os
import tempfile
import uuid
import base64
import wave
import json
from google import genai
from google.genai import types
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask, request, abort

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN environment variable is required")

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

app = Flask(__name__)
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
WEBHOOK_PORT = int(os.environ.get("PORT", 5000))

VOICES = [
    "Zephyr","Puck","Charon","Kore","Fenrir","Leda","Orus","Aoede","Callirrhoe",
    "Autonoe","Enceladus","Iapetus","Umbriel","Algieba","Despina","Erinome",
    "Algenib","Rasalgethi","Laomedeia","Achernar","Alnilam","Schedar","Gacrux",
    "Pulcherrima","Achird","Zubenelgenubi","Vindemiatrix","Sadachbia",
    "Sadalager","Sulafat"
]

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
        markup.add(*buttons[i:i+3])
    return markup

@bot.message_handler(commands=["start"])
def send_welcome(message):
    bot.send_message(message.chat.id, "Choose a voice from the buttons below:", reply_markup=make_voice_keyboard())

@bot.callback_query_handler(func=lambda call: call.data and call.data.startswith("select_voice|"))
def on_select_voice(call):
    try:
        _, v = call.data.split("|", 1)
        user_voice[call.from_user.id] = v
        bot.answer_callback_query(call.id)
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass
    except Exception:
        try:
            bot.answer_callback_query(call.id)
        except Exception:
            pass

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
                    ),
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
    if last_exception:
        raise Exception("too many requests try next day waqtigan camal 😜")
    else:
        raise Exception("failed to generate audio")

@bot.message_handler(func=lambda m: True, content_types=["text"])
def tts_handler(message):
    chat_id = message.chat.id
    text = message.text.strip()
    if not text:
        bot.send_message(chat_id, "Please write some text.")
        return
    voice = user_voice.get(message.from_user.id, "Kore")
    try:
        bot.send_chat_action(chat_id, "upload_audio")
        pcm = generate_audio_pcm_with_key_rotation(text, voice)
        tmp_dir = tempfile.gettempdir()
        unique_id = uuid.uuid4().hex[:8]
        fname = f"{voice}_{unique_id}.wav"
        path = os.path.join(tmp_dir, fname)
        write_wav(path, pcm)
        with open(path, "rb") as audio_file:
            bot.send_audio(chat_id, audio_file, caption=f"Voice: {voice}")
        try:
            os.remove(path)
        except Exception:
            pass
    except Exception as e:
        if "too many requests try next day waqtigan camal 😜" in str(e):
            bot.send_message(chat_id, "error too many requests try next day waqtigan camal 😜")
        else:
            bot.send_message(chat_id, f"Error: {e}")

@app.route("/", methods=["GET", "POST", "HEAD"])
def webhook():
    if request.method == "POST":
        if request.headers.get("content-type") == "application/json":
            json_string = request.get_data().decode("utf-8")
            update = telebot.types.Update.de_json(json_string)
            bot.process_new_updates([update])
            return "ok"
        else:
            abort(403)
    return "Bot is running", 200

if __name__ == "__main__":
    if WEBHOOK_URL:
        bot.remove_webhook()
        bot.set_webhook(url=WEBHOOK_URL)
        app.run(host="0.0.0.0", port=WEBHOOK_PORT, debug=False)
    else:
        bot.polling(non_stop=True, skip_pending=True)
