import asyncio
import os
import json
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.types import (Message, InlineKeyboardMarkup,
                           InlineKeyboardButton, LabeledPrice,
                           PreCheckoutQuery, WebAppInfo)
from aiogram.filters import CommandStart
 
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("arcana-bot")
 
BOT_TOKEN  = os.environ.get("BOT_TOKEN")
WEBAPP_URL = os.environ.get("WEBAPP_URL")
PORT       = int(os.environ.get("PORT", "8080"))
 
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
 
