import asyncio

import pytz
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from supabase import create_client, Client
from datetime import datetime, timedelta

from parser import get_prices
from config import TOKEN, SUPABASE_URL, SUPABASE_KEY


bot = Bot(token=TOKEN)
dp = Dispatcher()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


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
    # Fetch the latest prices (your fetch_prices function needs to be defined elsewhere)
    prices = get_prices()

    # Get the current time in Kyiv time zone
    kyiv_tz = pytz.timezone("Europe/Kiev")
    current_time = datetime.now(kyiv_tz)

    # Format the time to ISO 8601 format
    formatted_time = current_time.strftime("%Y-%m-%dT%H:%M:%S")

    # Fetch the last inserted prices from the database
    response = supabase.table("prices").select("*").order("timestamp", desc=True).limit(1).execute()
    previous_price = response.data[0] if response.data else None

    # If there are previous prices, check if there's any change in buy/sell prices
    if previous_price:
        previous_buy_price = previous_price["buy_price"]
        previous_sell_price = previous_price["sell_price"]

        # Compare with the current prices and notify if there's a change
        if prices["buy_price"] != previous_buy_price or prices["sell_price"] != previous_sell_price:
            await notify_users(prices, previous_buy_price, previous_sell_price)

    # Insert the new prices with the timestamp into the database
    supabase.table("prices").insert({**prices, "timestamp": formatted_time}).execute()

    # Calculate the last 24 hours in Kyiv time
    last_24h = current_time - timedelta(hours=24)
    response = supabase.table("prices").select("*").gte("timestamp", last_24h.isoformat()).execute()
    historical_prices = response.data

    # Find the max and min buy and sell prices in the last 24 hours
    max_buy = max(p["buy_price"] for p in historical_prices)
    min_buy = min(p["buy_price"] for p in historical_prices)
    max_sell = max(p["sell_price"] for p in historical_prices)
    min_sell = min(p["sell_price"] for p in historical_prices)

    # Notify users if the current price is outside the historical range
    if prices["buy_price"] > max_buy or prices["buy_price"] < min_buy or \
            prices["sell_price"] > max_sell or prices["sell_price"] < min_sell:
        await notify_users(prices)


async def notify_users(prices, previous_buy_price, previous_sell_price):
    # Get all users from the database
    response = supabase.table("users").select("user_id").execute()
    user_ids = [user["user_id"] for user in response.data]

    for user_id in user_ids:
        # Notify users if the buy or sell price has changed
        message = f"<b>Нові ціни:</b>\nКупівля: <b>{prices['buy_price']}</b> грн\nПродаж: <b>{prices['sell_price']}</b> грн\n"

        if prices["buy_price"] != previous_buy_price:
            change_buy = prices["buy_price"] - previous_buy_price
            message += f"\nЗміна ціни купівлі: <b>{previous_buy_price}</b> → <b>{prices['buy_price']}</b> грн " \
                       f"({change_buy:+.2f})"

        if prices["sell_price"] != previous_sell_price:
            change_sell = prices["sell_price"] - previous_sell_price
            message += f"\nЗміна ціни продажу: <b>{previous_sell_price}</b> → <b>{prices['sell_price']}</b> грн " \
                       f"({change_sell:+.2f})"

        await bot.send_message(user_id, message, parse_mode='HTML')


async def scheduler():
    while True:
        await check_prices()
        await asyncio.sleep(900)  # 15 хвилин


async def main():
    asyncio.create_task(scheduler())
    await dp.start_polling(bot)


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
