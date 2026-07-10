from datetime import datetime, timedelta
from aiogram import Router, F  # type: ignore
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton  # type: ignore
from aiogram.filters import CommandStart  # type: ignore
import database as db
from config import ADMIN_USER_ID, MENU_URL, bot

router = Router()


def get_lunch_keyboard():
    """Створює інтерактивну кнопку для підтвердження обіду."""
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


def get_remote_work_keyboard():
    """Створює кнопки для вибору дня віддаленої роботи."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🗓️ Вівторок", callback_data="remote_day_tuesday"),
            InlineKeyboardButton(text="🗓️ Середа", callback_data="remote_day_wednesday"),
            InlineKeyboardButton(text="🗓️ Четвер", callback_data="remote_day_thursday"),
        ],
        [
            InlineKeyboardButton(text="🚫 Не беру віддалену роботу", callback_data="remote_day_none"),
        ]
    ])


def get_remote_work_date(selected_day: str) -> str:
    """Обчислює дату обраного дня віддаленої роботи в поточному тижні."""
    today = datetime.now().date()
    weekday_map = {"tuesday": 1, "wednesday": 2, "thursday": 3}
    target_weekday = weekday_map[selected_day]
    current_weekday = today.weekday()
    delta = (target_weekday - current_weekday) % 7
    return (today + timedelta(days=delta)).strftime("%Y-%m-%d")


@router.message(CommandStart())
async def cmd_start(message: Message):
    """Обробка команди /start. Реєструємо користувача в MongoDB."""
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name

    await db.add_user(user_id=user_id, username=username, timezone="Europe/Kyiv")

    await message.answer(
        f"Привіт, {username}! 👋\n\n"
        f"Я твій обідній бот-нагадувачка.\n"
        f"З неділі по четвер о 17:00 я буду нагадувати тобі замовити їжу.\n"
        f"Щопонеділка о 13:00 я також спитую, коли ти працюватимеш віддалено."
    )


@router.callback_query(F.data == "confirm_lunch")
async def process_confirm_lunch(callback: CallbackQuery):
    """Обробка натискання на кнопку підтвердження."""
    user_id = callback.from_user.id

    await db.confirm_order(user_id)

    await callback.message.edit_text(
        "ℹ️ *Нагадування про обід*\n\n"
        "Чудово! Твоє замовлення підтверджено. Смачного! 🍽️"
    )
    await callback.answer("Статус оновлено!")


@router.callback_query(F.data.startswith("remote_day_"))
async def process_remote_work_day(callback: CallbackQuery):
    """Зберігає обраний день віддаленої роботи користувача або відмову від неї."""
    selected_day = callback.data.split("remote_day_", 1)[1]
    if selected_day not in {"tuesday", "wednesday", "thursday", "none"}:
        await callback.answer("Невірний вибір")
        return

    if selected_day == "none":
        await db.save_remote_work_day(callback.from_user.id, "none")
        await callback.message.edit_text(
            "✅ Дякую! Я запам'ятав, що цього тижня ти не береш віддалену роботу."
        )
        await callback.answer("Вибір збережено!")
        return

    remote_work_date = get_remote_work_date(selected_day)
    await db.save_remote_work_day(callback.from_user.id, remote_work_date)

    day_labels = {
        "tuesday": "вівторок",
        "wednesday": "середу",
        "thursday": "четвер",
    }

    await callback.message.edit_text(
        f"✅ Дякую! Я запам'ятав, що ти працюватимеш віддалено {day_labels[selected_day]} ({remote_work_date})."
    )
    await callback.answer("День збережено!")


@router.message(F.text == "/test_remote_question")
async def cmd_test_remote_question(message: Message):
    """Тестова команда для адміністратора: відправляє повідомлення про віддалену роботу."""
    if message.from_user.id != ADMIN_USER_ID:
        await message.answer("Ця команда доступна лише адміністратору.")
        return

    await bot.send_message(
        chat_id=message.chat.id,
        text="📅 Тестове повідомлення: коли ти працюватимеш віддалено на цьому тижні?\n\nОбери один день:",
        reply_markup=get_remote_work_keyboard(),
    )
    await message.answer("Тестове повідомлення відправлено.")


@router.message(F.text == "/help")
async def cmd_help(message: Message):
    """Обробка команди /help."""
    await message.answer(
        "🆘 *Допомога*\n\n"
        "Цей бот допомагає тобі не забувати замовляти обід.\n"
        "Просто чекай на нагадування о 17:00 з неділі по четвер і натискай кнопку, щоб підтвердити замовлення.\n\n"
        "Щопонеділка о 13:00 я також питатиму, коли ти працюватимеш віддалено.\n"
        "Для адміністратора доступна команда /test_remote_question для перевірки повідомлення.\n"
        "Якщо у тебе є питання або пропозиції, звертайся до `@Владислав Царук` в Slack."
    )
