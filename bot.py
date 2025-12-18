# bot.py
import asyncio
import aiosqlite
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from aiogram.exceptions import TelegramForbiddenError

# --- ЗАМЕНИ НА СВОЙ ТОКЕН ---
BOT_TOKEN = "8473568407:AAHDIUxnB2MZ39IylDYq8y4PFCK7KwLJzOw"
OWNER_ID = 5136595663

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

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

async def resolve_username(username: str) -> int | None:
    """Пытаемся получить user_id по username (работает ТОЛЬКО если пользователь писал в чат)"""
    # К сожалению, aiogram не может по username найти user_id напрямую.
    # Мы можем попробовать через get_chat, но это не всегда работает.
    try:
        chat = await bot.get_chat(username)
        if chat.type == "private":
            return chat.id
    except Exception:
        pass
    return None

@dp.message(Command("myname"))
async def cmd_myname(message: Message):
    name = await get_name(message.from_user.id)
    if name:
        await message.reply(f"✨ Твоё имя: **{name}**", parse_mode="Markdown")
    else:
        await message.reply("У тебя ещё нет имени. Админ может выдать его командой `/setname`.")

@dp.message(Command("setname"))
async def cmd_setname(message: Message, command: CommandObject):
    if message.from_user.id != OWNER_ID:
        await message.reply("🔒 Только владелец бота может назначать имена.")
        return

    if not command.args:
        await message.reply("Использование: `/setname @username Имя` или `/setname Имя` (для себя)", parse_mode="Markdown")
        return

    args = command.args.split(maxsplit=1)
    if len(args) < 2:
        # Назначить имя себе
        await set_name(message.from_user.id, args[0])
        await message.reply(f"✅ Тебе выдано имя: **{args[0]}**", parse_mode="Markdown")
        return

    target, name = args[0], args[1]

    # Определяем, кому назначаем
    if target.startswith("@"):
        username = target[1:]
        # Пытаемся получить user_id
        user_id = None
        try:
            chat = await bot.get_chat(f"@{username}")
            if chat.type == "private":
                user_id = chat.id
        except Exception as e:
            await message.reply(f"❌ Не удалось найти пользователя @{username}. Убедись, что он писал в этот чат или открыта переписка с ботом.")
            return
    else:
        await message.reply("❌ Укажи пользователя через @username.")
        return

    if user_id:
        await set_name(user_id, name)
        try:
            await bot.send_message(user_id, f"🎭 Админ выдал тебе имя: **{name}**", parse_mode="Markdown")
        except TelegramForbiddenError:
            pass  # Пользователь не открыл ЛС
        await message.reply(f"✅ Имя **{name}** выдано @{username} (id={user_id})", parse_mode="Markdown")
    else:
        await message.reply(f"❌ Пользователь @{username} не найден. Возможно, он не писал в чат.")

@dp.message(Command("listnames"))
async def cmd_listnames(message: Message):
    if message.from_user.id != OWNER_ID:
        return
    async with aiosqlite.connect("names.db") as db:
        async with db.execute("SELECT user_id, name FROM user_names") as cursor:
            rows = await cursor.fetchall()
    if not rows:
        await message.reply("Список имён пуст.")
        return
    text = "📋 Назначенные имена:\n"
    for user_id, name in rows:
        text += f"- `{user_id}` → {name}\n"
    await message.reply(text, parse_mode="Markdown")

async def main():
    await init_db()
    print("✅ Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())