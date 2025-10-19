import asyncio
import random
from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from utils.check_sub import check_subscription
from utils.db_manager import get_user, update_user, load_db, get_required_channel
from config import ADMIN_ID
from aiogram.types import CallbackQuery,  LabeledPrice, PreCheckoutQuery, SuccessfulPayment
from config import ADMIN_ID, ADMIN_2ID

ADMINS = [int(ADMIN_ID), int(ADMIN_2ID)]
router = Router()

# Активные уведомления, чтобы не дублировать
scheduled_notifications = {}

# 🔧 Тестовый режим уведомлений (True — тест, False — рабочий)
TEST_MODE = False
TEST_WAIT_SECONDS = 15  # В тестовом режиме уведомления через 15 сек

# =============================== #
#   Функции для работы с кейсом    #
# =============================== #

def can_open_today(user):
    last_open = user.get("last_open")
    if not last_open:
        return True
    try:
        last_date = datetime.strptime(last_open, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        last_date = datetime.strptime(last_open, "%Y-%m-%d")
    return datetime.now() >= last_date + timedelta(hours=24)


def time_until_next(user):
    last_open = user.get("last_open")
    if not last_open:
        return (0, 0)
    try:
        next_open = datetime.strptime(last_open, "%Y-%m-%d %H:%M:%S") + timedelta(hours=24)
    except ValueError:
        next_open = datetime.strptime(last_open, "%Y-%m-%d") + timedelta(hours=24)
    delta = next_open - datetime.now()
    if delta.total_seconds() <= 0:
        return (0, 0)
    hours = delta.seconds // 3600
    minutes = (delta.seconds % 3600) // 60
    return hours, minutes


async def schedule_notification(bot, user_id):
    """Отправка уведомления через 24 часа или TEST_WAIT_SECONDS"""
    user = get_user(user_id)
    if not user or not user.get("last_open"):
        return

    try:
        last_open = datetime.strptime(user["last_open"], "%Y-%m-%d %H:%M:%S")
    except ValueError:
        last_open = datetime.strptime(user["last_open"], "%Y-%m-%d")

    wait_time = TEST_WAIT_SECONDS if TEST_MODE else (last_open + timedelta(hours=24) - datetime.now()).total_seconds()

    if wait_time <= 0:
        try:
            await bot.send_message(
                user_id,
                "🎉 <b>Вам снова доступен бесплатный кейс с розой!</b>\nИспользуйте /start 🔥",
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"Ошибка уведомления {user_id}: {e}")
        return

    if user_id in scheduled_notifications:
        return

    async def notify_later():
        try:
            await asyncio.sleep(wait_time)
            await bot.send_message(
                user_id,
                "🎉 <b>Вам снова доступен бесплатный кейс с розой!</b>\nИспользуйте /start 🔥",
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"Ошибка при уведомлении {user_id}: {e}")
        finally:
            scheduled_notifications.pop(user_id, None)

    task = asyncio.create_task(notify_later())
    scheduled_notifications[user_id] = task

    if TEST_MODE:
        print(f"🧪 [TEST MODE] Уведомление для {user_id} через {TEST_WAIT_SECONDS} сек.")
    else:
        print(f"⏳ Уведомление для {user_id} через {wait_time / 3600:.2f} часов.")


async def restore_notifications(bot):
    """Перезапуск таймеров уведомлений для всех пользователей после рестарта"""
    data = load_db()
    valid_users = 0
    for user_id, user in data.items():
        if not str(user_id).isdigit():
            continue
        try:
            await schedule_notification(bot, int(user_id))
            valid_users += 1
        except Exception as e:
            print(f"Ошибка восстановления уведомления {user_id}: {e}")
    mode_text = "🧪 Тестовый" if TEST_MODE else "🚀 Рабочий"
    print(f"✅ Уведомления восстановлены ({valid_users} пользователей). Режим: {mode_text}")


# =============================== #
#   Функции для отправки подарка  #
# =============================== #
async def get_gifts(bot):
    """Получить словарь доступных подарков: gift_id -> gift object"""
    try:
        gifts_obj = await bot.get_available_gifts()
        gift_dict = {gift.id: gift for gift in gifts_obj.gifts}
        return gift_dict
    except Exception as e:
        print(f"Ошибка получения подарков: {e}")
        return {}


async def send_gift_to_user(bot, user_id, gift_id, text="Поздравляем!"):
    """Отправка подарка по gift_id"""
    try:
        success = await bot.send_gift(
            user_id=user_id,
            gift_id=gift_id,
            text=text,
            text_parse_mode="HTML"
        )
        return success
    except Exception as e:
        print(f"Ошибка отправки подарка: {e}")
        return False


# =============================== #
#           ГЛАВНОЕ МЕНЮ           #
# =============================== #
@router.message(F.text == "/start")
async def start_menu(message: Message):
    """ГЛАВНОЕ МЕНЮ"""
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💎 Платные кейсы 🎃", callback_data="paid_cases"),
            InlineKeyboardButton(text="🚀 Бесплатный кейс 🎃", callback_data="free_case")
        ],
        [
            InlineKeyboardButton(text="👤 Профиль 🎃", callback_data="profile")
        ]
    ])
    text = (
       "<b>💎 Добро пожаловать в Wayz Case!</b>\n\n"
        "<b>🎃 А так же открывай лимитированный кейс с NFT. Happy Hallowen🎃 !</b>\n\n"
        "💫 Открывай кейсы и получай подарки.\n"
        "Выбери раздел ниже 👇"
    )

    # 🔹 Отправляем изображение и описание
    try:
        photo = FSInputFile("assets/wayzban.png")  # путь к изображению
        await message.answer_photo(
            photo=photo,
            caption=text,
            reply_markup=kb,
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Ошибка при отправке кейса: {e}")
        await message.answer(text, reply_markup=kb, parse_mode="HTML")

    

@router.callback_query(F.data == "free_case")
async def show_free_case(callback: CallbackQuery, bot):
    """Show notification free case"""
    user_id = callback.from_user.id
    username = callback.from_user.username
    data = load_db()
    settings = data.get("settings", {})

    channel = settings.get("required_channel")
    invite_link = settings.get("invite_link")

    user = get_user(user_id) or {}
    can_open = can_open_today(user)

    if not can_open:
        asyncio.create_task(schedule_notification(bot, user_id))

    # LINK FOR SUBS
    if not channel:
        subscribe_url = "https://t.me"
    elif channel.startswith("@"):
        subscribe_url = f"https://t.me/{channel.lstrip('@')}"
    else:
        subscribe_url = invite_link or "https://t.me"
        if not invite_link:
            print(f"⚠️ Для канала {channel} не указана invite_link")

    # 🔹 Кнопки
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Подписаться", url=subscribe_url)],
        [InlineKeyboardButton(text="✅ Проверить подписку", callback_data="check_sub")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
    ])

    # 🔹 Текст статуса
    if can_open:
        status_text = "✅ <b>Кейс доступен!</b>\nНажми «Проверить подписку», чтобы открыть 🎁"
    else:
        hours, minutes = time_until_next(user)
        status_text = f"⏳ <b>Кейс недоступен</b>\nДо следующего открытия: {hours} ч {minutes} мин 🔒"

    await callback.message.answer(
        f"🚀 <b>Бесплатный кейс</b>\n\n"
        f"Каждый день можно открыть кейс и попытаться выбить подарок Rocket \n\n"
        f"{status_text}\n\n"
        f"Сначала подпишись на канал 👇",
        reply_markup=kb,
        parse_mode="HTML"
    )

