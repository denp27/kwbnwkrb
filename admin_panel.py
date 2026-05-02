from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import ADMIN_IDS
from database import (
    get_all_users, get_active_users_count, get_total_users_count,
    get_total_revenue, ban_user, unban_user, add_admin_log,
    add_promocode, update_subscription, get_user
)
from keyboards import get_admin_menu, get_back_button

router = Router()


class AdminStates(StatesGroup):
    waiting_for_broadcast = State()
    waiting_for_user_id = State()
    waiting_for_days = State()
    waiting_for_promo_code = State()
    waiting_for_promo_days = State()
    waiting_for_promo_limit = State()
    waiting_for_promo_expires = State()


def is_admin(telegram_id: int) -> bool:
    return telegram_id in ADMIN_IDS


@router.callback_query(F.data == "admin_panel")
async def show_admin_panel(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен", show_alert=True)
        return
    await callback.message.edit_text(
        "👑 <b>Админ-панель</b>\n\nВыберите действие:",
        reply_markup=get_admin_menu(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    
    total_users = get_total_users_count()
    active_users = get_active_users_count()
    revenue = get_total_revenue()
    
    await callback.message.edit_text(
        f"📊 <b>Статистика</b>\n\n"
        f"👥 Всего пользователей: {total_users}\n"
        f"✅ Активных подписок: {active_users}\n"
        f"💰 Общая выручка: {revenue} ₽\n"
        f"📈 Конверсия: {round(active_users/total_users*100, 1) if total_users else 0}%",
        reply_markup=get_back_button(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "admin_users")
async def list_users(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    
    users = get_all_users()
    text = "👥 <b>Список пользователей:</b>\n\n"
    for user in users[:10]:
        text += f"• {user['full_name']} (@{user['username']}) ID: {user['telegram_id']}\n"
    if len(users) > 10:
        text += f"\n<i>и еще {len(users)-10} пользователей...</i>"
    
    await callback.message.edit_text(text, reply_markup=get_back_button(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_add_days")
async def add_days_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await callback.message.edit_text(
        "➕ <b>Добавление дней подписки</b>\n\n"
        "Введите Telegram ID пользователя:",
        reply_markup=get_back_button(),
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_user_id)
    await callback.answer()


@router.message(AdminStates.waiting_for_user_id)
async def get_user_id(message: Message, state: FSMContext):
    try:
        user_id = int(message.text.strip())
        user = get_user(user_id)
        if not user:
            await message.answer("❌ Пользователь не найден. Попробуйте снова:")
            return
        await state.update_data(target_user=user_id)
        await message.answer(f"👤 Пользователь: {user['full_name']}\n\nВведите количество дней для добавления:")
        await state.set_state(AdminStates.waiting_for_days)
    except ValueError:
        await message.answer("❌ ID должен быть числом. Попробуйте снова:")


@router.message(AdminStates.waiting_for_days)
async def add_days_confirm(message: Message, state: FSMContext):
    try:
        days = int(message.text.strip())
        data = await state.get_data()
        user_id = data["target_user"]
        
        update_subscription(user_id, days)
        add_admin_log(message.from_user.id, "add_days", user_id, f"added {days} days")
        
        await message.answer(f"✅ Добавлено {days} дней пользователю!")
        await state.clear()
    except ValueError:
        await message.answer("❌ Введите число дней:")


@router.callback_query(F.data == "admin_create_promo")
async def create_promo_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await callback.message.edit_text(
        "🎫 <b>Создание промокода</b>\n\n"
        "Введите код промокода (латиница, цифры):",
        reply_markup=get_back_button(),
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_promo_code)
    await callback.answer()


@router.message(AdminStates.waiting_for_promo_code)
async def get_promo_code(message: Message, state: FSMContext):
    code = message.text.strip().upper()
    await state.update_data(promo_code=code)
    await message.answer(f"Код: {code}\n\nВведите количество бонусных дней:")
    await state.set_state(AdminStates.waiting_for_promo_days)


@router.message(AdminStates.waiting_for_promo_days)
async def get_promo_days(message: Message, state: FSMContext):
    try:
        days = int(message.text.strip())
        await state.update_data(promo_days=days)
        await message.answer(f"Бонус: {days} дней\n\nВведите лимит использований (0 - безлимит):")
        await state.set_state(AdminStates.waiting_for_promo_limit)
    except ValueError:
        await message.answer("❌ Введите число дней:")


@router.message(AdminStates.waiting_for_promo_limit)
async def get_promo_limit(message: Message, state: FSMContext):
    try:
        limit = int(message.text.strip())
        await state.update_data(promo_limit=limit)
        await message.answer(f"Лимит: {limit if limit>0 else 'безлимит'}\n\nВведите срок действия в днях (например, 30):")
        await state.set_state(AdminStates.waiting_for_promo_expires)
    except ValueError:
        await message.answer("❌ Введите число:")


@router.message(AdminStates.waiting_for_promo_expires)
async def create_promo_final(message: Message, state: FSMContext):
    try:
        expires_days = int(message.text.strip())
        data = await state.get_data()
        
        add_promocode(
            code=data["promo_code"],
            bonus_days=data["promo_days"],
            usage_limit=data["promo_limit"] if data["promo_limit"] > 0 else 999999,
            expires_days=expires_days,
            created_by=message.from_user.id
        )
        
        add_admin_log(message.from_user.id, "create_promo", details=f"{data['promo_code']}")
        
        await message.answer(
            f"✅ Промокод создан!\n\n"
            f"🎫 Код: {data['promo_code']}\n"
            f"📅 Бонус: {data['promo_days']} дней\n"
            f"🔢 Лимит: {data['promo_limit'] if data['promo_limit']>0 else 'безлимит'}\n"
            f"⏰ Действует: {expires_days} дней"
        )
        await state.clear()
    except ValueError:
        await message.answer("❌ Введите число дней:")
