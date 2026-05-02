#!/usr/bin/env python3
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.types import BotCommand
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, ADMIN_IDS
from database import init_db
from keyboards import get_main_menu
from handlers import user, payments, admin_panel

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=MemoryStorage())

async def set_commands():
    commands = [
        BotCommand(command="start", description="🚀 Запустить бота"),
        BotCommand(command="menu", description="📱 Главное меню"),
        BotCommand(command="profile", description="👤 Мой профиль"),
        BotCommand(command="admin", description="👑 Админ-панель (только админы)"),
    ]
    await bot.set_my_commands(commands)

async def main():
    # Инициализируем базу данных
    init_db()
    
    # Устанавливаем команды бота
    await set_commands()
    
    # Регистрируем все роутеры
    dp.include_router(user.router)
    dp.include_router(payments.router)
    dp.include_router(admin_panel.router)
    
    # Запускаем бота
    await bot.delete_webhook(drop_pending_updates=True)
    print("✅ Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
