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
Здравствуйте! 
Я - бот, который помогает маломобильным людям в Москве.
Чтобы узнать побольше о том, что я умею, вызовите команду /about
"""
    await message.answer(commands_list)


@dp.message(Command("about"))
async def send_about(message: Message):
    """Команда /about, которая предоставляет помощь пользователю"""
    help_text = """
У меня есть такие команды:
/start - Начать работу с ботом
/sos - Получить контакты экстренных служб
/search - Показать места поблизости, доступные на инвалидной коляске
/contacts - Получить контакты помогающих организаций г. Москвы
/about - Как пользоваться ботом
"""
    await message.answer(help_text)


@dp.message(Command("sos"))
async def send_sos(message: Message):
    """Команда /sos, которая показывает номера служб"""
    phones = """
🚒 Пожарная охрана и спасатели: 101
🚔 Полиция: 102
🚑 Скорая помощь: 103
🚨 Экстренные службы: 112
"""
    await message.answer(phones)


@dp.message(Command("contacts"))
async def send_contacts(message: Message):
    """Команда /send_contacts, которая показывает номера служб"""
    phones = """
🧑‍🦼 Горячая линия Ресурсного центра для людей с инвалидностью: +7 (495) 870-44-44
Ⓜ️ Центр мобильности метро	+7 (800) 250-73-41, +7 (495) 622-73-41
🚕 Социальное такси: +7 (499) 999-02-37
🗣️ Московская служба психологической помощи населению: +7 (495) 575-87-70 
"""
    await message.answer(phones)


@dp.message(Command("search"))
async def start_search(message: Message, state: FSMContext):
    """Команда /search, которая начинает процесс поиска"""
    await message.answer("Я помогу найти места поблизости, доступные на инвалидной коляске. Введите название района Москвы или адрес места, рядом с которым нужно искать:")
    await state.set_state(BotStates.waiting_for_district)


@dp.message(BotStates.waiting_for_district)
async def process_district(message: Message, state: FSMContext):
    """Обработка введённого района"""
    district = message.text
    coordinates = await get_coordinates(district)
    if not coordinates:
        await message.answer("Я не смог найти координаты такого района или места. Пожалуйста, введите название по-другому.")
        await state.set_state(BotStates.waiting_for_district)
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
        await callback.message.answer("Сначала введите название района или адрес места.")
        return

    await callback.message.answer(f"🔍 Ищу {category} поблизости...")
    await callback.message.delete()



    lat, lon = user_coordinates[user_id]
    places = await get_accessible_places(lat, lon, category)

    if not places:
        await callback.message.answer("К сожалению, у меня нет данных о доступных местах в этой категории.")
        return

    await callback.message.answer(f"Нашёл! Вот места в категории «{category}» поблизости, доступные на инвалидной коляске:")

    for place in places:
        # Формируем URL с отметкой точки
        yandex_url = f"https://yandex.ru/maps/?ll={place['lon']},{place['lat']}&pt={place['lon']},{place['lat']},pm2blm&z=16"
        address = get_address(place["lat"], place["lon"])
        await callback.message.answer(
            f"{place['name']}\n"
            f"🏠 Адрес: {address}\n"
            f"📍 Координаты: {place['lat']}, {place['lon']}\n"
            f"🗺️ Яндекс.Карты: {yandex_url}"
        )


if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))
