from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart
import database as db

router = Router()

def get_lunch_keyboard():
    """Створює інтерактивну кнопку для підтвердження обіду."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Я замовив обід!", 
                callback_data="confirm_lunch"
            )
        ]
    ])

@router.message(CommandStart())
async def cmd_start(message: Message):
    """Обробка команди /start. Реєструємо користувача в MongoDB."""
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    
    # Додаємо await, бо функція асинхронна
    await db.add_user(user_id=user_id, username=username, timezone="Europe/Kyiv")
    
    await message.answer(
        f"Привіт, {username}! 👋\n\n"
        f"Я твій обідній бот-нагадувачка.\n"
        f"З неділі по четвер о **17:00** я буду нагадувати тобі замовити їжу.\n"
    )

@router.callback_query(F.data == "confirm_lunch")
async def process_confirm_lunch(callback: CallbackQuery):
    """Обробка натискання на кнопку підтвердження."""
    user_id = callback.from_user.id
    
    # Додаємо await для фіксації замовлення в MongoDB
    await db.confirm_order(user_id)
    
    # Змінюємо текст повідомлення, прибираючи кнопку
    await callback.message.edit_text(
        "ℹ️ **Нагадування про обід**\n\n"
        "Чудово! Твоє замовлення підтверджено. Смачного! 🍽️"
    )
    await callback.answer("Статус оновлено!")

# Додаємо команду для тестування розсилки
@router.message(F.text == "/test_reminder")
async def cmd_test_reminder(message: Message):
    user_id = message.from_user.id
    
    # Перевірка, чи це наш тестовий користувач
    if user_id != 8504572391:
        await message.answer("❌ У вас немає доступу до цієї команди.")
        return
        
    # Перевіряємо статус в базі даних (імітуємо поведінку планувальника)
    has_ordered = await db.check_order_status(user_id)
    
    if not has_ordered:
        await message.answer(
            "🧪 **[ТЕСТ] Нагадування про обід!**\n\n"
            "Це тестовий запуск логіки 17:00. Будь ласка, натисніть кнопку нижче, щоб перевірити фіксацію в базі даних MongoDB.",
            reply_markup=get_lunch_keyboard()
        )
    else:
        await message.answer(
            "🧪 **[ТЕСТ]** Логіка перевірки спрацювала, але в базі даних для тебе на сьогодні вже стоїть статус **'Замовлено'**.\n\n"
            "Щоб скинути статус для наступного тесту, зачекай очищення або видали запис."
        )