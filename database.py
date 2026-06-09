from datetime import datetime
from config import db

users_collection = db["users"]
orders_collection = db["orders"]

async def add_user(user_id: int, username: str, timezone: str = 'Europe/Kyiv'):
    """Реєструє або оновлює дані користувача та його таймзону."""
    # В MongoDB зручно використовувати Telegram user_id як унікальний токен "_id"
    await users_collection.update_one(
        {"_id": user_id},
        {"$set": {"username": username, "timezone": timezone}},
        upsert=True  # Якщо користувача немає — він створиться, якщо є — оновиться
    )

async def get_all_users():
    """Повертає список всіх користувачів для планувальника."""
    users = []
    # cursor дозволяє перебирати документи в колекції
    cursor = users_collection.find({}, {"_id": 1, "timezone": 1})
    async for document in cursor:
        # Перетворюємо у такий же формат, як був у SQLite: (user_id, timezone)
        users.append((document["_id"], document["timezone"]))
    return users

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