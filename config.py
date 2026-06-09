import os
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from motor.motor_asyncio import AsyncIOMotorClient
import certifi

# Зчитування .env
if os.path.exists(".env"):
    with open(".env") as f:
        for line in f:
            if line.strip() and not line.startswith("#"):
                key, value = line.strip().split("=", 1)
                os.environ[key] = value

BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")

if not BOT_TOKEN:
    raise ValueError("Помилка: BOT_TOKEN не знайдено!")

# Ініціалізація бота та диспетчера
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# Підключення до MongoDB (база даних буде називатися lunch_bot_db)
mongo_client = AsyncIOMotorClient(MONGO_URI, tlsCAFile=certifi.where())
db = mongo_client["lunch_bot_db"]