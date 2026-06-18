import asyncio
import os
import json
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.types import (Message, InlineKeyboardMarkup,
                           InlineKeyboardButton, LabeledPrice,
                           PreCheckoutQuery, WebAppInfo)
from aiogram.filters import CommandStart, Command

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("arcana-bot")

BOT_TOKEN  = os.environ.get("BOT_TOKEN")
WEBAPP_URL = os.environ.get("WEBAPP_URL")
PORT       = int(os.environ.get("PORT", "8080"))

DONATE_ADDRESS = "TWTVnB4K6joTih2LFozxhvfBniW4BfpCfH"
PROMO_CODE     = "Blog X Studio"
PROMO_DELAY    = 20  # секунд

PROMO_USERS_FILE = "promo_users.json"

def load_promo_users():
    try:
        with open(PROMO_USERS_FILE, "r") as f:
            return set(json.load(f))
    except Exception:
        return set()

def save_promo_users(users):
    try:
        with open(PROMO_USERS_FILE, "w") as f:
            json.dump(list(users), f)
    except Exception:
        log.exception("failed to save promo users")

promo_users = load_promo_users()

PRICES = {
    "pro":     [LabeledPrice(label="Arcana Pro",     amount=299)],
    "premium": [LabeledPrice(label="Arcana Premium", amount=489)],
}

TITLES = {
    "pro":     "Arcana Pro — полный доступ навсегда",
    "premium": "Arcana Premium — всё включено навсегда",
}
DESCRIPTIONS = {
    "pro":     "Три карты, Кельтский крест, 78 арканов, нумерология, матрица судьбы",
    "premium": "Всё из Pro + персональный гороскоп + совместимость по числам",
}

bot = Bot(token=BOT_TOKEN)
dp  = Dispatcher()

async def send_donate_message(chat_id: int):
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✦ Поддержать Arcana", callback_data="show_donate")
    ]])
    await bot.send_message(
        chat_id,
        "🌙 *Поддержать Arcana*\n\n"
        "Если приложение резонирует с вами — вы можете поддержать его развитие.",
        parse_mode="Markdown",
        reply_markup=kb
    )

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
    await send_donate_message(message.chat.id)

@dp.message(Command("donate"))
async def cmd_donate(message: Message):
    await message.answer(
        f"🌙 *Поддержать Arcana*\n\n"
        f"Если приложение резонирует с вами — вы можете поддержать его развитие.\n\n"
        f"*TRC20 · USDT / TRX*\n`{DONATE_ADDRESS}`\n\n"
        f"Спасибо — каждый вклад помогает делать Arcana глубже и точнее ✦\n\n"
        f"После перевода пришлите сюда скриншот транзакции, и мы вышлем вам промокод на Arcana Premium.",
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "show_donate")
async def callback_show_donate(callback):
    await callback.message.answer(
        f"🌙 *Поддержать Arcana*\n\n"
        f"Если приложение резонирует с вами — вы можете поддержать его развитие.\n\n"
        f"*TRC20 · USDT / TRX*\n`{DONATE_ADDRESS}`\n\n"
        f"Спасибо — каждый вклад помогает делать Arcana глубже и точнее ✦\n\n"
        f"После перевода пришлите сюда скриншот транзакции, и мы вышлем вам промокод на Arcana Premium.",
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.message(F.photo)
async def handle_donate_screenshot(message: Message):
    user_id = message.from_user.id
    if user_id in promo_users:
        await message.answer("Вы уже получили промокод ранее 🌙")
        return

    await message.answer(f"Спасибо! Проверяем скрин, подождите ~{PROMO_DELAY} секунд…")

    async def send_promo_later():
        await asyncio.sleep(PROMO_DELAY)
        promo_users.add(user_id)
        save_promo_users(promo_users)
        await bot.send_message(
            user_id,
            f"🌟 *Спасибо за поддержку!*\n\n"
            f"Ваш промокод на Arcana Premium:\n`{PROMO_CODE}`\n\n"
            f"Введите его в приложении на вкладке «Тариф», в поле «Промокод».\n\n"
            f"Промокод создан при поддержке друзей из [Blog X — MediaOS](https://blogxstudio.com/)",
            parse_mode="Markdown"
        )

    asyncio.create_task(send_promo_later())

# Оставляем старый обработчик sendData на случай, если где-то ещё используется
@dp.message(F.web_app_data)
async def handle_webapp_data(message: Message):
    data = message.web_app_data.data
    if not data.startswith("buy:"):
        return
    plan = data.split(":")[1]
    if plan not in PRICES:
        return
    await bot.send_invoice(
        chat_id=message.chat.id,
        title=TITLES[plan],
        description=DESCRIPTIONS[plan],
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

# ──────────────────────────────────────────────
#  HTTP-эндпоинт для мини-аппы: создание ссылки на инвойс
# ──────────────────────────────────────────────
async def create_invoice_handler(request: web.Request):
    # CORS, чтобы мини-апа на github.io могла стучаться сюда
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
    }
    if request.method == "OPTIONS":
        return web.Response(status=200, headers=headers)

    try:
        body = await request.json()
        plan = body.get("plan")
        user_id = body.get("user_id")

        if plan not in PRICES:
            return web.json_response({"error": "invalid plan"}, status=400, headers=headers)
        if not user_id:
            return web.json_response({"error": "missing user_id"}, status=400, headers=headers)

        link = await bot.create_invoice_link(
            title=TITLES[plan],
            description=DESCRIPTIONS[plan],
            payload=f"arcana_{plan}_{user_id}",
            currency="XTR",
            prices=PRICES[plan],
            provider_token="",
        )
        return web.json_response({"invoice_url": link}, headers=headers)
    except Exception as e:
        log.exception("create_invoice failed")
        return web.json_response({"error": str(e)}, status=500, headers=headers)

async def health_handler(request: web.Request):
    return web.json_response({"status": "ok"})

async def start_web_server():
    app = web.Application()
    app.router.add_post("/create-invoice", create_invoice_handler)
    app.router.add_options("/create-invoice", create_invoice_handler)
    app.router.add_get("/", health_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    log.info(f"HTTP server started on port {PORT}")

async def main():
    await start_web_server()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
