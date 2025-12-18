# bot.py
import os
import random
import asyncio
import aiosqlite
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from aiogram.exceptions import TelegramForbiddenError

# Безопасное чтение токена из переменной окружения
BOT_TOKEN = "8473568407:AAHDIUxnB2MZ39IylDYq8y4PFCK7KwLJzOw"
OWNER_ID = 5136595663

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Инициализация базы
async def init_db():
    async with aiosqlite.connect("names.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_names (
                user_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            )
        """)
        await db.commit()

async def get_name(user_id: int) -> str | None:
    async with aiosqlite.connect("names.db") as db:
        async with db.execute("SELECT name FROM user_names WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None

async def set_name(user_id: int, name: str):
    async with aiosqlite.connect("names.db") as db:
        await db.execute("INSERT OR REPLACE INTO user_names (user_id, name) VALUES (?, ?)", (user_id, name))
        await db.commit()

# === Команды ===

@dp.message(Command("myname"))
async def cmd_myname(message: Message):
    name = await get_name(message.from_user.id)
    if name:
        await message.reply(f"✨ Твоё имя: **{name}**", parse_mode="Markdown")
    else:
        await message.reply("У тебя ещё нет имени. Админ может выдать его через `/setname`.")

@dp.message(Command("getid"))
async def cmd_getid(message: Message):
    user = message.from_user
    await message.reply(f"Ваш ID: `{user.id}`", parse_mode="Markdown")

@dp.message(Command("setname"))
async def cmd_setname(message: Message, command: CommandObject):
    if message.from_user.id != OWNER_ID:
        await message.reply("🔒 Только владелец бота может назначать имена.")
        return

    if not command.args:
        await message.reply(
            "Использование:\n"
            "`/setname @username Имя`\n"
            "`/setname 123456789 Имя`",
            parse_mode="Markdown"
        )
        return

    args = command.args.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("❌ Укажи и цель (ID или @username), и имя.")
        return

    target_str, name = args[0], args[1]
    user_id = None

    # Попытка: числовой ID
    if target_str.isdigit():
        user_id = int(target_str)
    # Попытка: @username
    elif target_str.startswith("@"):
        username = target_str[1:]
        try:
            chat = await bot.get_chat(f"@{username}")
            if chat.type == "private":
                user_id = chat.id
        except Exception:
            user_id = None

    if not user_id:
        await message.reply(
            "❌ Не удалось найти пользователя.\n"
            "👉 Попроси его написать `/getid` и пришли его числовой ID."
        )
        return

    await set_name(user_id, name)
    try:
        await bot.send_message(user_id, f"🎭 Админ выдал тебе имя: **{name}**", parse_mode="Markdown")
    except TelegramForbiddenError:
        pass  # Пользователь не открыл ЛС

    await message.reply(f"✅ Имя **{name}** выдано (ID: `{user_id}`)", parse_mode="Markdown")

@dp.message(Command("listnames"))
async def cmd_listnames(message: Message):
    if message.from_user.id != OWNER_ID:
        return
    async with aiosqlite.connect("names.db") as db:
        async with db.execute("SELECT user_id, name FROM user_names WHERE name != ''") as cursor:
            rows = await cursor.fetchall()
    if not rows:
        await message.reply("Список имён пуст.")
        return
    text = "📋 Назначенные имена:\n"
    for user_id, name in rows:
        text += f"- `{user_id}` → {name}\n"
    await message.reply(text, parse_mode="Markdown")

# Автоматически сохраняем всех, кто пишет (даже без имени)
@dp.message()
async def auto_save_user(message: Message):
    user = message.from_user
    # Сохраняем, даже если имя пустое — для будущего /setname по ID
    async with aiosqlite.connect("names.db") as db:
        await db.execute("INSERT OR IGNORE INTO user_names (user_id, name) VALUES (?, '')", (user.id,))
        await db.commit()

# === Запуск ===
async def main():
    await init_db()
    print("✅ Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

