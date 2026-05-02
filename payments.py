import aiohttp
import asyncio
import secrets
from datetime import datetime
from aiogram import Bot, Router, F
from aiogram.types import Message, CallbackQuery, PreCheckoutQuery, LabeledPrice
from config import (
    CRYPTOBOT_TOKEN, PLATEGA_API_URL, PLATEGA_API_KEY, PLATEGA_SHOP_ID,
    PRICES, BOT_TOKEN
)
from database import add_payment, mark_payment_paid
from remnawave_api import remnawave

router = Router()
bot = Bot(token=BOT_TOKEN)


# ============ CRYPTOBOT (КРИПТОВАЛЮТА) ============
# Документация Crypto Pay API: https://help.crypt.bot/crypto-pay-api
# Используем aiosend для асинхронной работы [citation:2]

async def create_cryptobot_invoice(telegram_id: int, amount: float, months: int) -> dict:
    """Создает инвойс в CryptoBot"""
    async with aiohttp.ClientSession() as session:
        headers = {
            "Crypto-Pay-API-Token": CRYPTOBOT_TOKEN,
            "Content-Type": "application/json"
        }
        payload = {
            "asset": "USDT",
            "amount": str(amount),
            "description": f"VPN Подписка на {months} месяц(ев)",
            "paid_btn_name": "callback",
            "paid_btn_url": "https://t.me/your_bot"
        }
        
        async with session.post(
            "https://pay.crypt.bot/api/createInvoice",
            json=payload,
            headers=headers
        ) as resp:
            data = await resp.json()
            if data.get("ok"):
                return data["result"]
            return None


# ============ PLATEGA.IO (БАНКОВСКИЕ КАРТЫ / СБП) ============
# Архитектура для интеграции с Platega.io
# ВАЖНО: Эндпоинты и формат данных уточните по документации Platega.io

