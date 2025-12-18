import os
import asyncio
import time
import threading
from flask import Flask, request, abort
import telebot
import edge_tts
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, Update

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8508232988:AAEZOvGOU9WNtC5JIhQWV68LL3gI3i-2RYg")
WEBHOOK_URL_BASE = os.environ.get("WEBHOOK_URL_BASE", "https://texttospeechbbot.onrender.com")
PORT = int(os.environ.get("PORT", "8080"))
WEBHOOK_PATH = os.environ.get("WEBHOOK_PATH", "/webhook/")
WEBHOOK_URL = WEBHOOK_URL_BASE.rstrip('/') + WEBHOOK_PATH if WEBHOOK_URL_BASE else ""
DOWNLOADS_DIR = os.environ.get("DOWNLOADS_DIR", "./downloads")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
flask_app = Flask(__name__)

CURRENT_VOICE_NAME = "so-SO-MuuseNeural"
CURRENT_VOICE_LABEL = "Muuse 👨🏻‍🦱"

user_rate_input_mode = {}
user_pitch_input_mode = {}
user_rate_settings = {}
user_pitch_settings = {}

def generate_tts_filename():
    return os.path.join(DOWNLOADS_DIR, f"tts_output_{int(time.time()*1000)}.mp3")

def create_voice_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    keyboard.add(KeyboardButton("Ubax 👩🏻‍🦳"), KeyboardButton("Muuse 👨🏻‍🦱"))
    return keyboard

@bot.message_handler(commands=["start"])
def start(message):
    keyboard = create_voice_keyboard()
    bot.send_message(
        message.chat.id,
        f"Soo dhawow! Waxaan ahay Somali Text-to-Speech bot. Codka asalka ah waa: {CURRENT_VOICE_LABEL}\n\nIi soo dir qoraal si aan u badalo cod💗",
        reply_markup=keyboard,
        reply_to_message_id=message.message_id
    )

@bot.message_handler(func=lambda m: m.text in ["Ubax 👩🏻‍🦳", "Muuse 👨🏻‍🦱"])
def set_voice(message):
    global CURRENT_VOICE_NAME, CURRENT_VOICE_LABEL
    choice = message.text
    if "Ubax" in choice:
        CURRENT_VOICE_NAME = "so-SO-UbaxNeural"
        CURRENT_VOICE_LABEL = "Ubax 👩🏻‍🦳"
    elif "Muuse" in choice:
        CURRENT_VOICE_NAME = "so-SO-MuuseNeural"
        CURRENT_VOICE_LABEL = "Muuse 👨🏻‍🦱"
    bot.send_message(
        message.chat.id,
        "OK, ii soo dir qoraalka.",
        reply_to_message_id=message.message_id
    )

def keep_sending_upload_action(chat_id, stop_event, interval=3):
    while not stop_event.is_set():
        try:
            bot.send_chat_action(chat_id, "upload_audio")
        except Exception:
            pass
        time.sleep(interval)

@bot.message_handler(commands=['rate'])
def cmd_rate(message):
    user_id = str(message.from_user.id)
    user_rate_input_mode[user_id] = "awaiting_rate_input"
    bot.send_message(
        message.chat.id,
        "Immisa xawaare ayaan ku hadli karaa? Soo dir lambar u dhexeeya -100 (aad u gaabis) ilaa +100 (aad u dhaqsiyo), 0 waa caadi:"
    )

@bot.message_handler(commands=['pitch'])
def cmd_pitch(message):
    user_id = str(message.from_user.id)
    user_pitch_input_mode[user_id] = "awaiting_pitch_input"
    bot.send_message(
        message.chat.id,
        "Aan hagaajino codka (pitch)! Soo dir lambar u dhexeeya -100 (hoose) ilaa +100 (sare), 0 waa caadi:"
    )

@bot.message_handler(func=lambda m: True, content_types=['text'])
def handle_text(message):
    user_id = str(message.from_user.id)
    if user_rate_input_mode.get(user_id) == "awaiting_rate_input":
        try:
            rate_val = int(message.text)
            if -100 <= rate_val <= 100:
                user_rate_settings[user_id] = rate_val
                user_rate_input_mode[user_id] = None
                bot.send_message(message.chat.id, f"🔊 Xawaaraha hadalka waxa la dejiyey: {rate_val}.")
            else:
                bot.send_message(message.chat.id, "❌ Qiime khaldan. Soo dir lambar u dhexeeya -100 ilaa +100 (0 waa caadi). Isku day mar kale:")
        except ValueError:
            bot.send_message(message.chat.id, "Tani ma aha lambarka saxda ah. Soo dir lambar u dhexeeya -100 ilaa +100 (0 waa caadi). Isku day mar kale:")
        return

    if user_pitch_input_mode.get(user_id) == "awaiting_pitch_input":
        try:
            pitch_val = int(message.text)
            if -100 <= pitch_val <= 100:
                user_pitch_settings[user_id] = pitch_val
                user_pitch_input_mode[user_id] = None
                bot.send_message(message.chat.id, f"🔊 Pitch-ka waa la dejiyey: {pitch_val}.")
            else:
                bot.send_message(message.chat.id, "❌ Pitch khaldan. Soo dir lambar u dhexeeya -100 ilaa +100 (0 waa caadi). Isku day mar kale:")
        except ValueError:
            bot.send_message(message.chat.id, "Tani ma aha lambarka saxda ah. Soo dir lambar u dhexeeya -100 ilaa +100 (0 waa caadi). Isku day mar kale:")
        return

    text = message.text.replace(".", ",")
    voice_name = CURRENT_VOICE_NAME
    filename = generate_tts_filename()

    async def make_tts():
        pitch_val = user_pitch_settings.get(user_id, 0)
        rate_val = user_rate_settings.get(user_id, 0)
        pitch = f"+{pitch_val}Hz" if pitch_val >= 0 else f"{pitch_val}Hz"
        rate = f"+{rate_val}%" if rate_val >= 0 else f"{rate_val}%"
        tts = edge_tts.Communicate(text, voice_name, rate=rate, pitch=pitch)
        await tts.save(filename)

    stop_event = threading.Event()
    action_thread = threading.Thread(target=keep_sending_upload_action, args=(message.chat.id, stop_event))
    action_thread.daemon = True
    action_thread.start()

    try:
        asyncio.run(make_tts())
        with open(filename, "rb") as voice:
            bot.send_voice(
                message.chat.id,
                voice,
                reply_to_message_id=message.message_id
            )
    except Exception as e:
        bot.send_message(
            message.chat.id,
            f"Khalad: {e}",
            reply_to_message_id=message.message_id
        )
    finally:
        stop_event.set()
        try:
            if os.path.exists(filename):
                os.remove(filename)
        except:
            pass

@flask_app.route("/", methods=["GET"])
def index():
    return "Bot-ka wuu socdaa💗", 200

@flask_app.route(WEBHOOK_PATH, methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        raw = request.get_data().decode('utf-8')
        bot.process_new_updates([Update.de_json(raw)])
        return '', 200
    abort(403)

if __name__ == "__main__":
    if WEBHOOK_URL:
        bot.remove_webhook()
        time.sleep(0.5)
        bot.set_webhook(url=WEBHOOK_URL)
        flask_app.run(host="0.0.0.0", port=PORT)
    else:
        print("Webhook URL lama dhisin, waan baxayaa.")
