import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import (Message, InlineKeyboardMarkup,
                           InlineKeyboardButton, LabeledPrice,
                           PreCheckoutQuery, WebAppInfo)
from aiogram.filters import CommandStart

BOT_TOKEN  = "8646621947:AAFigPZm257TqMlZ3B7ecpyFK9IJJPF7EKo"
WEBAPP_URL = "https://5s527njtj2-ship-it.github.io/arcana110"

PRICES = {
    "pro":     [LabeledPrice(label="Arcana Pro",     amount=299)],
    "premium": [LabeledPrice(label="Arcana Premium", amount=489)],
}

bot = Bot(token=BOT_TOKEN)
dp  = Dispatcher()

@dp.message(CommandStart())
async def cmd_start(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="✦ Открыть Arcana",
            web_app=WebAppInfo(url=WEBAPP_URL)
        )
    ]])
    await message.answer(
        "🌙 *Добро пожаловать в Arcana*\n\nТаро · Нумерология · Гороскоп",
        parse_mode="Markdown",
        reply_markup=kb
    )

@dp.message(F.web_app_data)
async def handle_webapp_data(message: Message):
    data = message.web_app_data.data
    if not data.startswith("buy:"):
        return
    plan = data.split(":")[1]
    if plan not in PRICES:
        return
    titles = {
        "pro":     "Arcana Pro — полный доступ навсегда",
        "premium": "Arcana Premium — всё включено навсегда",
    }
    descriptions = {
        "pro":     "Три карты, Кельтский крест, 78 арканов, нумерология, матрица судьбы",
        "premium": "Всё из Pro + персональный гороскоп + совместимость по числам",
    }
    await bot.send_invoice(
        chat_id=message.chat.id,
        title=titles[plan],
        description=descriptions[plan],
        payload=f"arcana_{plan}_{message.from_user.id}",
        currency="XTR",
        prices=PRICES[plan],
        provider_token="",
    )

@dp.pre_checkout_query()
async def pre_checkout(pcq: PreCheckoutQuery):
    await pcq.answer(ok=True)

@dp.message(F.successful_payment)
async def successful_payment(message: Message):
    payload = message.successful_payment.invoice_payload
    parts   = payload.split("_")
    plan    = parts[1]
    plan_names = {
        "pro":     "Arcana Pro ✦",
        "premium": "Arcana Premium ✦"
    }
    url = f"{WEBAPP_URL}?paid=1&plan={plan}"
    kb  = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="✦ Открыть Arcana",
            web_app=WebAppInfo(url=url)
        )
    ]])
    await message.answer(
        f"🌟 *{plan_names.get(plan, 'Arcana')} активирован!*\n\n"
        f"Спасибо — теперь у вас полный доступ навсегда.\n"
        f"Нажмите кнопку ниже, чтобы открыть приложение.",
        parse_mode="Markdown",
        reply_markup=kb
    )

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
