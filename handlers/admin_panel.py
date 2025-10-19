from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from config import ADMIN_ID, ADMIN_2ID
from utils.db_manager import load_db, save_db

router = Router()
ADMINS = [int(ADMIN_ID), int(ADMIN_2ID)]




@router.message(Command("admin"))
async def admin_panel(message: Message):
    """Главное меню администратора со статистикой и текущими настройками"""
    if message.from_user.id not in ADMINS:
        return

    db = load_db()
    users = db.get("users", {})
    settings = db.get("settings", {})

    channel = settings.get("required_channel", "❌ Не задан")
    invite_link = settings.get("invite_link")

    # Общая статистика
    total_users = len(users)
    total_roses = sum(user.get("roses", 0) for user in users.values())
    total_cases = sum(user.get("cases_opened", 0) for user in users.values())
    total_dark_spell_cases  = sum(user.get("darkcases_opened", 0) for user in users.values())
    total_dark_spell_stars  = sum(user.get("darkstars_spent", 0) for user in users.values())
    

    # Формируем текст
    text = (
        "🚀 <b>Панель администратора</b>\n\n"
        "📢 <b>Канал обязательной подписки:</b>\n"
        f"├ Канал: <code>{channel}</code>\n"
    )

    if invite_link:
        text += f"└ Ссылка: <a href=\"{invite_link}\">{invite_link}</a>\n"
    else:
        if channel.startswith("-100"):
            text += "└ ⚠️ Для канала с ID нет инвайт-ссылки!\n"
        else:
            text += "└ 🔓 Публичный канал (с username)\n"

    text += (
        "\n📊 <b>Статистика пользователей:</b>\n"
        f"├ 👥 Всего пользователей: <b>{total_users}</b>\n"
        f"├ 🎁 Бесплатных кейсов открыто: <b>{total_cases}</b>\n"
        f"├ 🎁 Dark Spell Case открыто: <b>{total_dark_spell_cases}</b>\n"
        f"├ ⭐ Звёзд потрачено на Dark Spell Case: <b>{total_dark_spell_stars}</b>\n"
        f"└ 🚀 Всего ракеток выдано: <b>{total_roses}</b>\n\n"
        "🛠 Чтобы изменить канал подписки:\n"
        "<code>/setchannel @channel</code> — для публичного\n"
        "<code>/setchannel -1001234567890 https://t.me/+invite</code> — для приватного"
    )

    await message.answer(text, parse_mode="HTML")



@router.message(Command("setchannel"))
async def set_channel(message: Message):
    """Изменение обязательного канала для подписки (с @username или ID + инвайт-ссылкой)"""
    if message.from_user.id not in ADMINS:
        return

    parts = message.text.split()
    if len(parts) < 2:
        await message.answer(
            "❌ Укажи канал:\n"
            "<code>/setchannel @channel</code>\n"
            "или\n"
            "<code>/setchannel -1001234567890 https://t.me/+invite</code>",
            parse_mode="HTML"
        )
        return

    new_channel = parts[1]
    invite_link = None

    # Если канал задан по ID, инвайт-ссылка обязательна
    if new_channel.startswith("-100"):
        if len(parts) < 3:
            await message.answer(
                "❌ Для каналов с ID нужно указать инвайт-ссылку!\n"
                "Пример:\n<code>/setchannel -1001234567890 https://t.me/+AbCdEfGhIj</code>",
                parse_mode="HTML"
            )
            return
        invite_link = parts[2]

    # Загружаем и обновляем настройки
    data = load_db()
    if "settings" not in data:
        data["settings"] = {}

    data["settings"]["required_channel"] = new_channel
    if invite_link:
        data["settings"]["invite_link"] = invite_link
    elif "invite_link" in data["settings"]:
        del data["settings"]["invite_link"]  # удаляем старую ссылку, если больше не нужна

    save_db(data)

    # Ответ администратору
    text = f"✅ Канал обязательной подписки изменён на <b>{new_channel}</b>"
    if invite_link:
        text += f"\n🔗 Инвайт-ссылка: <a href=\"{invite_link}\">{invite_link}</a>"

    await message.answer(text, parse_mode="HTML")
