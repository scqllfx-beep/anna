import asyncio
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# === НАСТРОЙКИ ===
BOT_TOKEN = "8391674607:AAGEUbcz4Qt0oEXf4T3iBM2wPXUir8r_Ojc"
SHEET_ID = "1FZdCS05ABW2PdHcgalWa8SiGezvECVIrQvu4bj7CpGA"

# Услуги и цены
services = {
    "Просто покрытие": "1400₽",
    "Наращивание (до 6)": "1500₽",
    "Коррекция": "1500₽",
}

# Свободные окошки
free_slots = {
    "27.12": ["09:00", "11:00"],
    "28.12": ["09:00", "11:00", "15:00"],
    "30.12": ["09:00", "15:00"],
    "31.12": ["09:00", "11:00", "13:00", "15:00"],
}

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# === GOOGLE SHEETS ===
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]
import os
import json

json_creds = os.getenv("GOOGLE_CREDS")
creds_dict = json.loads(json_creds)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(SHEET_ID).sheet1

# Простое состояние в памяти
user_state = {}  # user_id -> dict


def reset_state(user_id: int):
    user_state[user_id] = {"service": None, "date": None, "time": None}


# === ХЕНДЛЕРЫ ===

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    reset_state(message.from_user.id)

    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📅 Записаться")],
            [KeyboardButton(text="💅 Услуги"), KeyboardButton(text="📸 Работы")],
            [KeyboardButton(text="📞 Контакты")],
        ],
        resize_keyboard=True,
    )

    text = (
        "💅 *Запись на маникюр*\n\n"
        "👩 Мастер Настя\n"
        "📍 Томск\n\n"
        "Выберите действие:"
    )

    await message.answer(text, reply_markup=kb, parse_mode="Markdown")


@dp.message(F.text == "💅 Услуги")
async def show_services(message: types.Message):
    lines = [f"• {name} — {price}" for name, price in services.items()]
    text = "💅 *Прайс:*\n\n" + "\n".join(lines)
    await message.answer(text, parse_mode="Markdown")


@dp.message(F.text == "📸 Работы")
async def show_works(message: types.Message):
    await message.answer("📸 Примеры работ: скоро добавлю 😉")


@dp.message(F.text == "📞 Контакты")
async def show_contacts(message: types.Message):
    await message.answer("📞 Пиши сюда в бот, я всё вижу и отвечу 🙂")


@dp.message(F.text == "📅 Записаться")
async def booking_start(message: types.Message):
    reset_state(message.from_user.id)

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"{name} — {price}", callback_data=f"service|{name}")]
            for name, price in services.items()
        ]
    )
    await message.answer("💅 Выбери услугу:", reply_markup=kb)


@dp.callback_query(F.data.startswith("service|"))
async def choose_service(callback: types.CallbackQuery):
    service_name = callback.data.split("|", 1)[1]
    user_id = callback.from_user.id
    user_state.setdefault(user_id, {})
    user_state[user_id]["service"] = service_name

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=date, callback_data=f"date|{date}")]
            for date in free_slots.keys()
        ]
    )

    await callback.message.edit_text(
        f"✅ Услуга: *{service_name}*\n\n📅 Теперь выбери дату:",
        reply_markup=kb,
        parse_mode="Markdown",
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("date|"))
async def choose_date(callback: types.CallbackQuery):
    date = callback.data.split("|", 1)[1]
    user_id = callback.from_user.id
    user_state.setdefault(user_id, {})
    user_state[user_id]["date"] = date

    times = free_slots.get(date, [])
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t, callback_data=f"time|{t}")]
            for t in times
        ]
    )

    await callback.message.edit_text(
        f"✅ Дата: *{date}*\n\n⏰ Выбери время:",
        reply_markup=kb,
        parse_mode="Markdown",
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("time|"))
async def choose_time(callback: types.CallbackQuery):
    time = callback.data.split("|", 1)[1]
    user_id = callback.from_user.id
    st = user_state.get(user_id, {})
    st["time"] = time

    service = st.get("service")
    date = st.get("date")

    text = (
        "Проверь данные:\n\n"
        f"💅 Услуга: *{service}*\n"
        f"📅 Дата: *{date}*\n"
        f"⏰ Время: *{time}*\n\n"
        "Если всё верно, нажми «Подтвердить заявку»."
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить заявку", callback_data="confirm")],
            [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel")],
        ]
    )

    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()


@dp.callback_query(F.data == "cancel")
async def cancel_booking(callback: types.CallbackQuery):
    reset_state(callback.from_user.id)
    await callback.message.edit_text(
        "❌ Заявка отменена. Если нужно — начни заново: кнопка «📅 Записаться»."
    )
    await callback.answer()


@dp.callback_query(F.data == "confirm")
async def confirm_booking(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    st = user_state.get(user_id, {})

    service = st.get("service")
    date = st.get("date")
    time = st.get("time")

    user = callback.from_user
    name = user.full_name
    username = f"@{user.username}" if user.username else "-"

    next_id = len(sheet.get_all_values())
    row = [next_id, name, username, "", service, date, time, "Новая"]
    sheet.append_row(row)

    await callback.message.edit_text(
        "✅ Заявка отправлена!\n\n"
        "Я проверю свободно ли это время и лично подтвержу тебе запись в Telegram.",
        parse_mode="Markdown",
    )
    await callback.answer()


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
