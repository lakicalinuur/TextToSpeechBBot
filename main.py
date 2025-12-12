import os
import asyncio
import time
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

# Liiska Codadka
VOICES = {
    "Ubax 👩🏻‍🦳": "so-SO-UbaxNeural",
    "Muuse 👨🏻‍🦱": "so-SO-MuuseNeural",
    "Marcello 👨🏻": "it-IT-MarcelloMultilingualNeural" # Codka Cusub
}

# Codka Default-ka ah
CURRENT_VOICE_LABEL = "Muuse 👨🏻‍🦱"
CURRENT_VOICE_NAME = VOICES[CURRENT_VOICE_LABEL]

def generate_tts_filename():
    return os.path.join(DOWNLOADS_DIR, f"tts_output_{int(time.time()*1000)}.mp3")

def create_voice_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False, row_width=2)
    # Ku dar badhamada codadka oo ku jira laba saf
    voice_buttons = [KeyboardButton(label) for label in VOICES.keys()]
    keyboard.add(*voice_buttons)
    return keyboard

@bot.message_handler(commands=["start"])
def start(message):
    keyboard = create_voice_keyboard()
    bot.send_message(
        message.chat.id,
        f"Soo dhawow waxaan ahay Somali Text to Speech bot! default voice waa: {CURRENT_VOICE_LABEL}\n\nQoraal ii soo dir si aan cod ugu badalo💗",
        reply_markup=keyboard,
        reply_to_message_id=message.message_id
    )

@bot.message_handler(func=lambda m: m.text in VOICES.keys())
def set_voice(message):
    global CURRENT_VOICE_NAME, CURRENT_VOICE_LABEL
    choice = message.text
    
    # Hubi in codka la doortay uu ku jiro liiska VOICES
    if choice in VOICES:
        CURRENT_VOICE_LABEL = choice
        CURRENT_VOICE_NAME = VOICES[choice]
        
        bot.send_message(
            message.chat.id,
            f"Okey. Hadda waxaad dooratay codka: **{CURRENT_VOICE_LABEL}**. Fadlan Ii soo dir qoraalka.",
            parse_mode='Markdown',
            reply_to_message_id=message.message_id
        )
    else:
        # Tani ma dhacayso haddii badhamada si sax ah loo isticmaalo, laakiin waa difaac
        bot.send_message(
            message.chat.id,
            "Fadlan dooro mid ka mid ah codadka la heli karo.",
            reply_to_message_id=message.message_id
        )

@bot.message_handler(func=lambda m: True, content_types=['text'])
def handle_text(message):
    text = message.text.replace(".", "،")
    voice_name = CURRENT_VOICE_NAME
    filename = generate_tts_filename()
    chat_id = message.chat.id

    # 1. Muuji in botku hawsha bilaabay (upload audio)
    bot.send_chat_action(chat_id, "upload_audio")

    async def make_tts():
        tts = edge_tts.Communicate(text, voice_name)
        await tts.save(filename)

    try:
        asyncio.run(make_tts())
        
        # 2. Marka uu codku diyaar noqdo, u dir userka
        with open(filename, "rb") as voice:
            bot.send_voice(
                chat_id,
                voice,
                reply_to_message_id=message.message_id
            )
    except Exception as e:
        # Xaaladaha khaladaadka
        bot.send_message(
            chat_id,
            f"Wuu dhacay khalad inta aan sameynayay codka: {e}",
            reply_to_message_id=message.message_id
        )
    finally:
        # Nadiifi faylka markasta
        try:
            if os.path.exists(filename):
                os.remove(filename)
        except:
            # Ka gudub khaladaadka haddii tirtiristu ay fashilanto
            pass

@flask_app.route("/", methods=["GET"])
def index():
    return "Bot Running💗", 200

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
        print("Webhook URL not set, exiting.")
