import json
import os
from config import DB_PATH


# --- Вспомогательные функции для работы с JSON ---
def load_db():
    """Загрузка базы данных из JSON-файла"""
    if not os.path.exists(DB_PATH):
        # Если файл отсутствует — создаём базу по умолчанию
        default_data = {
            "users": {},
            "settings": {
                "required_channel": "@example_channel"
            }
        }
        save_db(default_data)
        return default_data

    with open(DB_PATH, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            # Если JSON повреждён — создаём чистую базу
            default_data = {
                "users": {},
                "settings": {"required_channel": "@example_channel"}
            }
            save_db(default_data)
            return default_data


def save_db(data):
    """Сохранение базы данных"""
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# --- Работа с пользователями ---
def get_user(user_id):
    """Получить данные пользователя"""
    db = load_db()
    return db["users"].get(str(user_id))


def update_user(user_id, username, **kwargs):
    """
    Обновить или создать пользователя.
    kwargs может содержать: roses, last_open, cases_opened и т.д.
    """
    db = load_db()
    users = db["users"]

    user = users.get(str(user_id), {
        "username": username,
        "roses": 0,
        "cases_opened": 0,
        "darkcases_opened": 0,
        "darkstars_spent":0,
        "last_open": None
    })

    # Увеличиваем счётчик открытий, если явно передано
    if "increment_case" in kwargs:
        user["cases_opened"] = user.get("cases_opened", 0) + 1
        kwargs.pop("increment_case")

    # Обновляем все переданные поля
    user.update(kwargs)
    users[str(user_id)] = user

    save_db(db)


def get_all_users():
    """Получить всех пользователей"""
    db = load_db()
    return db["users"]


# --- Настройки ---
def get_required_channel():
    """Получить текущий канал обязательной подписки"""
    db = load_db()
    return db["settings"].get("required_channel", "@example_channel")


def set_required_channel(new_channel):
    """Изменить канал обязательной подписки"""
    db = load_db()
    db["settings"]["required_channel"] = new_channel
    save_db(db)

    # =============================== #
#       Баланс бота (XTR)         #
# =============================== #

def load_bot_balance():
    """Загрузка текущего баланса бота"""
    db = load_db()
    if "bot" not in db:
        db["bot"] = {"balance": 0}
        save_db(db)
    return db["bot"].get("balance", 0)


def update_bot_balance(new_balance: int):
    """Обновление баланса бота"""
    db = load_db()
    if "bot" not in db:
        db["bot"] = {}
    db["bot"]["balance"] = new_balance
    save_db(db)

