from datetime import date, datetime, timedelta
from config import db

users_collection = db["users"]
orders_collection = db["orders"]

async def add_user(user_id: int, username: str, timezone: str = 'Europe/Kyiv'):
    """Реєструє або оновлює дані користувача та його таймзону."""
    await users_collection.update_one(
        {"_id": user_id},
        {"$set": {"username": username, "timezone": timezone}},
        upsert=True
    )

async def get_all_users():
    """Повертає список всіх користувачів для планувальника."""
    users = []
    cursor = users_collection.find({}, {"_id": 1, "timezone": 1})
    async for document in cursor:
        users.append((document["_id"], document["timezone"]))
    return users

async def get_user_timezone(user_id: int) -> str:
    """Повертає часовий пояс користувача або стандартний Europe/Kyiv."""
    user = await users_collection.find_one({"_id": user_id}, {"timezone": 1})
    if user and user.get("timezone"):
        return user["timezone"]
    return "Europe/Kyiv"

async def save_remote_work_day(user_id: int, remote_work_date: str):
    """Зберігає дату віддаленої роботи для користувача."""
    await users_collection.update_one(
        {"_id": user_id},
        {"$set": {"remote_work_date": remote_work_date}},
        upsert=True
    )

async def get_remote_work_date(user_id: int):
    """Повертає збережену дату віддаленої роботи користувача."""
    user = await users_collection.find_one({"_id": user_id}, {"remote_work_date": 1})
    if user and user.get("remote_work_date"):
        return user["remote_work_date"]
    return None

async def should_skip_lunch_reminder(user_id: int, current_date: date) -> bool:
    """Повертає True, якщо сьогодні — день перед віддаленою роботою."""
    remote_work_date_str = await get_remote_work_date(user_id)
    if not remote_work_date_str:
        return False

    try:
        remote_work_date = datetime.strptime(remote_work_date_str, "%Y-%m-%d").date()
    except ValueError:
        return False

    return current_date == remote_work_date - timedelta(days=1)

async def confirm_order(user_id: int):
    """Фіксує, що користувач замовив обід на сьогоднішню дату."""
    today_date = datetime.now().strftime("%Y-%m-%d")

    await orders_collection.update_one(
        {"date": today_date, "user_id": user_id},
        {"$set": {"has_ordered": True}},
        upsert=True
    )

async def check_order_status(user_id: int) -> bool:
    """Перевіряє, чи замовив користувач обід сьогодні. Повертає True, якщо замовив."""
    today_date = datetime.now().strftime("%Y-%m-%d")

    order = await orders_collection.find_one({"date": today_date, "user_id": user_id})
    if order and order.get("has_ordered") is True:
        return True
    return False

async def clear_old_orders():
    """Повністю видаляє всі документи з колекції замовлень."""
    result = await orders_collection.delete_many({})
    print(f"🧹 Базу даних очищено! Видалено замовлень: {result.deleted_count}")