async def create_platega_invoice(telegram_id: int, amount: int, months: int) -> dict:
    """
    Создает платеж через Platega.io
    Формат запроса - примерный, заполните по документации Platega.io
    """
    async with aiohttp.ClientSession() as session:
        headers = {
            "Authorization": f"Bearer {PLATEGA_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Генерируем уникальный ID заказа
        order_id = f"VPN_{telegram_id}_{datetime.now().timestamp()}"
        
        payload = {
            "shop_id": PLATEGA_SHOP_ID,
            "amount": amount,
            "currency": "RUB",
            "order_id": order_id,
            "description": f"VPN подписка на {months} месяц(ев)",
            "success_url": f"https://t.me/your_bot",
            "fail_url": f"https://t.me/your_bot",
            "webhook_url": "https://your-server.com/webhook/platega"  # Для получения уведомлений
        }
        
        async with session.post(
            f"{PLATEGA_API_URL}/payment/create",
            json=payload,
            headers=headers
        ) as resp:
            data = await resp.json()
            # Формат ответа зависит от документации Platega.io
            # Обычно возвращается payment_url для редиректа
            return {
                "payment_url": data.get("payment_url"),
                "order_id": order_id
            }


# ============ ПРОВЕРКА СТАТУСОВ ПЛАТЕЖЕЙ ============

async def check_cryptobot_payment(invoice_id: str) -> bool:
    """Проверяет статус оплаты в CryptoBot"""
    async with aiohttp.ClientSession() as session:
        headers = {"Crypto-Pay-API-Token": CRYPTOBOT_TOKEN}
        async with session.post(
            "https://pay.crypt.bot/api/getInvoices",
            json={"invoice_ids": [invoice_id]},
            headers=headers
        ) as resp:
            data = await resp.json()
            if data.get("ok") and data["result"]["items"]:
                invoice = data["result"]["items"][0]
                return invoice.get("status") == "paid"
    return False


async def check_platega_payment(order_id: str) -> bool:
    """
    Проверяет статус оплаты через Platega.io
    Формат запроса - примерный, уточните по документации Platega.io
    """
    async with aiohttp.ClientSession() as session:
        headers = {"Authorization": f"Bearer {PLATEGA_API_KEY}"}
        async with session.get(
            f"{PLATEGA_API_URL}/payment/status/{order_id}",
            headers=headers
        ) as resp:
            data = await resp.json()
            return data.get("status") == "paid"


# ============ ОБРАБОТЧИКИ В БОТЕ ============

@router.callback_query(F.data == "buy")
async def show_tariffs(callback: CallbackQuery):
    """Показывает меню выбора тарифов"""
    from keyboards import get_tariffs_menu
    await callback.message.edit_text(
        "🛒 <b>Выберите тариф подписки:</b>\n\n"
        "После оплаты вы получите персональную ссылку для подключения к VPN.",
        reply_markup=get_tariffs_menu(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("tariff_"))
async def select_tariff(callback: CallbackQuery):
    """Выбор тарифа -> показываем способы оплаты"""
    months = int(callback.data.split("_")[1])
    amount = PRICES.get(months)
    
    from keyboards import get_payment_methods_menu
    
    await callback.message.edit_text(
        f"💰 <b>Оплата: {amount} ₽</b>\n\n"
        f"🗓 Подписка: {months} месяц(ев)\n"
        f"💳 Сумма: {amount} ₽\n\n"
        f"Выберите способ оплаты:",
        reply_markup=get_payment_methods_menu(months, amount),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("crypto_"))
async def pay_with_cryptobot(callback: CallbackQuery):
    """Оплата через CryptoBot"""
    _, months, amount = callback.data.split("_")
    months = int(months)
    amount = float(amount)
    
    # Создаем инвойс в CryptoBot
    invoice = await create_cryptobot_invoice(callback.from_user.id, amount, months)
    
    if invoice:
        # Сохраняем платеж в БД
        add_payment(
            telegram_id=callback.from_user.id,
            amount=int(amount),
            months=months,
            payment_system="cryptobot",
            external_id=invoice["invoice_id"]
        )
        
        # Отправляем ссылку на оплату
        await callback.message.edit_text(
            f"💸 <b>Счет для оплаты создан!</b>\n\n"
            f"💰 Сумма: {amount} USDT\n"
            f"🗓 Подписка: {months} месяц(ев)\n\n"
            f"👉 [Оплатить в CryptoBot]({invoice['pay_url']})\n\n"
            f"<i>После оплаты подписка активируется автоматически.</i>",
            parse_mode="HTML"
        )
        
        # Запускаем проверку оплаты (polling)
        asyncio.create_task(poll_cryptobot_payment(callback.from_user.id, invoice["invoice_id"]))
    else:
        await callback.message.edit_text(
            "❌ Ошибка при создании счета. Попробуйте позже.",
            parse_mode="HTML"
        )
    await callback.answer()


@router.callback_query(F.data.startswith("platega_"))
async def pay_with_platega(callback: CallbackQuery):
    """Оплата через Platega.io"""
    _, months, amount = callback.data.split("_")
    months = int(months)
    amount = int(amount)
    
    # Создаем платеж в Platega.io
    invoice = await create_platega_invoice(callback.from_user.id, amount, months)
    
    if invoice and invoice.get("payment_url"):
        # Сохраняем платеж в БД
        add_payment(
            telegram_id=callback.from_user.id,
            amount=amount,
            months=months,
            payment_system="platega",
            external_id=invoice["order_id"]
        )
        
        await callback.message.edit_text(
            f"💳 <b>Оплата через Platega.io</b>\n\n"
            f"💰 Сумма: {amount} ₽\n"
            f"🗓 Подписка: {months} месяц(ев)\n\n"
            f"👉 [Перейти к оплате]({invoice['payment_url']})\n\n"
            f"<i>После оплаты подписка активируется автоматически (до 1 минуты).</i>",
            parse_mode="HTML",
            disable_web_page_preview=True
        )
        
        # Запускаем проверку оплаты
        asyncio.create_task(poll_platega_payment(callback.from_user.id, invoice["order_id"], months))
    else:
        await callback.message.edit_text(
            "❌ Ошибка при создании платежа. Попробуйте позже.",
            parse_mode="HTML"
        )
    await callback.answer()


async def poll_cryptobot_payment(telegram_id: int, invoice_id: str, check_interval: int = 10):
    """Проверяет статус оплаты CryptoBot каждые N секунд"""
    for _ in range(30):  # Проверяем в течение 5 минут (30 * 10 сек)
        await asyncio.sleep(check_interval)
        if await check_cryptobot_payment(invoice_id):
            # Оплата подтверждена
            if mark_payment_paid(invoice_id):
                await bot.send_message(
                    telegram_id,
                    "✅ <b>Оплата подтверждена!</b>\n\n"
                    "Ваша подписка активирована. Используйте /profile для получения ссылки на подключение.",
                    parse_mode="HTML"
                )
            return
    # Таймаут - оплата не получена
    await bot.send_message(
        telegram_id,
        "⏰ Время ожидания оплаты истекло. Если вы оплатили, обратитесь в поддержку.",
        parse_mode="HTML"
    )


async def poll_platega_payment(telegram_id: int, order_id: str, months: int, check_interval: int = 10):
    """Проверяет статус оплаты Platega.io каждые N секунд"""
    for _ in range(30):
        await asyncio.sleep(check_interval)
        if await check_platega_payment(order_id):
            if mark_payment_paid(order_id):
                await bot.send_message(
                    telegram_id,
                    "✅ <b>Оплата подтверждена!</b>\n\n"
                    "Ваша подписка активирована. Используйте /profile для получения ссылки на подключение.",
                    parse_mode="HTML"
                )
            return
    # Таймаут
    await bot.send_message(
        telegram_id,
        "⏰ Время ожидания оплаты истекло. Если вы оплатили, обратитесь в поддержку.",
        parse_mode="HTML"
    )
