from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart
import database as db
from config import ADMIN_USER_ID, MENU_URL

router = Router()

def get_lunch_keyboard():
    """Створює інтерактивну кнопку для підтвердження обіду\."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Я замовив обід!", 
                callback_data="confirm_lunch"
            )
        ],
        [
            InlineKeyboardButton(
                text="📋 Меню",
                url=MENU_URL,
            )
        ]
    ])

@router.message(CommandStart())
async def cmd_start(message: Message):
    """Обробка команди /start. Реєструємо користувача в MongoDB\."""
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    
    # Додаємо await, бо функція асинхронна
    await db.add_user(user_id=user_id, username=username, timezone="Europe/Kyiv")
    
    await message.answer(
        f"Привіт\, {username}\! 👋\n\n"
        f"Я твій обідній бот\-нагадувачка\.\n"
        f"З неділі по четвер о _17:00_ я буду нагадувати тобі замовити їжу\.\n"
    )

@router.callback_query(F.data == "confirm_lunch")
async def process_confirm_lunch(callback: CallbackQuery):
    """Обробка натискання на кнопку підтвердження\."""
    user_id = callback.from_user.id
    
    # Додаємо await для фіксації замовлення в MongoDB
    await db.confirm_order(user_id)
    
    # Змінюємо текст повідомлення, прибираючи кнопку
    await callback.message.edit_text(
        "ℹ️ *Нагадування про обід*\n\n"
        "Чудово\! Твоє замовлення підтверджено\. Смачного\! 🍽️"
    )
    await callback.answer("Статус оновлено\!")

@router.message(F.text == "/help")
async def cmd_help(message: Message):
    """Обробка команди /help\."""
    await message.answer(
        "🆘 *Допомога*\n\n"
        "Цей бот допомагає тобі не забувати замовляти обід\.\n"
        "Просто чекай на нагадування о 17:00 з неділі по четвер і натискай кнопку, щоб підтвердити замовлення\.\n\n"
        "Якщо у тебе є питання або пропозиції\, звертайся до `@Владислав Царук` в Slack\."
    )
