import asyncio
from datetime import datetime, timedelta
import pytz # type: ignore
from apscheduler.schedulers.asyncio import AsyncIOScheduler # type: ignore
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton # type: ignore

import database as db
from config import MENU_URL, bot
from handlers import get_remote_work_keyboard


def get_lunch_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Я замовив обід!", callback_data="confirm_lunch")],
        [InlineKeyboardButton(text="📋 Меню", url=MENU_URL)],
    ])


async def check_and_send_reminders():
    users = await db.get_all_users()

    for user_id, tz_name in users:
        try:
            user_tz = pytz.timezone(tz_name)
            user_now = datetime.now(pytz.utc).astimezone(user_tz)

            lunch_date = user_now.date() + timedelta(days=2)

            # Замовлення потрібні лише для обідів у робочі дні (понеділок-п'ятниця).
            if lunch_date.weekday() > 4:
                continue

            if await db.should_skip_lunch_reminder(user_id, lunch_date):
                continue

            current_time_str = user_now.strftime("%H:%M")

            if current_time_str == "15:00":
                if not await db.check_order_status(user_id):
                    await bot.send_message(
                        chat_id=user_id,
                        text=(
                            "⏰ *Нагадування про обід!*\n\n"
                            f"Не забудь замовити обід на {lunch_date.strftime('%d.%m.%Y')}. "
                            "Прийом замовлень завершується о 07:00 наступного ранку. 🍽️"
                        ),
                        reply_markup=get_lunch_keyboard(),
                        parse_mode="Markdown",
                    )
            elif current_time_str == "18:00":
                if not await db.check_order_status(user_id):
                    await bot.send_message(
                        chat_id=user_id,
                        text=(
                            "⏰ *Нагадування про обід!*\n\n"
                            f"Не забудь замовити обід на {lunch_date.strftime('%d.%m.%Y')}. "
                            "Прийом замовлень завершується о 07:00 наступного ранку. 🍽️"
                        ),
                        reply_markup=get_lunch_keyboard(),
                        parse_mode="Markdown",
                    )
                    
        except Exception as e:
            print(f"Помилка відправки для користувача {user_id}: {e}")


async def send_remote_work_question():
    """Щосуботи о 13:00 питає користувача про віддалену роботу наступного тижня."""
    users = await db.get_all_users()

    for user_id, tz_name in users:
        try:
            user_tz = pytz.timezone(tz_name)
            user_now = datetime.now(pytz.utc).astimezone(user_tz)

            if user_now.weekday() != 5:
                continue

            current_time_str = user_now.strftime("%H:%M")
            if current_time_str != "13:00":
                continue

            await bot.send_message(
                chat_id=user_id,
                text="📅 Коли ти працюватимеш віддалено наступного тижня?\n\nОбери один день:",
                reply_markup=get_remote_work_keyboard(),
                parse_mode=None,
            )
        except Exception as e:
            print(f"Помилка відправки питання про віддалену роботу для користувача {user_id}: {e}")


def start_scheduler():
    """Ініціалізація планувальника."""
    scheduler = AsyncIOScheduler()

    # 1. Перевірка нагадувань — щохвилини, відправка о 15:00 за локальним часом
    scheduler.add_job(check_and_send_reminders, 'cron', second=0)

    # 2. Щосуботи о 13:00 за часовим поясом користувача — питання про віддалену роботу
    scheduler.add_job(send_remote_work_question, 'cron', second=0)

    # 3. Очищення аналітичних даних, старших за два місяці — щосуботи о 03:00
    scheduler.add_job(db.clear_old_analytics_data, 'cron', day_of_week='sat', hour=3, minute=0)

    scheduler.start()
    print("📅 Планувальник нагадувань, remote work і очищення даних старших за два місяці запущені!")
