from aiogram import Router, F
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    LabeledPrice,
    PreCheckoutQuery,
    SuccessfulPayment
)
from config import ADMIN_ID
from utils.db_manager import load_bot_balance, update_bot_balance  # свои функции для баланса бота

ADMINS = [ADMIN_ID]

router = Router()

# =============================== #
#       Команда /payment_stars    #
# =============================== #
@router.message(F.text == "/payment_stars")
async def payment_stars_handler(message: Message):
    if message.from_user.id not in ADMINS:
        await message.answer("❌ Только для админов!")
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 25 ⭐️", callback_data="topup_25")],
        [InlineKeyboardButton(text="💰 50 ⭐️", callback_data="topup_50")],
        [InlineKeyboardButton(text="💰 500 ⭐️", callback_data="topup_500")],
        [InlineKeyboardButton(text="💰 1000 ⭐️", callback_data="topup_1000")]
    ])
    await message.answer("Выберите сумму для пополнения баланса бота:", reply_markup=kb)


# =============================== #
#       Выбор суммы для пополнения
# =============================== #
@router.callback_query(F.data.startswith("topup_"))
async def topup_callback(callback, bot):
    if callback.from_user.id not in ADMINS:
        await callback.answer("❌ Только для админов!", show_alert=True)
        return

    amount = int(callback.data.split("_")[1])  # Получаем сумму
    invoice_payload = f"bot_balance_{amount}"
    start_parameter = f"bot_xtr_topup_{amount}"

    prices = [LabeledPrice(label=f"💰 Пополнение {amount} ⭐️", amount=amount)]

    try:
        await bot.send_invoice(
            chat_id=callback.from_user.id,
            title="Пополнение баланса бота",
            description=f"Добавляет {amount} ⭐️ на баланс бота для автоотправки подарков.",
            payload=invoice_payload,
            provider_token="",  # токен XTR или test_mode токен
            currency="XTR",
            prices=prices,
            start_parameter=start_parameter,
            # test_mode=True  # включить для теста
        )
        await callback.answer("💳 Счёт создан!", show_alert=True)
    except Exception as e:
        await callback.answer(f"Ошибка при создании счета: {e}", show_alert=True)


# =============================== #
#       PreCheckout Handler       #
# =============================== #
@router.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_query: PreCheckoutQuery):
    # Всегда подтверждаем pre_checkout
    await pre_checkout_query.answer(ok=True)


# =============================== #
#       Successful Payment Handler
# =============================== #
@router.message(F.successful_payment)
async def success_payment_handler(message: Message):
    payment: SuccessfulPayment = message.successful_payment
    payload = payment.invoice_payload  # payload из send_invoice

    if payload.startswith("bot_balance_"):
        try:
            amount = int(payload.split("_")[2])
        except Exception:
            await message.answer("❌ Ошибка при обработке суммы пополнения.")
            return

        # Обновляем баланс бота
        current_balance = load_bot_balance()
        new_balance = current_balance + amount
        update_bot_balance(new_balance)

        # Сообщаем админу и пользователю
        await message.answer(
            f"✅ Баланс бота успешно пополнен на {amount} ⭐️!\n"
            f"Текущий баланс: {new_balance} ⭐️."
        )

        try:
            await message.bot.send_message(
                ADMIN_ID,
                f"💳 Админ {message.from_user.full_name} пополнил баланс бота на {amount} ⭐️.\n"
                f"Новый баланс бота: {new_balance} ⭐️."
            )
        except Exception as e:
            print(f"Ошибка уведомления админа: {e}")
