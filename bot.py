# bot.py
import os
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

# === База данных ===
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
        await message.reply("У тебя ещё нет имени. Админ может выдать его через `/setname`.", parse_mode="Markdown")

@dp.message(Command("getid"))
async def cmd_getid(message: Message):
    await message.reply(f"Ваш ID: `{message.from_user.id}`", parse_mode="Markdown")

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
        await message.reply("❌ Укажи и цель, и имя.")
        return

    target_str, name = args[0], args[1]
    user_id = None

    if target_str.isdigit():
        user_id = int(target_str)
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
        await bot.send_message(
            user_id,
            f"🎭 Админ выдал тебе имя: **{name}**",
            parse_mode="Markdown"
        )
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
    for uid, name in rows:
        text += f"- `{uid}` → {name}\n"
    await message.answer(text, parse_mode="Markdown")

# === Зеркалирование сообщений (только в группах) ===

@dp.message()
async def mirror_message(message: Message):
    # Игнорируем ЛС и сообщения от самого бота
    if message.chat.type == "private" or message.from_user.id == bot.id:
        return

    user = message.from_user

    # Получаем выданное имя
    game_name = await get_name(user.id)

    # Fallback: если имя не задано — используем обычное имя или username
    if not game_name:
        real = (user.first_name or "") + (" " + (user.last_name or ""))
        real = real.strip()
        if not real:
            real = f"@{user.username}" if user.username else "Аноним"
        game_name = real

    text = message.text or message.caption or ""

    # Удаляем оригинал (требуются права админа)
    try:
        await message.delete()
    except Exception:
        pass

    # Отправляем от имени бота
    if message.content_type == "text":
        await message.answer(f"**{game_name}**: {text}", parse_mode="Markdown")
    elif message.content_type == "photo":
        await message.answer_photo(
            photo=message.photo[-1].file_id,
            caption=f"**{game_name}**: {text}",
            parse_mode="Markdown"
        )
    elif message.content_type == "video":
        await message.answer_video(
            video=message.video.file_id,
            caption=f"**{game_name}**: {text}",
            parse_mode="Markdown"
        )
    elif message.content_type == "sticker":
        await message.answer(f"**{game_name}** отправил стикер")
    else:
        await message.answer(f"**{game_name}** отправил {message.content_type}")

# === Запуск ===
async def main():
    await init_db()
    print("✅ Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
