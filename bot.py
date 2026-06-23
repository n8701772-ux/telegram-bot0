import telebot
from telebot.types import Message
import time
from collections import defaultdict
from datetime import datetime
import random

TOKEN = "8666576626:AAHFlk3KhsRsmBnd_YjGZ_YsO7YblsA5vw4"

bot = telebot.TeleBot(TOKEN)

users = {}
waiting_list = []
chats = {} 
chat_messages = defaultdict(list)

# ==============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ==============================================

def format_timestamp(timestamp):
    return datetime.fromtimestamp(timestamp).strftime('%d.%m.%Y %H:%M:%S')

def get_username(user_id):
    return users.get(user_id, {}).get('username', str(user_id))

# ==============================================
# ОСНОВНЫЕ ФУНКЦИИ
# ==============================================

def send_welcome(message):
    user_id = message.from_user.id
    username = message.from_user.username or str(user_id)
    
    users[user_id] = {
        "state": "none",
        "partner_id": None,
        "chat_id": None,
        "username": username
    }
    
    bot.send_message(
        message.chat.id,
        "🔥 *ANONIM CHAT* 🔥\n\n"
        "Анонимное общение без границ.\n"
        "Никаких запретов. Всё разрешено.\n\n"
        "👤 *Создатель: Белый Дарон*\n\n"
        "📌 Команды:\n"
        "/find - Найти собеседника\n"
        "/leave - Выйти из чата\n"
        "/help - Помощь",
        parse_mode='Markdown'
    )

def show_help(message):
    bot.send_message(
        message.chat.id,
        "📋 *Команды ANONIM CHAT:*\n\n"
        "/find - Найти собеседника\n"
        "/leave - Выйти из чата\n"
        "/help - Помощь\n\n"
        "💬 Всё анонимно. Без регистрации.\n"
        "🔞 Всё разрешено. Без цензуры.\n\n"
        "👤 Создатель: Белый Дарон",
        parse_mode='Markdown'
    )

def find_partner(message):
    user_id = message.from_user.id
    
    if user_id not in users:
        send_welcome(message)
        return
    
    if users[user_id]["state"] != "none":
        bot.send_message(message.chat.id, "❌ Ты уже в чате или в поиске")
        return
    
    users[user_id]["state"] = "waiting"
    waiting_list.append(user_id)
    
    bot.send_message(message.chat.id, "🔍 Ищем собеседника...")
    try_find_pair()

def try_find_pair():
    while len(waiting_list) >= 2:
        user1 = waiting_list.pop(0)
        user2 = waiting_list.pop(0)
        
        if users[user1]["state"] != "waiting" or users[user2]["state"] != "waiting":
            continue
        
        chat_id = f"{user1}_{user2}_{int(time.time())}"
        chats[chat_id] = {
            "user1": user1,
            "user2": user2,
            "created_at": time.time()
        }

        users[user1].update({"state": "chatting", "partner_id": user2, "chat_id": chat_id})
        users[user2].update({"state": "chatting", "partner_id": user1, "chat_id": chat_id})

        bot.send_message(user1, "💬 *Собеседник найден!*\nНачинайте общение.", parse_mode='Markdown')
        bot.send_message(user2, "💬 *Собеседник найден!*\nНачинайте общение.", parse_mode='Markdown')

def leave_chat(message):
    user_id = message.from_user.id
    
    if user_id not in users or users[user_id]["state"] == "none":
        bot.send_message(user_id, "❌ Ты не в чате")
        return
    
    if users[user_id]["state"] == "waiting":
        if user_id in waiting_list:
            waiting_list.remove(user_id)
        users[user_id]["state"] = "none"
        bot.send_message(user_id, "🔎 Поиск остановлен")
        return

    partner_id = users[user_id]["partner_id"]
    users[user_id]["state"] = "none"
    users[user_id]["partner_id"] = None
    users[user_id]["chat_id"] = None
    
    bot.send_message(user_id, "✅ Ты вышел из чата")

    if partner_id in users and users[partner_id]["state"] == "chatting":
        bot.send_message(partner_id, "❌ Собеседник покинул чат")
        users[partner_id]["state"] = "none"
        users[partner_id]["partner_id"] = None
        users[partner_id]["chat_id"] = None

