import asyncio
import random
from datetime import date
from aiogram import Router, F
from aiogram.types import Message
from config import ADMIN_ID
from utils.db_manager import get_user, update_user

router = Router()


def can_open_today(user):
    """Проверяем, открывал ли пользователь кейс сегодня"""
    return user.get("last_open") != str(date.today())


@router.message(F.text.lower() == "🎁 открыть секретный бокс🌹")
async def open_secret_box(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username

    user = get_user(user_id) or {}

    # Проверяем лимит 1 кейс в день
    if not can_open_today(user):
        await message.answer("😅 Ты уже открывал бокс сегодня! Попробуй завтра 🌞")
        return

    # Анимация открытия
    await message.answer("🎁 *Открываем секретный бокс...*", parse_mode="Markdown")
    await asyncio.sleep(2)
    await message.answer("✨ *Вы видите блеск внутри...*", parse_mode="Markdown")
    await asyncio.sleep(2)

    # Шанс 2% на выпадение розы
    drop_chance = random.random()
    if drop_chance <= 0.02:
        await message.answer("🌹 *Поздравляем! Вам выпала роза!*", parse_mode="Markdown")

        # Обновляем данные пользователя
        new_roses = user.get("roses", 0) + 1
        update_user(user_id, username, roses=new_roses, last_open=str(date.today()))

        # Уведомляем админа
        try:
            await bot.send_message(
                ADMIN_ID,
                f"🌹 *Новая роза!*\n\n"
                f"Пользователь: @{username or 'без username'}\n"
                f"ID: `{user_id}`\n"
                f"Всего роз: {new_roses}",
                parse_mode="Markdown"
            )
        except Exception as e:
            print(f"Ошибка при уведомлении админа: {e}")

    else:
        # Обновляем только дату открытия
        update_user(user_id, username, last_open=str(date.today()))
        await message.answer("😔 К сожалению, роза не выпала. Попробуйте завтра!")
