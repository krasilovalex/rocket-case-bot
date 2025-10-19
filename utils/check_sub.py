from aiogram import Bot
from aiogram.types import ChatMember
from utils.db_manager import get_required_channel

async def check_subscription(bot: Bot, user_id: int) -> bool:
    channel = get_required_channel()
    try:
        # Проверяем, это username или ID
        if channel.startswith("@"):
            chat_identifier = channel  # публичный канал
        else:
            # Пробуем преобразовать в число (ID приватного канала)
            chat_identifier = int(channel)
        
        member: ChatMember = await bot.get_chat_member(chat_identifier, user_id)
        return member.status != "left"

    except Exception as e:
        print(f"Ошибка проверки подписки: {e}")
        return False
