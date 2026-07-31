import calendar
from datetime import date, datetime
from config import db

users_collection = db["users"]
orders_collection = db["orders"]
remote_work_collection = db["remote_work_events"]

async def add_user(user_id: int, username: str, timezone: str = 'Europe/Kyiv'):
    """Реєструє або оновлює дані користувача та його таймзону."""
    await users_collection.update_one(
        {"_id": user_id},
        {
            "$set": {"username": username, "timezone": timezone},
            "$setOnInsert": {"created_at": datetime.utcnow()},
        },
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

async def save_remote_work_day(user_id: int, remote_work_date: str, selected_day: str):
    """Зберігає дату віддаленої роботи для користувача."""
    await users_collection.update_one(
        {"_id": user_id},
        {"$set": {"remote_work_date": remote_work_date}},
        upsert=True
    )
    await remote_work_collection.insert_one({
        "user_id": user_id,
        "selected_day": selected_day,
        "remote_work_date": remote_work_date,
        "selected_at": datetime.utcnow(),
    })

async def get_remote_work_date(user_id: int):
    """Повертає збережену дату віддаленої роботи користувача."""
    user = await users_collection.find_one({"_id": user_id}, {"remote_work_date": 1})
    if user and user.get("remote_work_date"):
        return user["remote_work_date"]
    return None

async def should_skip_lunch_reminder(user_id: int, lunch_date: date) -> bool:
    """Повертає True, якщо нагадування стосується обіду в день віддаленої роботи."""
    remote_work_date_str = await get_remote_work_date(user_id)
    if not remote_work_date_str:
        return False

    try:
        remote_work_date = datetime.strptime(remote_work_date_str, "%Y-%m-%d").date()
    except ValueError:
        return False

    return lunch_date == remote_work_date

async def confirm_order(user_id: int):
    """Фіксує, що користувач замовив обід на сьогоднішню дату."""
    today_date = datetime.now().strftime("%Y-%m-%d")

    await orders_collection.update_one(
        {"date": today_date, "user_id": user_id},
        {"$set": {"has_ordered": True, "confirmed_at": datetime.utcnow()}},
        upsert=True
    )

async def check_order_status(user_id: int) -> bool:
    """Перевіряє, чи замовив користувач обід сьогодні. Повертає True, якщо замовив."""
    today_date = datetime.now().strftime("%Y-%m-%d")

    order = await orders_collection.find_one({"date": today_date, "user_id": user_id})
    if order and order.get("has_ordered") is True:
        return True
    return False

async def get_current_month_report():
    """Повертає статистику використання бота від першого числа поточного місяця."""
    now = datetime.utcnow()
    month_start = datetime(now.year, now.month, 1)
    month_start_date = month_start.strftime("%Y-%m-%d")

    order_filter = {
        "$or": [
            {"confirmed_at": {"$gte": month_start}},
            {"confirmed_at": {"$exists": False}, "date": {"$gte": month_start_date}},
        ]
    }
    order_pipeline = [
        {"$match": order_filter},
        {"$group": {"_id": "$user_id", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    order_rows = await orders_collection.aggregate(order_pipeline).to_list(length=None)
    remote_rows = await remote_work_collection.aggregate([
        {"$match": {"selected_at": {"$gte": month_start}}},
        {"$group": {"_id": "$selected_day", "count": {"$sum": 1}}},
    ]).to_list(length=None)

    active_user_ids = {row["_id"] for row in order_rows}
    remote_user_ids = await remote_work_collection.distinct(
        "user_id", {"selected_at": {"$gte": month_start}}
    )
    active_user_ids.update(remote_user_ids)

    order_user_ids = [row["_id"] for row in order_rows]
    users_by_id = {}
    if order_user_ids:
        cursor = users_collection.find(
            {"_id": {"$in": order_user_ids}}, {"username": 1}
        )
        async for user in cursor:
            users_by_id[user["_id"]] = user.get("username") or str(user["_id"])

    return {
        "year": now.year,
        "month": now.month,
        "total_users": await users_collection.count_documents({}),
        "new_users": await users_collection.count_documents({"created_at": {"$gte": month_start}}),
        "active_users": len(active_user_ids),
        "confirmed_orders": sum(row["count"] for row in order_rows),
        "orders_by_user": [
            {"username": users_by_id.get(row["_id"], str(row["_id"])), "count": row["count"]}
            for row in order_rows
        ],
        "remote_choices": {row["_id"]: row["count"] for row in remote_rows},
    }


def _two_months_ago(now: datetime) -> datetime:
    """Повертає таку саму дату два календарні місяці тому."""
    month = now.month - 2
    year = now.year
    if month <= 0:
        month += 12
        year -= 1
    day = min(now.day, calendar.monthrange(year, month)[1])
    return now.replace(year=year, month=month, day=day)


async def clear_old_analytics_data():
    """Видаляє дані про замовлення та remote work, старші за два календарні місяці."""
    cutoff = _two_months_ago(datetime.utcnow())
    cutoff_date = cutoff.strftime("%Y-%m-%d")
    orders_result = await orders_collection.delete_many({
        "$or": [
            {"confirmed_at": {"$lt": cutoff}},
            {"confirmed_at": {"$exists": False}, "date": {"$lt": cutoff_date}},
        ]
    })
    remote_result = await remote_work_collection.delete_many({"selected_at": {"$lt": cutoff}})
    print(
        "🧹 Очищено застарілі дані: "
        f"замовлень — {orders_result.deleted_count}, remote-виборів — {remote_result.deleted_count}"
    )
