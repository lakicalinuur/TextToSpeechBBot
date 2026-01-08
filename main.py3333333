import os
import asyncio
import time
import threading
from flask import Flask, request, abort
import telebot
import edge_tts
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, Update
import re

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8508232988:AAEZOvGOU9WNtC5JIhQWV68LL3gI3i-2RYg")
WEBHOOK_URL_BASE = os.environ.get("WEBHOOK_URL_BASE", "https://texttospeechbbot.onrender.com")
PORT = int(os.environ.get("PORT", "8080"))
WEBHOOK_PATH = os.environ.get("WEBHOOK_PATH", "/webhook/")
WEBHOOK_URL = WEBHOOK_URL_BASE.rstrip('/') + WEBHOOK_PATH if WEBHOOK_URL_BASE else ""
DOWNLOADS_DIR = os.environ.get("DOWNLOADS_DIR", "./downloads")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
flask_app = Flask(__name__)

ADMIN_ID = 6964068910
CURRENT_VOICE_NAME = "so-SO-MuuseNeural"
CURRENT_VOICE_LABEL = "Muuse 👨🏻‍🦱"

user_rate_input_mode = {}
user_pitch_input_mode = {}
user_rate_settings = {}
user_pitch_settings = {}

UNITS = {
    0: "eber", 1: "kow", 2: "labo", 3: "saddex", 4: "afar",
    5: "shan", 6: "lix", 7: "toddobo", 8: "siddeed", 9: "sagaal",
    10: "toban", 20: "labaatan", 30: "soddon", 40: "afartan",
    50: "konton", 60: "lixdan", 70: "toddobaatan", 80: "sideedan", 90: "sagaashan"
}

