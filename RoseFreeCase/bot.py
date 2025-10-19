import asyncio
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from handlers import user_start, admin_panel, payment_stars, aio

# Импорт функции для вывода доступных подарков
from handlers.aio import print_available_gifts  

async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # Вывод всех доступных подарков при старте
    await print_available_gifts(bot)

    # Подключаем роутеры
    dp.include_router(user_start.router)
    dp.include_router(admin_panel.router)
    dp.include_router(payment_stars.router)

    # Восстанавливаем уведомления
    await user_start.restore_notifications(bot)

    print("✅ Bot is running...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
