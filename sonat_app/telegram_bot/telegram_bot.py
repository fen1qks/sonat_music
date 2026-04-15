import requests
import telebot
from telebot import types

BOT_TOKEN = "8698711733:AAHEW2b5BIt0qYZYbed-6P3BOhiGb5GQxY8"

bot = telebot.TeleBot(BOT_TOKEN)

user_forms = {}


@bot.message_handler(commands=["start"])
def start_handler(message):
    sent = bot.send_message(
        message.chat.id,
        "Enter connected code:"
    )
    bot.register_next_step_handler(sent, process_code)

def process_code(message):
    if not message.text:
        bot.send_message(message.chat.id, "Enter only symbol code:")
        return

    code = message.text.strip().upper()

    payload = {
        "code": code,
        "telegram_id": str(message.from_user.id),
    }

    try:
        response = requests.post("http://localhost:8000/api/telegram/connected/", json=payload, timeout=10)
        data = response.json()

        if response.status_code == 200:
            bot.send_message(message.chat.id, "Account success linked")
            send_menu(message.chat.id)
        else:
            bot.send_message(
                message.chat.id,
                data.get("error", "Code not valid,try again")
            )

    except requests.RequestException:
        bot.send_message(message.chat.id, "Fail connect to server")
    except ValueError:
        bot.send_message(message.chat.id, "Backend error")

def send_menu(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("Add file", "Logout")
    bot.send_message(chat_id, "Choose action", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "Logout")
def logout_handler(message):
    payload = {
        "telegram_id": str(message.from_user.id),
    }

    try:
        response = requests.post(
            "http://localhost:8000/api/telegram/logout/",
            json=payload,
            timeout=10
        )
        data = response.json()

        if response.status_code == 200:
            markup = types.ReplyKeyboardRemove()
            sent = bot.send_message(
                message.chat.id,
                data.get("success", "Account successfully unlinked.\nEnter connected code:"),
                reply_markup=markup
            )
            bot.register_next_step_handler(sent, process_code)
        else:
            bot.send_message(
                message.chat.id,
                data.get("error", "Error logout")
            )

    except requests.RequestException:
        bot.send_message(message.chat.id, "Fail connect to server")

    except ValueError:
        bot.send_message(message.chat.id, "Backend error")

@bot.message_handler(func=lambda m: m.text == "Add file")
def add_file_handler(message):
    telegram_id = str(message.from_user.id)

    user_forms[telegram_id] = {
        "state": "wait_title"
    }

    sent = bot.send_message(message.chat.id, "Send title")
    bot.register_next_step_handler(sent, process_title)

def process_title(message):
    telegram_id = str(message.from_user.id)

    if not message.text:
        sent = bot.send_message(message.chat.id, "Send title as text")
        bot.register_next_step_handler(sent, process_title)
        return

    user_forms[telegram_id]["title"] = message.text.strip()
    user_forms[telegram_id]["state"] = "wait_author"

    sent = bot.send_message(message.chat.id, "Title saved. Send author")
    bot.register_next_step_handler(sent, process_author)

def process_author(message):
    telegram_id = str(message.from_user.id)

    if not message.text:
        sent = bot.send_message(message.chat.id, "Send author as text")
        bot.register_next_step_handler(sent, process_author)
        return

    user_forms[telegram_id]["author"] = message.text.strip()
    user_forms[telegram_id]["state"] = "wait_cover"

    sent = bot.send_message(message.chat.id, "Author saved. Send cover as photo:")
    bot.register_next_step_handler(sent, process_cover)

def process_cover(message):
    telegram_id = str(message.from_user.id)

    if not message.photo:
        sent = bot.send_message(message.chat.id, "Send cover as photo:")
        bot.register_next_step_handler(sent, process_cover)
        return

    cover_file_id = message.photo[-1].file_id

    user_forms[telegram_id]["cover_file_id"] = cover_file_id
    user_forms[telegram_id]["state"] = "wait_audio"

    sent = bot.send_message(message.chat.id, "Cover saved. Send audio file:")
    bot.register_next_step_handler(sent, process_audio)

def process_audio(message):
    telegram_id = str(message.from_user.id)

    file_id = None
    file_name = None

    if message.audio:
        file_id = message.audio.file_id
        file_name = message.audio.file_name or "track.mp3"
    elif message.document:
        file_id = message.document.file_id
        file_name = message.document.file_name or "track.mp3"

    if not file_id:
        sent = bot.send_message(message.chat.id, "Send audio or document:")
        bot.register_next_step_handler(sent, process_audio)
        return

    user_forms[telegram_id]["audio_file_id"] = file_id
    user_forms[telegram_id]["audio_filename"] = file_name
    user_forms[telegram_id]["state"] = "wait_confirm"

    data = user_forms[telegram_id]

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.row("Yes", "No")

    bot.send_message(
        message.chat.id,
        f"Confirm upload?\n\n"
        f"Title: {data['title']}\n"
        f"Author: {data['author']}",
        reply_markup=markup
    )

@bot.message_handler(func=lambda m: m.text in ["Yes", "No"])
def confirm_handler(message):
    telegram_id = str(message.from_user.id)

    session = user_forms.get(telegram_id)
    if not session or session.get("state") != "wait_confirm":
        return

    if message.text == "No":
        user_forms.pop(telegram_id, None)
        bot.send_message(message.chat.id, "Upload canceled.")
        send_menu(message.chat.id)
        return

    result = upload_form_db(telegram_id)

    if result["ok"]:
        user_forms.pop(telegram_id, None)
        bot.send_message(message.chat.id, "Track uploaded successfully.")
    else:
        bot.send_message(message.chat.id, result["error"])

    send_menu(message.chat.id)

def upload_form_db(telegram_id):
    form = user_forms.get(telegram_id)
    if not form:
        return {"ok": False, "error": "Forms not found"}

    try:
        cover_info = bot.get_file(form["cover_file_id"])
        cover_bytes = bot.download_file(cover_info.file_path)

        audio_info = bot.get_file(form["audio_file_id"])
        audio_bytes = bot.download_file(audio_info.file_path)

        data = {
            "telegram_id": telegram_id,
            "title": form["title"],
            "author": form["author"],
        }

        files = {
            "cover": ("cover.jpg", cover_bytes, "image/jpeg"),
            "audio": (form["audio_filename"], audio_bytes, "audio/mpeg"),
        }

        response = requests.post(
            "http://localhost:8000/api/telegram/upload_track/",
            data=data,
            files=files,
            timeout=30,
        )

        response_data = response.json()

        if response.status_code == 200:
            return {"ok": True}

        return {
            "ok": False,
            "error": response_data.get("error", "Upload error")
        }

    except requests.RequestException:
        return {"ok": False, "error": "Fail connect to server"}
    except ValueError:
        return {"ok": False, "error": "Backend returned invalid JSON"}
    except Exception:
        return {"ok": False, "error": "Unexpected error"}




if __name__ == "__main__":
    bot.infinity_polling(skip_pending=True)