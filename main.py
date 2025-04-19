import asyncio

import pytz
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from supabase import create_client, Client
from datetime import datetime, timedelta

from parser import get_usd_prices, get_eur_prices
from config import TOKEN, SUPABASE_URL, SUPABASE_KEY
from init_db import create_supabase_tables

bot = Bot(token=TOKEN)
dp = Dispatcher()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


async def ensure_tables_exist():
    """Перевіряє наявність необхідних таблиць і створює їх, якщо вони відсутні"""
    try:
        # Перевіряємо таблицю користувачів
        try:
            supabase.table("users").select("*").limit(1).execute()
            print("Таблиця 'users' існує")
        except Exception:
            print("Таблиця 'users' не існує, створюємо...")
            # Використовуємо функцію для створення таблиць
            create_supabase_tables()
            return

        # Перевіряємо таблицю цін
        try:
            supabase.table("prices").select("*").limit(1).execute()
            print("Таблиця 'prices' існує")
        except Exception:
            print("Таблиця 'prices' не існує, створюємо...")
            # Використовуємо функцію для створення таблиць
            create_supabase_tables()
    except Exception as e:
        print(f"Помилка при перевірці таблиць: {e}")
        # Продовжимо роботу навіть при помилці, можливо таблиці вже існують


@dp.message(Command("start"))
async def start_command(message: types.Message):
    response = supabase.table("users").select("*").eq("user_id", message.from_user.id).execute()
    users = response.data

    if users:  # Якщо користувач уже є в базі
        await message.answer("Ви вже підписані на сповіщення. Використовуйте /stop, щоб відписатися.")
    else:
        # Додавання нового користувача
        user_data = {"user_id": message.from_user.id, "username": message.from_user.username}
        add_response = supabase.table("users").insert(user_data).execute()

        if add_response.data:
            await message.answer(
                "Вітаю, ви успішно додані до списку для сповіщень! "
                "Бот буде надсилати вам оновлення цін кожні 15 хвилин. "
                "Використовуйте /stop, щоб відписатися."
            )
        else:
            await message.answer("Сталася помилка при додаванні. Спробуйте пізніше.")


@dp.message(Command("stop"))
async def stop_command(message: types.Message):
    response = supabase.table("users").delete().eq("user_id", message.from_user.id).execute()
    if response.data:
        await message.answer("Вас видалено зі списку для сповіщень.")
    else:
        await message.answer("Сталася помилка при видаленні.")


async def check_prices():
    # Отримуємо актуальні ціни USD
    usd_prices = get_usd_prices()

    # Отримуємо актуальні ціни EUR
    eur_prices = get_eur_prices()

    # Отримуємо поточний час у київському часовому поясі
    kyiv_tz = pytz.timezone("Europe/Kiev")
    current_time = datetime.now(kyiv_tz)

    # Форматуємо час до ISO 8601 формату
    formatted_time = current_time.strftime("%Y-%m-%dT%H:%M:%S")

    # Отримуємо останні ціни USD з бази даних
    response_usd = supabase.table("prices").select("*").eq("currency", "USD").order("timestamp", desc=True).limit(
        1).execute()
    previous_usd_price = response_usd.data[0] if response_usd.data else None

    # Отримуємо останні ціни EUR з бази даних
    response_eur = supabase.table("prices").select("*").eq("currency", "EUR").order("timestamp", desc=True).limit(
        1).execute()
    previous_eur_price = response_eur.data[0] if response_eur.data else None

    # Перевіряємо зміни для USD
    if previous_usd_price:
        previous_buy_price = previous_usd_price["buy_price"]
        previous_sell_price = previous_usd_price["sell_price"]
        previous_nbu_price = previous_usd_price.get("nbu_price")

        # Порівнюємо з поточними цінами та сповіщаємо, якщо є зміни
        if usd_prices["buy_price"] != previous_buy_price or usd_prices["sell_price"] != previous_sell_price or \
                usd_prices["nbu_price"] != previous_nbu_price:
            await notify_users(usd_prices, previous_buy_price, previous_sell_price, previous_nbu_price, "USD")

    # Перевіряємо зміни для EUR
    if previous_eur_price:
        previous_buy_price = previous_eur_price["buy_price"]
        previous_sell_price = previous_eur_price["sell_price"]
        previous_nbu_price = previous_eur_price.get("nbu_price")

        # Порівнюємо з поточними цінами та сповіщаємо, якщо є зміни
        if eur_prices["buy_price"] != previous_buy_price or eur_prices["sell_price"] != previous_sell_price or \
                eur_prices["nbu_price"] != previous_nbu_price:
            await notify_users(eur_prices, previous_buy_price, previous_sell_price, previous_nbu_price, "EUR")

    # Додаємо нові ціни USD до бази даних
    supabase.table("prices").insert({**usd_prices, "timestamp": formatted_time, "currency": "USD"}).execute()

    # Додаємо нові ціни EUR до бази даних
    supabase.table("prices").insert({**eur_prices, "timestamp": formatted_time, "currency": "EUR"}).execute()


async def notify_users(prices, previous_buy_price, previous_sell_price, previous_nbu_price=None, currency="USD"):
    # Отримуємо всіх користувачів з бази даних
    response = supabase.table("users").select("user_id").execute()
    user_ids = [user["user_id"] for user in response.data]

    # Обираємо емодзі в залежності від валюти
    currency_emoji = "💵" if currency == "USD" else "💶"

    for user_id in user_ids:
        message = (
            f"{currency_emoji} <b>Оновлення курсу {currency}</b> {currency_emoji}\n\n"
            f"🔹 <b>Купівля:</b> {prices['buy_price']} грн\n"
            f"🔹 <b>Продаж:</b> {prices['sell_price']} грн\n"
            f"🏦 <b>Курс НБУ:</b> {prices['nbu_price']} грн\n"
        )

        # Зміни
        changes = []

        if previous_buy_price and prices["buy_price"] != previous_buy_price:
            change = prices["buy_price"] - previous_buy_price
            arrow = "🔼" if change > 0 else "🔽"
            changes.append(
                f"{arrow} <b>Зміна купівлі:</b> {previous_buy_price} → {prices['buy_price']} грн ({change:+.2f})"
            )

        if previous_sell_price and prices["sell_price"] != previous_sell_price:
            change = prices["sell_price"] - previous_sell_price
            arrow = "🔼" if change > 0 else "🔽"
            changes.append(
                f"{arrow} <b>Зміна продажу:</b> {previous_sell_price} → {prices['sell_price']} грн ({change:+.2f})"
            )

        if previous_nbu_price and prices["nbu_price"] != previous_nbu_price:
            change = prices["nbu_price"] - previous_nbu_price
            arrow = "🔼" if change > 0 else "🔽"
            changes.append(
                f"{arrow} <b>Зміна НБУ:</b> {previous_nbu_price} → {prices['nbu_price']} грн ({change:+.2f})"
            )

        if changes:
            message += "\n" + "\n".join(changes)

        await bot.send_message(user_id, message, parse_mode='HTML')


async def scheduler():
    while True:
        await check_prices()
        await asyncio.sleep(900)  # 15 хвилин


async def main():
    # Переконуємося, що необхідні таблиці існують
    await ensure_tables_exist()

    # Запускаємо планувальник
    asyncio.create_task(scheduler())

    # Запускаємо бота
    await dp.start_polling(bot)


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
