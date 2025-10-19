from aiogram.methods.get_available_gifts import GetAvailableGifts

async def print_available_gifts(bot):
    """Вывод всех доступных подарков бота в консоль с ценой в XTR"""
    try:
        gifts_obj = await bot(GetAvailableGifts())
        if not gifts_obj.gifts:
            print("⚠️ Нет доступных подарков")
            return
        
        print("✅ Доступные подарки:")
        for gift in gifts_obj.gifts:
            gift_id = getattr(gift, "id", "—")
            # эмодзи берем из стикера, если есть
            emoji = getattr(getattr(gift, "sticker", None), "emoji", "—")
            # количество звезд для отправки
            star_count = getattr(gift, "star_count", "—")
            print(f"ID: {gift_id} | Emoji: {emoji} | Звезды: {star_count} XTR")
    except Exception as e:
        print(f"Ошибка получения доступных подарков: {e}")