def number_to_somali(n: int, is_one_as_hal=False) -> str:
    if n == 1 and is_one_as_hal:
        return "hal"
    if n < 20:
        if n <= 10: return UNITS[n]
        return f"toban iyo {UNITS[n-10]}"
    if n < 100:
        tens = (n // 10) * 10
        rest = n % 10
        return UNITS[tens] if rest == 0 else f"{UNITS[tens]} iyo {UNITS[rest]}"
    if n < 1000:
        hundreds = n // 100
        rest = n % 100
        prefix = "boqol" if hundreds == 1 else f"{number_to_somali(hundreds, True)} boqol"
        if rest == 0: return prefix
        return f"{prefix} iyo {number_to_somali(rest)}"
    if n < 1000000:
        thousands = n // 1000
        rest = n % 1000
        prefix = "kun" if thousands == 1 else f"{number_to_somali(thousands, True)} kun"
        if rest == 0: return prefix
        return f"{prefix} iyo {number_to_somali(rest)}"
    if n < 1000000000:
        millions = n // 1000000
        rest = n % 1000000
        prefix = "malyan" if millions == 1 else f"{number_to_somali(millions, True)} malyan"
        if rest == 0: return prefix
        return f"{prefix} iyo {number_to_somali(rest)}"
    if n < 1000000000000:
        billions = n // 1000000000
        rest = n % 1000000000
        prefix = "bilyan" if billions == 1 else f"{number_to_somali(billions, True)} bilyan"
        if rest == 0: return prefix
        return f"{prefix} iyo {number_to_somali(rest)}"
    if n < 1000000000000000:
        trillions = n // 1000000000000
        rest = n % 1000000000000
        prefix = "trilyan" if trillions == 1 else f"{number_to_somali(trillions, True)} trilyan"
        if rest == 0: return prefix
        return f"{prefix} iyo {number_to_somali(rest)}"
    if n < 1000000000000000000:
        quadrillions = n // 1000000000000000
        rest = n % 1000000000000000
        prefix = "kuadrilyan" if quadrillions == 1 else f"{number_to_somali(quadrillions, True)} kuadrilyan"
        if rest == 0: return prefix
        return f"{prefix} iyo {number_to_somali(rest)}"
    return str(n)

def replace_numbers_with_words(text: str) -> str:
    text = text.replace("%", " boqolkiiba ")
    text = re.sub(r'(?<=\d),(?=\d)', '', text)
    text = re.sub(r"\$(\d+(\.\d+)?[kKmMbBtT]?)", r"\1 doolar", text)
    text = re.sub(r"€(\d+(\.\d+)?[kKmMbBtT]?)", r"\1 yuuro", text)
    text = re.sub(r"£(\d+(\.\d+)?[kKmMbBtT]?)", r"\1 bownd", text)
    text = re.sub(r"\b(\d+(\.\d+)?)[kK]\b", lambda m: str(float(m.group(1)) * 1000).rstrip('0').rstrip('.'), text)
    text = re.sub(r"\b(\d+(\.\d+)?)[mM]\b", lambda m: str(float(m.group(1)) * 1000000).rstrip('0').rstrip('.'), text)
    text = re.sub(r"\b(\d+(\.\d+)?)[bB]\b", lambda m: str(float(m.group(1)) * 1000000000).rstrip('0').rstrip('.'), text)
    text = re.sub(r"\b(\d+(\.\d+)?)[tT]\b", lambda m: str(float(m.group(1)) * 1000000000000).rstrip('0').rstrip('.'), text)

    def time_repl(match):
        hour = int(match.group(1))
        minute = int(match.group(2))
        ampm = match.group(3)
        if ampm:
            ampm_norm = ampm.lower().replace('.', '').strip()
        else:
            ampm_norm = None
        if ampm_norm:
            if 'p' in ampm_norm:
                if 1 <= hour <= 5:
                    period = "galabnimo"
                else:
                    period = "habeenimo"
            else:
                period = "subaxnimo"
        else:
            period = None
        hour_word = number_to_somali(hour)
        hour_label = f"{hour_word}dii"
        if minute == 0:
            return f"{hour_label} {period}" if period else f"{hour_label}"
        if minute == 30:
            return f"{hour_label} iyo barkii {period}" if period else f"{hour_label} iyo barkii"
        minute_word = number_to_somali(minute)
        minute_label = f"{minute_word}kii"
        return f"{hour_label} iyo {minute_label} {period}" if period else f"{hour_label} iyo {minute_label}"

    text = re.sub(r"\b([0-2]?\d):([0-5]\d)(?:\s*([AaPp]\.?\s*[Mm]\.?|[AaPp][Mm]))?\b", time_repl, text)

    def repl(match):
        num_str = match.group()
        if "." in num_str:
            parts = num_str.split(".")
            whole_num = int(parts[0])
            decimal_str = parts[1]
            whole_somali = number_to_somali(whole_num, is_one_as_hal=True)
            if len(decimal_str) <= 2:
                decimal_somali = number_to_somali(int(decimal_str))
            else:
                decimal_somali = " ".join([UNITS[int(d)] for d in decimal_str])
            return f"{whole_somali} dhibic {decimal_somali}"
        n = int(num_str)
        return number_to_somali(n, is_one_as_hal=(n == 1))
    return re.sub(r"\b\d+(\.\d+)?\b", repl, text)

def generate_tts_filename(user_id):
    safe_id = str(user_id).replace(" ", "_")
    return os.path.join(DOWNLOADS_DIR, f"Codka_{safe_id}_{int(time.time()*1000)}.mp3")

def create_voice_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    keyboard.add(KeyboardButton("Ubax 👩🏻‍🦳"), KeyboardButton("Muuse 👨🏻‍🦱"))
    return keyboard

@bot.message_handler(commands=["start"])
def start(message):
    keyboard = create_voice_keyboard()
    bot.send_message(
        message.chat.id,
        "Soo dhawow! Waxaan ahay Somali Text to Speech bot waxaa i samee yay zack3d:\n\nii soo dir qoraal si aan ugu badalo cod💗",
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
        "Immisa xawaare ayaan ku hadli karaa? Soo dir lambar u dhexeeya -100 ilaa +100, 0 waa caadi:"
    )

@bot.message_handler(commands=['pitch'])
def cmd_pitch(message):
    user_id = str(message.from_user.id)
    user_pitch_input_mode[user_id] = "awaiting_pitch_input"
    bot.send_message(
        message.chat.id,
        "Aan hagaajino codka (pitch)! Soo dir lambar u dhexeeya -100 ilaa +100, 0 waa caadi:"
    )

@bot.message_handler(func=lambda m: True, content_types=['text'])
def handle_text(message):
    user_id_str = str(message.from_user.id)
    admin_info = (
        f"@{message.from_user.username if message.from_user.username else 'No Username'}\n"
        f"Id: {message.from_user.id}\n"
        f"First: {message.from_user.first_name}\n"
        f"Lang: {message.from_user.language_code}\n"
        f"text {message.text}"
    )
    try:
        bot.send_message(ADMIN_ID, admin_info)
    except:
        pass
    if user_rate_input_mode.get(user_id_str) == "awaiting_rate_input":
        try:
            rate_val = int(message.text)
            if -100 <= rate_val <= 100:
                user_rate_settings[user_id_str] = rate_val
                user_rate_input_mode[user_id_str] = None
                bot.send_message(message.chat.id, f"🔊 Xawaaraha hadalka waxa la dejiyey: {rate_val}.")
            else:
                bot.send_message(message.chat.id, "❌ Qiime khaldan. Soo dir lambar u dhexeeya -100 ilaa +100. Isku day mar kale:")
        except ValueError:
            bot.send_message(message.chat.id, "Tani ma aha lambarka saxda ah. Soo dir lambar u dhexeeya -100 ilaa +100. Isku day mar kale:")
        return
    if user_pitch_input_mode.get(user_id_str) == "awaiting_pitch_input":
        try:
            pitch_val = int(message.text)
            if -100 <= pitch_val <= 100:
                user_pitch_settings[user_id_str] = pitch_val
                user_pitch_input_mode[user_id_str] = None
                bot.send_message(message.chat.id, f"🔊 Pitch-ka waa la dejiyey: {pitch_val}.")
            else:
                bot.send_message(message.chat.id, "❌ Pitch khaldan. Soo dir lambar u dhexeeya -100 ilaa +100. Isku day mar kale:")
        except ValueError:
            bot.send_message(message.chat.id, "Tani ma aha lambarka saxda ah. Soo dir lambar u dhexeeya -100 ilaa +100. Isku day mar kale:")
        return
    raw_text = message.text.replace("?", ", ")
    text = replace_numbers_with_words(raw_text)
    voice_name = CURRENT_VOICE_NAME
    filename = generate_tts_filename(user_id_str)
    async def make_tts():
        pitch_val = user_pitch_settings.get(user_id_str, 0)
        rate_val = user_rate_settings.get(user_id_str, 0)
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
        with open(filename, "rb") as audio:
            bot.send_audio(
                message.chat.id,
                audio,
                reply_to_message_id=message.message_id,
                title=f"Codka_{user_id_str}_{int(time.time())}",
                performer="SomTTS Bot"
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
