from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import sqlite3
import random
import datetime

TOKEN = "8666576626:AAHFlk3KhsRsmBnd_YjGZ_YsO7YblsA5vw4"

conn = sqlite3.connect('users.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users
             (user_id INTEGER PRIMARY KEY, 
              state TEXT, 
              partner INTEGER, 
              gender TEXT, 
              filter_gender TEXT,
              name TEXT, 
              age INTEGER, 
              bio TEXT, 
              rating INTEGER DEFAULT 0,
              chats INTEGER DEFAULT 0)''')
conn.commit()

MENU = """
🌟 *ДОБРО ПОЖАЛОВАТЬ В ANONCHAT* 🌟

┌─────────────────────┐
│  Анонимное общение   │
│  Без регистрации     │
│  Без слежки          │
│  Только ты и друг    │
└─────────────────────┘

💫 *Что умеет бот?*
▫️ Поиск по интересам
▫️ Фильтр по полу (опционально)
▫️ Анонимный чат
▫️ Рейтинг собеседников
▫️ Блокировка токсиков

👇 *Выбери действие:*
"""

async def start(update: Update, context):
    uid = update.effective_user.id
    c.execute('INSERT OR IGNORE INTO users (user_id, state, filter_gender) VALUES (?, ?, ?)', 
              (uid, 'idle', 'all'))
    conn.commit()
    
    keyboard = [
        [InlineKeyboardButton("🔍 Найти собеседника", callback_data='find')],
        [InlineKeyboardButton("📝 Моя анкета", callback_data='profile')],
        [InlineKeyboardButton("🎯 Фильтр по полу", callback_data='filter_menu')],
        [InlineKeyboardButton("⭐ Рейтинг", callback_data='rating')],
        [InlineKeyboardButton("❓ Помощь", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        MENU,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    
    if query.data == 'find':
        await find_partner(query, context)
    elif query.data == 'profile':
        await show_profile(query)
    elif query.data == 'filter_menu':
        await show_filter_menu(query)
    elif query.data.startswith('filter_'):
        filter_type = query.data.split('_')[1]
        c.execute('UPDATE users SET filter_gender = ? WHERE user_id = ?', (filter_type, uid))
        conn.commit()
        
        filter_names = {
            'all': '🔓 Все (без фильтра)',
            'м': '👨 Только мужчины',
            'ж': '👩 Только женщины'
        }
        await query.edit_message_text(
            f"✅ *Фильтр обновлён!*\n\n"
            f"Текущий фильтр: {filter_names.get(filter_type, filter_type)}\n\n"
            f"Теперь поиск будет учитывать твой выбор.\n"
            f"Можешь изменить в любой момент через меню.",
            parse_mode='Markdown'
        )
    elif query.data == 'rating':
        await show_rating(query)
    elif query.data == 'help':
        await show_help(query)
    elif query.data.startswith('gender_'):
        gender = query.data.split('_')[1]
        c.execute('UPDATE users SET gender = ? WHERE user_id = ?', (gender, uid))
        conn.commit()
        
        keyboard = [[InlineKeyboardButton("🔙 Назад в меню", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"✅ Пол сохранён: {gender}\n\nТеперь заполни остальную анкету или ищи собеседника!",
            reply_markup=reply_markup
        )
    elif query.data == 'back_to_menu':
        await show_main_menu(query)
    elif query.data.startswith('block_'):
        blocker = uid
        blocked = int(query.data.split('_')[1])
        c.execute('UPDATE users SET state = "idle", partner = NULL WHERE user_id = ?', (blocker,))
        c.execute('UPDATE users SET state = "idle", partner = NULL WHERE user_id = ?', (blocked,))
        conn.commit()
        await query.edit_message_text("🚫 Пользователь заблокирован. Чат закрыт.")
        await context.bot.send_message(blocked, "🚫 Собеседник заблокировал вас. Чат закрыт.")

async def show_main_menu(query):
    keyboard = [
        [InlineKeyboardButton("🔍 Найти собеседника", callback_data='find')],
        [InlineKeyboardButton("📝 Моя анкета", callback_data='profile')],
        [InlineKeyboardButton("🎯 Фильтр по полу", callback_data='filter_menu')],
        [InlineKeyboardButton("⭐ Рейтинг", callback_data='rating')],
        [InlineKeyboardButton("❓ Помощь", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(MENU, parse_mode='Markdown', reply_markup=reply_markup)

async def show_filter_menu(query):
    uid = query.from_user.id
    c.execute('SELECT filter_gender FROM users WHERE user_id = ?', (uid,))
    current = c.fetchone()[0]
    
    filter_names = {
        'all': '🔓 Все',
        'м': '👨 Мужчины',
        'ж': '👩 Женщины'
    }
    
    keyboard = [
        [InlineKeyboardButton(f"{'✅ ' if current == 'all' else ''}🔓 Все (без фильтра)", callback_data='filter_all')],
        [InlineKeyboardButton(f"{'✅ ' if current == 'м' else ''}👨 Только мужчины", callback_data='filter_м')],
        [InlineKeyboardButton(f"{'✅ ' if current == 'ж' else ''}👩 Только женщины", callback_data='filter_ж')],
        [InlineKeyboardButton("🔙 Назад в меню", callback_data='back_to_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"🎯 *НАСТРОЙКА ФИЛЬТРА ПО ПОЛУ*\n\n"
        f"Текущий фильтр: {filter_names.get(current, 'Все')}\n\n"
        f"Выбери кого хочешь искать:\n"
        f"• *Все* — ищем всех пользователей\n"
        f"• *Мужчины* — только парней\n"
        f"• *Женщины* — только девушек\n\n"
        f"ℹ️ Фильтр работает *только* при поиске.\n"
        f"Анкета хранит твой пол отдельно.",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def find_partner(query, context):
    uid = query.from_user.id
    c.execute('SELECT state, partner, filter_gender FROM users WHERE user_id = ?', (uid,))
    row = c.fetchone()
    
    if row and row[0] == 'chat':
        await query.edit_message_text("⚠️ Ты уже в чате! Используй /stop чтобы выйти.")
        return
    
    filter_gender = row[2] if row else 'all'
    
    c.execute('SELECT gender, name, age, bio FROM users WHERE user_id = ?', (uid,))
    data = c.fetchone()
    if not data or not data[0] or not data[1]:
        keyboard = [
            [InlineKeyboardButton("👨 Мужской", callback_data='gender_м')],
            [InlineKeyboardButton("👩 Женский", callback_data='gender_ж')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "📝 *Сначала заполни анкету:*\n\nВыбери свой пол:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        return
    
    if filter_gender == 'all':
        c.execute('''SELECT user_id FROM users 
                     WHERE state = "search" 
                     AND user_id != ? 
                     AND gender IS NOT NULL 
                     AND name IS NOT NULL''', (uid,))
    else:
        c.execute('''SELECT user_id FROM users 
                     WHERE state = "search" 
                     AND user_id != ? 
                     AND gender = ? 
                     AND gender IS NOT NULL 
                     AND name IS NOT NULL''', (uid, filter_gender))
    
    seekers = c.fetchall()
    
    if seekers:
        partner = random.choice(seekers)[0]
        c.execute('UPDATE users SET state = "chat", partner = ? WHERE user_id = ?', (partner, uid))
        c.execute('UPDATE users SET state = "chat", partner = ? WHERE user_id = ?', (uid, partner))
        conn.commit()
        
        c.execute('SELECT name, gender, age, bio FROM users WHERE user_id = ?', (partner,))
        pdata = c.fetchone()
        
        filter_text = f"Фильтр: {filter_gender if filter_gender != 'all' else 'Все'}"
        
        await context.bot.send_message(
            partner,
            f"🔗 *СОБЕСЕДНИК НАЙДЕН!*\n\n"
            f"👤 {pdata[0]} | {pdata[1]} | {pdata[2] if pdata[2] else '?'} лет\n"
            f"📝 {pdata[3] if pdata[3] else 'Без описания'}\n\n"
            f"💬 Пиши анонимно! Используй /stop для выхода."
        )
        await query.edit_message_text(
            f"🔗 *СОБЕСЕДНИК НАЙДЕН!*\n\n"
            f"👤 {pdata[0]} | {pdata[1]} | {pdata[2] if pdata[2] else '?'} лет\n"
            f"📝 {pdata[3] if pdata[3] else 'Без описания'}\n\n"
            f"🎯 {filter_text}\n"
            f"💬 Пиши анонимно! /stop для выхода.",
            parse_mode='Markdown'
        )
    else:
        c.execute('UPDATE users SET state = "search", partner = NULL WHERE user_id = ?', (uid,))
        conn.commit()
        
        filter_text = f"с фильтром '{filter_gender}'" if filter_gender != 'all' else "без фильтра"
        
        await query.edit_message_text(
            f"⏳ *ИЩЕМ СОБЕСЕДНИКА...*\n\n"
            f"Ищем {filter_text}\n"
            f"Как только кто-то появится - сразу сообщим!\n\n"
            f"📌 Напиши /stop чтобы отменить поиск.",
            parse_mode='Markdown'
        )

async def show_profile(query):
    uid = query.from_user.id
    c.execute('SELECT name, gender, age, bio, rating, chats, filter_gender FROM users WHERE user_id = ?', (uid,))
    data = c.fetchone()
    
    if not data or not data[0]:
        keyboard = [[InlineKeyboardButton("🔙 Назад в меню", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "📝 *Заполни анкету:*\n\n"
            "Отправь мне сообщение в формате:\n"
            "`Имя|Возраст|О себе`\n\n"
            "Пример: `Алексей|25|Люблю котиков и игры`",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        return
    
    name, gender, age, bio, rating, chats, filter_gender = data
    
    filter_names = {
        'all': '🔓 Все',
        'м': '👨 Мужчины',
        'ж': '👩 Женщины'
    }
    
    keyboard = [[InlineKeyboardButton("🔙 Назад в меню", callback_data='back_to_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"📋 *ТВОЯ АНКЕТА*\n\n"
        f"👤 Имя: {name}\n"
        f"⚥ Пол: {gender}\n"
        f"🎂 Возраст: {age if age else 'Не указан'}\n"
        f"📝 О себе: {bio if bio else 'Не заполнено'}\n\n"
        f"🎯 Фильтр поиска: {filter_names.get(filter_gender, 'Все')}\n\n"
        f"⭐ Рейтинг: {'🌟' * (rating if rating <= 5 else 5)} ({rating})\n"
        f"💬 Чатов: {chats}\n\n"
        f"✏️ Чтобы изменить анкету - отправь:\n"
        f"`Имя|Возраст|О себе`\n"
        f"🎯 Чтобы изменить фильтр - в меню",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def show_rating(query):
    c.execute('SELECT name, rating FROM users WHERE rating > 0 ORDER BY rating DESC LIMIT 10')
    top = c.fetchall()
    
    keyboard = [[InlineKeyboardButton("🔙 Назад в меню", callback_data='back_to_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if not top:
        await query.edit_message_text(
            "🌟 Пока нет рейтингов. Будь первым!",
            reply_markup=reply_markup
        )
        return
    
    text = "🏆 *ТОП ПОЛЬЗОВАТЕЛЕЙ*\n\n"
    for i, (name, rating) in enumerate(top, 1):
        stars = '🌟' * (rating if rating <= 5 else 5)
        text += f"{i}. {name} {stars} ({rating})\n"
    
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)

async def show_help(query):
    keyboard = [[InlineKeyboardButton("🔙 Назад в меню", callback_data='back_to_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "📖 *ПОМОЩЬ*\n\n"
        "🔍 /start - Главное меню\n"
        "🔍 /join - Найти собеседника\n"
        "📝 Отправь: `Имя|Возраст|О себе` - Заполнить анкету\n"
        "🎯 Фильтр по полу - в меню\n"
        "⏹ /stop - Выйти из чата\n"
        "🚫 /block - Заблокировать собеседника\n\n"
        "💡 *Советы:*\n"
        "• Заполни анкету для лучшего поиска\n"
        "• Включи фильтр если хочешь искать только мужчин или женщин\n"
        "• Будь вежлив - твой рейтинг растёт\n"
        "• Используй /stop перед выходом",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def handle_profile(update: Update, context):
    uid = update.effective_user.id
    text = update.message.text
    
    if '|' not in text:
        await update.message.reply_text(
            "❌ Неправильный формат!\n"
            "Используй: `Имя|Возраст|О себе`\n"
            "Пример: `Алексей|25|Люблю котиков`",
            parse_mode='Markdown'
        )
        return
    
    parts = text.split('|')
    name = parts[0].strip()
    age = parts[1].strip() if len(parts) > 1 else ''
    bio = parts[2].strip() if len(parts) > 2 else ''
    
    c.execute('UPDATE users SET name = ?, age = ?, bio = ? WHERE user_id = ?', 
              (name, age, bio, uid))
    conn.commit()
    
    keyboard = [[InlineKeyboardButton("🔍 Найти собеседника", callback_data='find')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"✅ *Анкета сохранена!*\n\n"
        f"👤 Имя: {name}\n"
        f"🎂 Возраст: {age}\n"
        f"📝 О себе: {bio}\n\n"
        f"Теперь используй меню для поиска!",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def stop(update: Update, context):
    uid = update.effective_user.id
    c.execute('SELECT partner FROM users WHERE user_id = ?', (uid,))
    row = c.fetchone()
    
    if row and row[0]:
        partner = row[0]
        c.execute('UPDATE users SET state = "idle", partner = NULL WHERE user_id = ?', (uid,))
        c.execute('UPDATE users SET state = "idle", partner = NULL WHERE user_id = ?', (partner,))
        conn.commit()
        await context.bot.send_message(partner, "👋 Собеседник покинул чат. Было приятно!")
        await update.message.reply_text("👋 Ты покинул чат. Возвращайся!")
    else:
        c.execute('UPDATE users SET state = "idle", partner = NULL WHERE user_id = ?', (uid,))
        conn.commit()
        await update.message.reply_text("✅ Готово! Используй /start для нового поиска.")

async def block(update: Update, context):
    uid = update.effective_user.id
    c.execute('SELECT partner FROM users WHERE user_id = ?', (uid,))
    row = c.fetchone()
    
    if row and row[0]:
        partner = row[0]
        c.execute('UPDATE users SET state = "idle", partner = NULL WHERE user_id = ?', (uid,))
        c.execute('UPDATE users SET state = "idle", partner = NULL WHERE user_id = ?', (partner,))
        conn.commit()
        await context.bot.send_message(partner, "🚫 Собеседник заблокировал вас.")
        await update.message.reply_text("🚫 Пользователь заблокирован. Чат закрыт.")
    else:
        await update.message.reply_text("❌ Ты не в чате.")

async def relay(update: Update, context):
    uid = update.effective_user.id
    text = update.message.text
    
    if not text or text.startswith('/'):
        return
    
    if '|' in text:
        await handle_profile(update, context)
        return
    
    c.execute('SELECT state, partner FROM users WHERE user_id = ?', (uid,))
    row = c.fetchone()
    
    if row and row[0] == 'chat' and row[1]:
        await context.bot.send_message(row[1], text)
        c.execute('UPDATE users SET chats = chats + 1 WHERE user_id = ?', (uid,))
        conn.commit()

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('join', lambda u,c: start(u,c)))
    app.add_handler(CommandHandler('stop', stop))
    app.add_handler(CommandHandler('block', block))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, relay))
    
    print('🌟 ANONCHAT БОТ ЗАПУЩЕН! 🌟')
    print(f'📅 {datetime.datetime.now()}')
    app.run_polling()

if __name__ == '__main__':
    main()