@router.callback_query(F.data == "profile")
async def show_profile(callback: CallbackQuery):
    user = get_user(callback.from_user.id) or {}
    username = callback.from_user.username or "Без ника"
    roses = user.get("roses", 0)
    cases_opened = user.get("cases_opened", 0)
    stars = user.get("stars", 0)

    text = (
        f"👤 <b>Профиль игрока</b>\n\n"
        f"🪪 ID: <code>{callback.from_user.id}</code>\n"
        f"📛 Никнейм: @{username}\n\n"
        f"🚀 Ракеток: <b>{roses}</b>\n"
        f"📦 Кейсов открыто: <b>{cases_opened}</b>\n"
        f"⭐ Баланс: <b>{stars}</b> Stars"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
    ])
    await callback.message.answer(text, parse_mode="HTML", reply_markup=kb)

  
# ===================== #
#       НАЗАД           #
# ===================== #
@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery):
    await start_menu(callback.message)


# ===================== #
#   ПЛАТНЫЕ КЕЙСЫ       #
# ===================== #
@router.callback_query(F.data == "paid_cases")
async def show_paid_cases(callback: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎃 Dark Spell Case — 25⭐", callback_data="case_dark_spell")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
    ])
    await callback.message.answer("💎 Выбери платный кейс:", reply_markup=kb)

