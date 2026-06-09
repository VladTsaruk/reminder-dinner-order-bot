from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart
import database as db
from config import bot

router = Router()
ADMIN_USER_ID = 8504572391

def get_lunch_keyboard():
    """Створює інтерактивну кнопку для підтвердження обіду\."""
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
        "Посилання на меню: [Меню](https://imperialfood.com.ua/iEmployee/#!menu)"
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


@router.message(F.text.startswith("/send"))
async def cmd_send_reminder(message: Message):
    """Ручна розсилка нагадування всім користувачам від адміна."""
    user_id = message.from_user.id

    if user_id != ADMIN_USER_ID:
        await message.answer("❌ У вас немає доступу до цієї команди\\.")
        return

    parts = (message.text or "").split(maxsplit=1)
    reminder_time = parts[1].strip() if len(parts) > 1 else ""

    if not reminder_time:
        await message.answer("Використання: /send 17:40", parse_mode=None)
        return

    try:
        hour, minute = reminder_time.split(":", 1)
        hour_number = int(hour)
        minute_number = int(minute)
        if hour_number < 0 or hour_number > 23 or minute_number < 0 or minute_number > 59:
            raise ValueError
        reminder_time = f"{hour_number:02d}:{minute_number:02d}"
    except ValueError:
        await message.answer("Час має бути у форматі HH:MM, наприклад /send 17:40", parse_mode=None)
        return

    users = await db.get_all_users()
    sent_count = 0
    skipped_count = 0
    failed_count = 0

    for target_user_id, _ in users:
        try:
            if await db.check_order_status(target_user_id):
                skipped_count += 1
                continue

            await bot.send_message(
                chat_id=target_user_id,
                text=(
                    f"⏰ Нагадування про обід!\n\n"
                    f"Зараз {reminder_time}. Не забудь замовити свій обід! 🍽️"
                ),
                reply_markup=get_lunch_keyboard(),
                parse_mode=None,
            )
            sent_count += 1
        except Exception as e:
            failed_count += 1
            print(f"Помилка ручної розсилки для користувача {target_user_id}: {e}")

    await message.answer(
        (
            "Ручну розсилку завершено.\n"
            f"Відправлено: {sent_count}\n"
            f"Пропущено вже замовивших: {skipped_count}\n"
            f"Помилок: {failed_count}"
        ),
        parse_mode=None,
    )


# Додаємо команду для тестування розсилки
@router.message(F.text == "/test_reminder")
async def cmd_test_reminder(message: Message):
    user_id = message.from_user.id
    
    # Перевірка, чи це наш тестовий користувач
    if user_id != ADMIN_USER_ID:
        await message.answer("❌ У вас немає доступу до цієї команди\.")
        return
        
    # Перевіряємо статус в базі даних (імітуємо поведінку планувальника)
    has_ordered = await db.check_order_status(user_id)
    
    if not has_ordered:
        await message.answer(
            "🧪 *[ТЕСТ] Нагадування про обід\!*\n\n"
            "Це тестовий запуск логіки 17:00\. Будь ласка\, натисніть кнопку нижче\, щоб перевірити фіксацію в базі даних MongoDB\.",
            reply_markup=get_lunch_keyboard()
        )
    else:
        await message.answer(
            "🧪 *[ТЕСТ]* Логіка перевірки спрацювала\, але в базі даних для тебе на сьогодні вже стоїть статус *'Замовлено'*\.\n\n"
            "Щоб скинути статус для наступного тесту\, зачекай очищення або видали запис\."
        )
