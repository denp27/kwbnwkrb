from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import PRICES

def get_main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Купить подписку", callback_data="buy")],
        [InlineKeyboardButton(text="👤 Мой профиль", callback_data="profile")],
        [InlineKeyboardButton(text="🎁 Пробный период", callback_data="trial")],
        [InlineKeyboardButton(text="👥 Реферальная система", callback_data="referral")],
        [InlineKeyboardButton(text="❓ Помощь", callback_data="help")]
    ])

def get_tariffs_menu() -> InlineKeyboardMarkup:
    buttons = []
    for months, price in PRICES.items():
        buttons.append([InlineKeyboardButton(
            text=f"🗓 {months} месяц(ев) — {price} ₽",
            callback_data=f"tariff_{months}"
        )])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_payment_methods_menu(months: int, amount: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🪙 CryptoBot (USDT)", callback_data=f"crypto_{months}_{amount}")],
        [InlineKeyboardButton(text="💳 Platega.io (Карта/СБП)", callback_data=f"platega_{months}_{amount}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="buy")]
    ])

def get_profile_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Продлить подписку", callback_data="buy")],
        [InlineKeyboardButton(text="🔗 Моя реферальная ссылка", callback_data="my_ref_link")],
        [InlineKeyboardButton(text="🎟 Активировать промокод", callback_data="activate_promo")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
    ])

def get_admin_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users")],
        [InlineKeyboardButton(text="➕ Добавить дни", callback_data="admin_add_days")],
        [InlineKeyboardButton(text="🚫 Управление банами", callback_data="admin_ban")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="🎫 Создать промокод", callback_data="admin_create_promo")],
        [InlineKeyboardButton(text="📜 Логи админов", callback_data="admin_logs")],
        [InlineKeyboardButton(text="🔙 Выход", callback_data="back_to_menu")]
    ])

def get_back_button() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
    ])
