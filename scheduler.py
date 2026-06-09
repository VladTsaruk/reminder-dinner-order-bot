import asyncio
from datetime import datetime
import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Імпортуємо нову функцію clear_old_orders
import database as db
from config import bot

def get_lunch_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Я замовив обід!", callback_data="confirm_lunch")]
    ])

async def check_and_send_reminders():
    """Головна функція перевірки (неділя-четвер)."""
    users = await db.get_all_users() 
    
    for user_id, tz_name in users:
        try:
            user_tz = pytz.timezone(tz_name)
            user_now = datetime.now(pytz.utc).astimezone(user_tz)
            
            valid_days = [6, 0, 1, 2, 3] # Неділя - Четвер
            
            if user_now.weekday() not in valid_days:
                continue
                
            current_time_str = user_now.strftime("%H:%M")
            
            # --- ХВИЛЯ 1: 17:00 ---
            if current_time_str == "17:50":
                if not await db.check_order_status(user_id):
                    await bot.send_message(
                        chat_id=user_id,
                        text="⏰ *Нагадування про обід!*\n\nДо кінця прийому замовлень залишилася 1 година. Не забудь замовити свій обід! 🍽️",
                        reply_markup=get_lunch_keyboard(),
                        parse_mode=None,
                    )
            
            # --- ХВИЛЯ 2: 17:30 ---
            elif current_time_str == "17:53":
                if not await db.check_order_status(user_id):
                    await bot.send_message(
                        chat_id=user_id,
                        text="⚠️ *Залишилося 30 хвилин!*\n\nТи досі не підтвердив замовлення обіду. Будь ласка, замов їжу та натисни кнопку нижче! 👇",
                        reply_markup=get_lunch_keyboard(),
                        parse_mode=None,
                    )
                    
        except Exception as e:
            print(f"Помилка відправки для користувача {user_id}: {e}")

def start_scheduler():
    """Ініціалізація планувальника."""
    scheduler = AsyncIOScheduler()
    
    # 1. Перевірка нагадувань — щохвилини
    scheduler.add_job(check_and_send_reminders, 'cron', second=0)
    
    # 2. Автоматичне очищення бази даних — щосуботи (day_of_week='sat') о 03:00 ночі
    scheduler.add_job(db.clear_old_orders, 'cron', day_of_week='sat', hour=3, minute=0)
    
    scheduler.start()
    print("📅 Планувальник нагадувань та таска очищення БД запущені!")