from aiogram.types import FSInputFile

from aiogram.types import FSInputFile, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

# ===================== #
#   DARK SPELL CASE     #
# ===================== #
@router.callback_query(F.data == "case_dark_spell")
async def case_dark_spell_info(callback: CallbackQuery):
    """Показывает описание кейса Dark Spell перед покупкой"""
    user_id = callback.from_user.id

    # 🔹 Описание кейса
    text = (
        "🎃 <b>Dark Spell Case</b>\n\n"
        "💫 Мистический кейс, в котором скрыта редкая NFT и магические призы!\n\n"
        "📊 <b>Шансы выпадения наград:</b>\n"
        "❌ — 5%\n"
        "🧸 — 40%\n"
        "🌹 — 30%\n"
        "🚀 — 15%\n"
        "🪄 NFT: Witch Hat — 10%\n\n"
        "💰 Стоимость открытия: <b>25⭐</b>"
    )

    # 🔹 Кнопки
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Открыть за 25⭐", callback_data="buy_dark_spell")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="paid_cases")]
    ])

    # 🔹 Отправляем изображение и описание
    try:
        photo = FSInputFile("assets/dark_spell_case.jpg")  # путь к изображению
        await callback.message.answer_photo(
            photo=photo,
            caption=text,
            reply_markup=kb,
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Ошибка при отправке кейса: {e}")
        await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")

    await callback.answer()





# =============================== #
#   Проверка подписки и открытие  #
# =============================== #
@router.callback_query(F.data == "check_sub")
async def check_sub_callback(callback, bot):
    user_id = callback.from_user.id
    username = callback.from_user.username
    subscribed = await check_subscription(bot, user_id)
    if not subscribed:
        await callback.answer("❌ Ты не подписан!", show_alert=True)
        return

    user = get_user(user_id) or {}
    if not can_open_today(user):
        hours, minutes = time_until_next(user)
        await callback.message.answer(
            f"😅 Ты уже открывал кейс сегодня!\nПопробуй через {hours} ч {minutes} мин 🌞"
        )
        return

    await callback.message.answer("🎁 <b>Открываем кейс...</b>", parse_mode="HTML")
    await asyncio.sleep(2)
    await callback.message.answer("✨ <i>Вы видите блеск внутри...</i>", parse_mode="HTML")
    await asyncio.sleep(2)

    # Временно 100% шанс выпадения для теста
    # Шанс выпадения 0.2%
    if random.randint(1,1000) == 1:
        new_roses = user.get("roses", 0) + 1
        update_user(user_id, username, roses=new_roses, last_open=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        await callback.message.answer(
            f"🚀 <b>Поздравляем!</b> Тебе выпала ракетка!\nВсего ракеток: {new_roses}",
            parse_mode="HTML"
        )

        # Авто-отправка подарка "мишки за 15 звезд"
        gifts = await get_gifts(bot)
        teddy_gift = None
        for gift in gifts.values():
            emoji = getattr(getattr(gift, "sticker", None), "emoji", "")
            star_count = getattr(gift, "star_count", 0)
            if emoji == "🚀" and star_count == 50:
                teddy_gift = gift
                break

        if teddy_gift:
            sent = await send_gift_to_user(
                bot,
                user_id,
                gift_id=teddy_gift.id,
                text="🚀 Подарок от @wayzcase_bot"
            )
            if sent:
                await callback.message.answer("🚀 Ракетка успешно отправлена в подарок!")
            else:
                await callback.message.answer("❌ Не удалось отправить подарок.")
        else:
            await callback.message.answer("❌ Подарок роза не найдена не найден в доступных подарках.")

        user_link = f"@{username}" if username else f'<a href="tg://user?id={user_id}">Профиль</a>'
        try:
            await bot.send_message(
                ADMIN_ID,
                f"🚀 Пользователь {user_link} выбил Rocket!\n"
                f"🆔 ID: <code>{user_id}</code>\n"
                f"💐 Всего роз: <b>{new_roses}</b>",
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"Ошибка уведомления админа: {e}")
    else:
        update_user(user_id, username, last_open=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), increment_case=True)
        await callback.message.answer("😔 К сожалению, роза не выпала. Попробуй завтра 💫")

    asyncio.create_task(schedule_notification(bot, user_id))

### BUY CASE SUKA
import random
import asyncio
from datetime import datetime
from aiogram.types import CallbackQuery, Message, LabeledPrice, SuccessfulPayment

# ====================== #
#  Автовыдача подарков
# ====================== #


async def get_dark_gifts(bot):
    """Получить словарь доступных подарков: gift_id -> gift object"""
    try:
        gifts_obj = await bot.get_available_gifts()
        gift_dict = {gift.id: gift for gift in gifts_obj.gifts}
        return gift_dict
    except Exception as e:
        print(f"Ошибка получения подарков: {e}")
        return {}

async def send_giftdark_to_user(bot, user_id, gift_id, text="Поздравляем!"):
    """Отправка подарка по gift_id"""
    try:
        return await bot.send_gift(
            user_id=user_id,
            gift_id=gift_id,
            text=text,
            text_parse_mode="HTML"
        )
    except Exception as e:
        print(f"Ошибка отправки подарка: {e}")
        return False

# 🔹 Соответствие предмет -> gift_id
AUTO_GIFTS = {
    "🧸 Мишка": "5170233102089322756",
    "🌹 Роза": '5168103777563050263',
    "🚀 Ракета": '5170564780938756245'
}

async def send_autodark_gift(bot, user_id, item_name):
    """Автовыдача подарка при выпадении из кейса через фиксированный gift_id"""
    if item_name not in AUTO_GIFTS:
        print(f"❌ Подарок {item_name} не настроен для автоподачи")
        return False

    gift_id = AUTO_GIFTS[item_name]

    try:
        sent = await bot.send_gift(
            user_id=user_id,
            gift_id=gift_id,
            text=f"🎁 Твой подарок: {item_name} от @rosecase_bot",
            text_parse_mode="HTML"
        )
        return sent
    except Exception as e:
        print(f"Ошибка отправки подарка {item_name}: {e}")
        return False



# ====================== #
#  Рандом предмета кейса
# ====================== #
def open_dark_spell_case():
    """Рандомный предмет из Dark Spell Case с шансами"""
    items = {
        "❌ Пусто": 55,
        "🧸 Мишка": 30,
        "🌹 Роза": 12,
        "🚀 Ракета": 2.99,
        "NFT — Witch Hat": 0.01
    }
    roll = random.uniform(0, 100)
    cumulative = 0
    for item, chance in items.items():
        cumulative += chance
        if roll <= cumulative:
            return item
    return "❌ Пусто"


# ====================== #
#  Кнопка купить кейс
# ====================== #
@router.callback_query(F.data == "buy_dark_spell")
async def buy_dark_spell_callback(callback: CallbackQuery, bot):
    user_id = callback.from_user.id
    amount = 25  # Стоимость кейса

    invoice_payload = f"case_dark_spell_{user_id}_{int(datetime.now().timestamp())}"
    start_parameter = f"dark_spell_{user_id}_{int(datetime.now().timestamp())}"

    prices = [LabeledPrice(label=f"🎃 Dark Spell Case — {amount}⭐", amount=amount)]

    try:
        await bot.send_invoice(
            chat_id=user_id,
            title="🎃 Dark Spell Case",
            description="Мистический кейс с шансом получить редкие предметы!\nПосле оплаты увидишь анимацию открытия!",
            payload=invoice_payload,
            provider_token="<TOKEN>",  # токен платежного провайдера
            currency="XTR",
            prices=prices,
            start_parameter=start_parameter,
            # test_mode=True
        )
        await callback.answer("💳 Счёт на оплату отправлен!", show_alert=True)
    except Exception as e:
        await callback.answer(f"Ошибка при создании счёта: {e}", show_alert=True)


# ====================== #
#  Обработка успешного платежа
# ====================== #
@router.message(F.successful_payment)
async def success_payment_handler(message: Message, bot):
    payment: SuccessfulPayment = message.successful_payment
    payload = payment.invoice_payload

    if not payload.startswith("case_dark_spell_"):
        return

    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.full_name

    # 🔹 Анимация открытия кейса
    await message.answer("🎁 <b>Открываем кейс...</b>", parse_mode="HTML")
    await asyncio.sleep(2)
    await message.answer("✨ <i>Ты видишь блеск внутри...</i>", parse_mode="HTML")
    await asyncio.sleep(2)

    # 🔹 Рандомный предмет
    item = open_dark_spell_case()
    await message.answer(f"🎉 Поздравляем! Ты получил: {item}!")

    # 🔹 Автовыдача подарков
    if item in AUTO_GIFTS:
        sent = await send_autodark_gift(bot, user_id, item)
        if sent:
            await message.answer(f"🎁 {item} успешно отправлен тебе в подарок!")
        else:
            await message.answer(f"❌ Не удалось отправить подарок {item}.")

    # 🔹 Обновляем статистику пользователя для админ-панели
    # 🔹 Обновляем статистику пользователя для админ-панели
    db = load_db()  # получаем всю базу
    user = db["users"].get(str(user_id), {"username": username, "darkcases_opened": 0, "darkstars_spent": 0})

    # увеличиваем значения
    darkcases_opened = user.get("darkcases_opened", 0) + 1
    darkstars_spent = user.get("darkstars_spent", 0) + 25

    # сохраняем обратно
    update_user(user_id, username, darkcases_opened=darkcases_opened, darkstars_spent=darkstars_spent)
  # сохраняем изменения

    # 🔹 Уведомление админу
    try:
        await bot.send_message(
            ADMIN_ID,
            f"🎃 Пользователь @{username} открыл Dark Spell Case и получил: {item}\n"
        )
    except Exception as e:
        print(f"Ошибка уведомления админа: {e}")

@router.message(F.text.startswith("/refundStarPayment"))
async def refund_handler(message: Message, bot):
    """Возврат XTR-платежа (только для админов)"""
    if message.from_user.id not in ADMINS:
        await message.answer("❌ Только для админов!")
        return

    # Получаем аргументы команды
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("❌ Укажите ID транзакции после команды.")
        return

    transaction_id = parts[1].strip()

    try:
        await bot.refund_star_payment(
            user_id=message.from_user.id,  # ID юзера, которому делаем возврат
            telegram_payment_charge_id=transaction_id
        )
        await message.answer(f"✅ Возврат по транзакции <code>{transaction_id}</code> выполнен успешно", parse_mode="HTML")
    except Exception as e:
        await message.answer(f"❌ Ошибка возврата: {str(e)}")


from aiogram import Router, F
from aiogram.types import Message
from config import ADMIN_ID, ADMIN_2ID
from utils.db_manager import load_db
import asyncio

ADMINS = [ADMIN_ID, ADMIN_2ID]


@router.message(F.text == "/broadcast")
async def start_broadcast(message: Message):
    """Команда для запуска рассылки (только для админов)"""
    if message.from_user.id not in ADMINS:
        return await message.answer("❌ У вас нет доступа к этой команде.")

    await message.answer(
        "📣 Отправь сообщение, которое нужно разослать всем пользователям.\n\n"
        "Можно прикрепить фото и добавить подпись — она тоже будет отправлена."
    )

    # Ожидаем следующее сообщение от админа (в течение 2 минут)
    @router.message(F.from_user.id == message.from_user.id)
    async def get_content(msg: Message):
        db = load_db()
        users = db.get("users", {})

        sent, failed = 0, 0
        await msg.answer("🚀 Начинаю рассылку...")

        for user_id in list(users.keys()):
            try:
                if msg.photo:
                    # Если отправлено фото
                    await msg.bot.send_photo(
                        chat_id=int(user_id),
                        photo=msg.photo[-1].file_id,
                        caption=msg.caption or "📢 Сообщение без подписи",
                    )
                else:
                    # Если обычное текстовое сообщение
                    await msg.bot.send_message(
                        chat_id=int(user_id),
                        text=msg.text or "📢 Пустое сообщение",
                    )
                sent += 1
                await asyncio.sleep(0.05)  # антиспам-пауза
            except Exception:
                failed += 1
                continue

        await msg.answer(
            f"✅ Рассылка завершена!\n\n"
            f"📬 Успешно: <b>{sent}</b>\n"
            f"⚠️ Ошибок: <b>{failed}</b>",
            parse_mode="HTML"
        )

        # удаляем обработчик после рассылки
        router.message.handlers.pop()