def forward_message(message):
    user_id = message.from_user.id
    chat_info = users[user_id]
    
    if chat_info["state"] != "chatting" or chat_info["partner_id"] not in users:
        bot.send_message(user_id, "❌ Собеседник покинул чат")
        users[user_id]["state"] = "none"
        return
    
    partner_id = chat_info["partner_id"]
    chat_id = chat_info["chat_id"]

    # Сохраняем в историю
    if message.content_type == 'text':
        chat_messages[chat_id].append({
            "sender": user_id,
            "type": "text",
            "content": message.text,
            "timestamp": time.time()
        })
    else:
        file_id = None
        if message.content_type == 'photo':
            file_id = message.photo[-1].file_id
        elif message.content_type == 'video':
            file_id = message.video.file_id
        elif message.content_type == 'document':
            file_id = message.document.file_id
        elif message.content_type == 'audio':
            file_id = message.audio.file_id
        elif message.content_type == 'voice':
            file_id = message.voice.file_id
        elif message.content_type == 'sticker':
            file_id = message.sticker.file_id
        else:
            return
        
        chat_messages[chat_id].append({
            "sender": user_id,
            "type": message.content_type,
            "content": file_id,
            "timestamp": time.time()
        })

    # Пересылаем собеседнику
    try:
        if message.content_type == 'text':
            bot.send_message(partner_id, message.text)
        elif message.content_type == 'photo':
            bot.send_photo(partner_id, message.photo[-1].file_id)
        elif message.content_type == 'video':
            bot.send_video(partner_id, message.video.file_id)
        elif message.content_type == 'document':
            bot.send_document(partner_id, message.document.file_id)
        elif message.content_type == 'audio':
            bot.send_audio(partner_id, message.audio.file_id)
        elif message.content_type == 'voice':
            bot.send_voice(partner_id, message.voice.file_id)
        elif message.content_type == 'sticker':
            bot.send_sticker(partner_id, message.sticker.file_id)
    except Exception as e:
        print(f"Ошибка: {e}")
        bot.send_message(user_id, "❌ Собеседник покинул чат")
        users[user_id]["state"] = "none"
        users[partner_id]["state"] = "none"

# ==============================================
# ОБРАБОТЧИКИ СООБЩЕНИЙ
# ==============================================

@bot.message_handler(commands=['start', 'help', 'find', 'leave'])
def handle_commands(message):
    command = message.text.split()[0].lower()
    
    if command == '/start':
        send_welcome(message)
    elif command == '/help':
        show_help(message)
    elif command == '/find':
        find_partner(message)
    elif command == '/leave':
        leave_chat(message)

@bot.message_handler(content_types=['text'])
def handle_text(message):
    user_id = message.from_user.id
    
    if user_id not in users:
        send_welcome(message)
        return
    
    if users[user_id]["state"] != "chatting":
        bot.send_message(user_id, "ℹ️ Используй /find для поиска собеседника")
        return
    
    forward_message(message)

@bot.message_handler(content_types=['photo', 'video', 'document', 'audio', 'voice', 'sticker'])
def handle_media(message):
    user_id = message.from_user.id
    
    if user_id not in users or users[user_id]["state"] != "chatting":
        return
    
    forward_message(message)

# ==============================================
# ЗАПУСК БОТА
# ==============================================

if __name__ == '__main__':
    print("🔥 ANONIM CHAT ЗАПУЩЕН! 🔥")
    print("👤 Создатель: Белый Дарон")
    print("📅", datetime.now())
    bot.infinity_polling()
