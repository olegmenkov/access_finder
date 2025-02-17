import logging
import asyncio
import requests
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from geopy.distance import geodesic
from dotenv import load_dotenv
import os

from map_functions import get_coordinates, get_accessible_places, get_address

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Хранилище координат для пользователей (грязно, но работает -- можешь сделать, чтоб было более изящно)
user_coordinates = {}

YANDEX_MAPS_URL = "https://yandex.ru/maps/?ll={lon}%2C{lat}&z=16"


class BotStates(StatesGroup):
    waiting_for_district = State()
    # новое_имя_состояния = State()


@dp.message(Command("start"))
async def send_welcome(message: Message):
    """Команда /start, которая выводит список доступных команд и их описание"""
    commands_list = """
Доступные команды:
/start - Показать список команд и их описание
/help - Получить помощь
/search - Начать поиск доступных мест
"""
    await message.answer(commands_list)


@dp.message(Command("help"))
async def send_help(message: Message):
    """Команда /help, которая предоставляет помощь пользователю"""
    help_text = """
Этот бот помогает найти доступные места в Москве.
Используйте команду /search, чтобы начать поиск.
"""
    await message.answer(help_text)


@dp.message(Command("search"))
async def start_search(message: Message, state: FSMContext):
    """Команда /search, которая начинает процесс поиска"""
    await message.answer("Введите название района Москвы:")
    await state.set_state(BotStates.waiting_for_district)


"""@dp.message(Command("новое_имя_команды"))
async def start_search(message: Message, state: FSMContext):
    await message.answer("бебебе и бабаба")
"""


@dp.message(BotStates.waiting_for_district)
async def process_district(message: Message, state: FSMContext):
    """Обработка введённого района"""
    district = message.text
    coordinates = await get_coordinates(district)
    if not coordinates:
        await message.answer("Не удалось найти координаты района. Попробуйте еще раз.")
        return

    user_coordinates[message.chat.id] = coordinates

    # Клавиатура для выбора категории
    builder = InlineKeyboardBuilder()
    categories = ["кафе", "магазины", "транспорт", "музеи", "больницы"]
    for category in categories:
        builder.add(types.InlineKeyboardButton(
            text=category.capitalize(), callback_data=f"category_{category}")
        )
    builder.adjust(2)
    await message.answer("Выберите категорию:", reply_markup=builder.as_markup())

    # Сбрасываем состояние
    await state.clear()


@dp.callback_query(lambda c: c.data.startswith('category_'))
async def process_category(callback: CallbackQuery):
    """Обработка выбора категории"""
    category = callback.data.split('_')[1]
    user_id = callback.message.chat.id

    if user_id not in user_coordinates:
        await callback.message.answer("Сначала введите название района.")
        return

    lat, lon = user_coordinates[user_id]
    places = await get_accessible_places(lat, lon, category)

    if not places:
        await callback.message.answer("Нет данных о доступных местах в этой категории.")
        return

    for place in places:
        # Формируем URL с отметкой точки
        yandex_url = f"https://yandex.ru/maps/?ll={place['lon']},{place['lat']}&pt={place['lon']},{place['lat']},pm2blm&z=16"
        address = get_address(place["lat"], place["lon"])
        await callback.message.answer(
            f"{place['name']}\n"
            f"Адрес: {address}\n"
            f"Координаты: {place['lat']}, {place['lon']}\n"
            f"Яндекс.Карты: {yandex_url}"
        )


if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))
