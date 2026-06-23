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
              age INTEGER,
              filter_age_min INTEGER DEFAULT 0,
              filter_age_max INTEGER DEFAULT 100)''')
conn.commit()

RULES = """
🔞 *ПРАВИЛА ANONCHAT* 🔞

Здесь НЕТ:
❌ Запретов
❌ Цензуры
❌ Блокировок
❌ Модерации

✅ РАЗРЕШЕНО ВСЁ:
• Любые темы
• Любые выражения
• Любой контент
• Абсолютная анонимность

⚠️ Единственное правило:
Ты общаешься на свой страх и риск.
Никто не несёт ответственности.

🔥 ДОБРО ПОЖАЛОВАТЬ В СВОБОДНОЕ ОБЩЕНИЕ!
"""

async def start(update: Update, context):
    uid = update.effective_user.id
    c.execute('INSERT OR IGNORE INTO users (user_id, state) VALUES (?, ?)', (uid, 'idle'))
    conn.commit()
    
    keyboard = [
        [InlineKeyboardButton("🔍 ПОИСК ( /search )", callback_data='search')],
        [InlineKeyboardButton("📋 ПРАВИЛА", callback_data='rules')],
        [InlineKeyboardButton("⚙️ ФИЛЬТР ВОЗРАСТА", callback_data='filter')],
        [InlineKeyboardButton("⏹ ВЫЙТИ ( /stop )", callback_data='stop')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🔥 *ANONCHAT*\n\n"
        "Анонимное общение без границ.\n"
        "Нажми /search чтобы найти собеседника.\n\n"
        "Никаких анкет. Только возраст.\n"
        "Никаких запретов. Всё разрешено.",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    
    if query.data == 'search':
        await find_partner(query, context)
    elif query.data == 'rules':
        await show_rules(query)
    elif query.data == 'filter':
        await show_filter_menu(query)
    elif query.data.startswith('filter_'):
        parts = query.data.split('_')
        if parts[1] == 'min':
            c.execute('UPDATE users SET filter_age_min = ? WHERE user_id = ?', (int(parts[2]), uid))
            conn.commit()
            await query.edit_message_text(f"✅ Минимальный возраст: {parts[2]}")
        elif parts[1] == 'max':
            c.execute('UPDATE users SET filter_age_max = ? WHERE user_id = ?', (int(parts[2]), uid))
            conn.commit()
            await query.edit_message_text(f"✅ Максимальный возраст: {parts[2]}")
        await show_filter_menu(query)
    elif query.data == 'stop':
        await stop_command(update, context)
    elif query.data.startswith('block_'):
        blocker = uid
        blocked = int(query.data.split('_')[1])
        c.execute('UPDATE users SET state = "idle", partner = NULL WHERE user_id = ?', (blocker,))
        c.execute('UPDATE users SET state = "idle", partner = NULL WHERE user_id = ?', (blocked,))
        conn.commit()
        await query.edit_message_text("⛔ Собеседник заблокирован.")
        await context.bot.send_message(blocked, "⛔ Собеседник завершил общение.")

async def show_rules(query):
    await query.edit_message_text(RULES, parse_mode='Markdown')

async def show_filter_menu(query):
    uid = query.from_user.id
    c.execute('SELECT filter_age_min, filter_age_max FROM users WHERE user_id = ?', (uid,))
    min_age, max_age = c.fetchone()
    
    keyboard = [
        [InlineKeyboardButton(f"🔽 Мин возраст: {min_age}", callback_data='noop')],
        [InlineKeyboardButton("16", callback_data='filter_min_16'), InlineKeyboardButton("18", callback_data='filter_min_18'), InlineKeyboardButton("21", callback_data='filter_min_21')],
        [InlineKeyboardButton(f"🔼 Макс возраст: {max_age}", callback_data='noop')],
        [InlineKeyboardButton("25", callback_data='filter_max_25'), InlineKeyboardButton("35", callback_data='filter_max_35'), InlineKeyboardButton("50", callback_data='filter_max_50')],
        [InlineKeyboardButton("🔙 Назад", callback_data='back_to_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "⚙️ *ФИЛЬТР ВОЗРАСТА*\n\n"
        f"Текущий фильтр: {min_age}–{max_age} лет\n\n"
        "Выбери диапазон возрастов для поиска:",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def find_partner(query, context):
    uid = query.from_user.id
    c.execute('SELECT state, partner FROM users WHERE user_id = ?', (uid,))
    row = c.fetchone()
    
    if row and row[0] == 'chat':
        await query.edit_message_text("⚠️ Ты уже в чате. /stop чтобы выйти.")
        return
    
    # Проверка возраста
    c.execute('SELECT age FROM users WHERE user_id = ?', (uid,))
    age_data = c.fetchone()
    if not age_data or not age_data[0]:
        await query.edit_message_text(
            "📝 *Укажи свой возраст*\n\n"
            "Просто отправь число (например 25):",
            parse_mode='Markdown'
        )
        return
    
    # Фильтр
    c.execute('SELECT filter_age_min, filter_age_max FROM users WHERE user_id = ?', (uid,))
    min_age, max_age = c.fetchone()
    
    # Поиск с фильтром
    c.execute('''SELECT user_id FROM users 
                 WHERE state = "search" 
                 AND user_id != ? 
                 AND age IS NOT NULL
                 AND age >= ? AND age <= ?''', (uid, min_age, max_age))
    seekers = c.fetchall()
    
    if seekers:
        partner = random.choice(seekers)[0]
        c.execute('UPDATE users SET state = "chat", partner = ? WHERE user_id = ?', (partner, uid))
        c.execute('UPDATE users SET state = "chat", partner = ? WHERE user_id = ?', (uid, partner))
        conn.commit()
        
        c.execute('SELECT age FROM users WHERE user_id = ?', (partner,))
        pdata = c.fetchone()
        
        await context.bot.send_message(
            partner,
            "🔗 *СОБЕСЕДНИК НАЙДЕН!*\n\n"
            f"🎂 Возраст: {pdata[0] if pdata[0] else '?'} лет\n\n"
            "💬 Пиши анонимно! Всё разрешено.\n"
            "/stop — выйти\n"
            "/block — заблокировать"
        )
        await query.edit_message_text(
            "🔗 *СОБЕСЕДНИК НАЙДЕН!*\n\n"
            f"🎂 Возраст: {pdata[0] if pdata[0] else '?'} лет\n\n"
            "💬 Пиши анонимно! Всё разрешено.\n"
            "/stop — выйти\n"
            "/block — заблокировать",
            parse_mode='Markdown'
        )
    else:
        c.execute('UPDATE users SET state = "search", partner = NULL WHERE user_id = ?', (uid,))
        conn.commit()
        await query.edit_message_text(
            "⏳ *ИЩЕМ СОБЕСЕДНИКА...*\n\n"
            "Как только кто-то появится — соединим.\n"
            "/stop чтобы отменить поиск.",
            parse_mode='Markdown'
        )

async def set_age(update: Update, context):
    uid = update.effective_user.id
    try:
        age = int(update.message.text.strip())
        if 13 <= age <= 100:
            c.execute('UPDATE users SET age = ? WHERE user_id = ?', (age, uid))
            conn.commit()
            await update.message.reply_text(f"✅ Возраст сохранён: {age}\nТеперь используй /search для поиска!")
        else:
            await update.message.reply_text("❌ Введи возраст от 13 до 100.")
    except ValueError:
        await update.message.reply_text("❌ Отправь число, например: 25")

async def search_command(update: Update, context):
    uid = update.effective_user.id
    c.execute('INSERT OR IGNORE INTO users (user_id, state) VALUES (?, ?)', (uid, 'idle'))
    conn.commit()
    
    c.execute('SELECT state, partner FROM users WHERE user_id = ?', (uid,))
    row = c.fetchone()
    
    if row and row[0] == 'chat':
        await update.message.reply_text("⚠️ Ты уже в чате. /stop чтобы выйти.")
        return
    
    # Имитация нажатия кнопки "Поиск"
    query = type('obj', (object,), {'from_user': update.effective_user, 'edit_message_text': lambda self, text, **kwargs: None, 'message': update.message})()
    await find_partner(query, context)

async def stop_command(update: Update, context):
    uid = update.effective_user.id
    c.execute('SELECT partner FROM users WHERE user_id = ?', (uid,))
    row = c.fetchone()
    
    if row and row[0]:
        partner = row[0]
        c.execute('UPDATE users SET state = "idle", partner = NULL WHERE user_id = ?', (uid,))
        c.execute('UPDATE users SET state = "idle", partner = NULL WHERE user_id = ?', (partner,))
        conn.commit()
        await context.bot.send_message(partner, "👋 Собеседник покинул чат.")
        await update.message.reply_text("👋 Ты вышел из чата.")
    else:
        c.execute('UPDATE users SET state = "idle", partner = NULL WHERE user_id = ?', (uid,))
        conn.commit()
        await update.message.reply_text("✅ Готово. /search чтобы найти кого-то.")

async def block_command(update: Update, context):
    uid = update.effective_user.id
    c.execute('SELECT partner FROM users WHERE user_id = ?', (uid,))
    row = c.fetchone()
    
    if row and row[0]:
        partner = row[0]
        c.execute('UPDATE users SET state = "idle", partner = NULL WHERE user_id = ?', (uid,))
        c.execute('UPDATE users SET state = "idle", partner = NULL WHERE user_id = ?', (partner,))
        conn.commit()
        await context.bot.send_message(partner, "⛔ Собеседник завершил общение.")
        await update.message.reply_text("⛔ Собеседник заблокирован.")
    else:
        await update.message.reply_text("❌ Ты не в чате.")

async def relay(update: Update, context):
    uid = update.effective_user.id
    text = update.message.text
    
    if not text or text.startswith('/'):
        return
    
    # Если число — сохраняем возраст
    if text.isdigit() and 13 <= int(text) <= 100:
        await set_age(update, context)
        return
    
    c.execute('SELECT state, partner FROM users WHERE user_id = ?', (uid,))
    row = c.fetchone()
    
    if row and row[0] == 'chat' and row[1]:
        await context.bot.send_message(row[1], f"💬 {text}")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('search', search_command))
    app.add_handler(CommandHandler('stop', stop_command))
    app.add_handler(CommandHandler('block', block_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, relay))
    
    print('🔥 ANONCHAT БОТ ЗАПУЩЕН! ВСЁ РАЗРЕШЕНО! 🔥')
    print(f'📅 {datetime.datetime.now()}')
    app.run_polling()

if __name__ == '__main__':
    main()
