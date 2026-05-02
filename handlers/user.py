from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from datetime import datetime
import uuid

from database import get_user, create_user, update_subscription, set_trial_used, use_promocode
from remnawave_api import remnawave
from keyboards import get_main_menu, get_profile_menu, get_back_button
from config import TRIAL_DAYS, SUBSCRIPTION_DOMAIN

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message):
    args = message.text.split()
    referrer_id = int(args[1]) if len(args) > 1 and args[1].isdigit() else None
    
    user = get_user(message.from_user.id)
    
    if not user:
        user = create_user(
            telegram_id=message.from_user.id,
            username=message.from_user.username or "",
            full_name=message.from_user.full_name,
            referrer_id=referrer_id
        )
    
    await message.answer(
        f"🔒 <b>VPN Бот</b>\n\n"
        f"Привет, {message.from_user.full_name}!\n\n"
        f"Быстрый и безопасный VPN доступ.\n"
        f"✅ Без логов\n"
        f"✅ Высокая скорость\n"
        f"✅ Защита ваших данных\n\n"
        f"Используй кнопки меню для управления подпиской.",
        reply_markup=get_main_menu(),
        parse_mode="HTML"
    )


@router.message(Command("menu"))
async def cmd_menu(message: Message):
    await message.answer("Главное меню:", reply_markup=get_main_menu())


@router.message(Command("profile"))
async def cmd_profile(message: Message):
    await show_profile(message)


@router.callback_query(F.data == "profile")
async def callback_profile(callback: CallbackQuery):
    await show_profile(callback.message)
    await callback.answer()


async def show_profile(target):
    user = get_user(target.chat.id)
    
    if user.get("subscription_end") and datetime.fromisoformat(user["subscription_end"]) > datetime.now():
        days_left = (datetime.fromisoformat(user["subscription_end"]) - datetime.now()).days
        status = f"✅ Активна • {days_left} дн."
        # Формируем ссылку для подключения
        config_link = f"{SUBSCRIPTION_DOMAIN}/sub/{user['remna_uuid']}"
    else:
        status = "❌ Не активна"
        config_link = "Нет активной подписки"
    
    await target.answer(
        f"👤 <b>Мой профиль</b>\n\n"
        f"ID: {user['telegram_id']}\n"
        f"Статус: {status}\n\n"
        f"🔗 <b>Ссылка для подключения (Happ / v2rayNG / Nekobox):</b>\n"
        f"<code>{config_link}</code>\n\n"
        f"<i>Скопируйте ссылку и вставьте в приложение</i>",
        reply_markup=get_profile_menu(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "trial")
async def activate_trial(callback: CallbackQuery):
    user = get_user(callback.from_user.id)
    
    if user.get("is_trial_used"):
        await callback.message.edit_text(
            "❌ Вы уже использовали пробный период!",
            reply_markup=get_back_button(),
            parse_mode="HTML"
        )
        await callback.answer()
        return
    
    if user.get("subscription_end") and datetime.fromisoformat(user["subscription_end"]) > datetime.now():
        await callback.message.edit_text(
            "❌ У вас уже есть активная подписка!",
            reply_markup=get_back_button(),
            parse_mode="HTML"
        )
        await callback.answer()
        return
    
    # Создаем пользователя в панели Remnawave и активируем пробный период
    subscription_link = await remnawave.create_user(
        callback.from_user.id,
        callback.from_user.username or "",
        TRIAL_DAYS
    )
    
    update_subscription(callback.from_user.id, TRIAL_DAYS)
    # Сохраняем UUID из ссылки
    uuid_part = subscription_link.split("/")[-1]
    import sqlite3
    conn = sqlite3.connect("vpn_bot.db")
    conn.execute("UPDATE users SET remna_uuid = ? WHERE telegram_id = ?", (uuid_part, callback.from_user.id))
    conn.commit()
    conn.close()
    
    set_trial_used(callback.from_user.id)
    
    await callback.message.edit_text(
        f"🎁 <b>Пробный период активирован!</b>\n\n"
        f"📅 Подписка активна на {TRIAL_DAYS} дня\n\n"
        f"🔗 <b>Ссылка для подключения:</b>\n"
        f"<code>{subscription_link}</code>\n\n"
        f"<i>Скопируйте ссылку и вставьте в приложение Happ / v2rayNG / Nekobox</i>\n\n"
        f"После окончания пробного периода вы можете приобрести полную подписку через меню «Купить».",
        reply_markup=get_main_menu(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "referral")
async def show_referral(callback: CallbackQuery):
    user = get_user(callback.from_user.id)
    ref_link = f"https://t.me/YourBotNameBot?start={user['telegram_id']}"
    
    await callback.message.edit_text(
        f"👥 <b>Реферальная система</b>\n\n"
        f"Приглашайте друзей и получайте бонусы!\n\n"
        f"🔗 <b>Ваша реферальная ссылка:</b>\n"
        f"<code>{ref_link}</code>\n\n"
        f"🎁 За каждого приглашенного друга вы получаете +{7} дней подписки!\n\n"
        f"<i>Нажмите на ссылку, чтобы скопировать</i>",
        reply_markup=get_back_button(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "activate_promo")
async def activate_promo_start(callback: CallbackQuery):
    await callback.message.edit_text(
        "🎟 <b>Активация промокода</b>\n\n"
        "Введите промокод одним сообщением:",
        reply_markup=get_back_button(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(F.text & ~F.text.startswith("/"))
async def handle_promo_input(message: Message):
    user = get_user(message.from_user.id)
    if not user:
        return
    
    bonus_days = use_promocode(message.text.strip().upper(), message.from_user.id)
    if bonus_days:
        await message.answer(
            f"✅ Промокод активирован!\n"
            f"🎁 Вам начислено {bonus_days} дней подписки!",
            reply_markup=get_main_menu()
        )
    else:
        await message.answer(
            "❌ Недействительный или просроченный промокод.",
            reply_markup=get_main_menu()
        )


@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "🔒 <b>Главное меню</b>\n\nВыберите действие:",
        reply_markup=get_main_menu(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "help")
async def show_help(callback: CallbackQuery):
    await callback.message.edit_text(
        "❓ <b>Помощь</b>\n\n"
        "<b>Как подключиться?</b>\n"
        "1. Скачайте приложение Happ (рекомендуется) или v2rayNG\n"
        "2. Скопируйте ссылку из профиля\n"
        "3. Вставьте ссылку в приложение (Импорт подписки)\n"
        "4. Нажмите подключение\n\n"
        "<b>Проблемы?</b>\n"
        "• Убедитесь, что подписка активна\n"
        "• Попробуйте перезагрузить подписку в приложении\n"
        "• Свяжитесь с поддержкой: @YourSupport",
        reply_markup=get_back_button(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Доступ запрещен")
        return
    from keyboards import get_admin_menu
    await message.answer(
        "👑 <b>Админ-панель</b>\n\nВыберите действие:",
        reply_markup=get_admin_menu(),
        parse_mode="HTML"
    )
