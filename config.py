import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x]

PANEL_URL = os.getenv("PANEL_URL")
PANEL_USERNAME = os.getenv("PANEL_USERNAME")
PANEL_PASSWORD = os.getenv("PANEL_PASSWORD")
INBOUND_ID = int(os.getenv("INBOUND_ID", "1"))
SUBSCRIPTION_DOMAIN = os.getenv("SUBSCRIPTION_DOMAIN")

CRYPTOBOT_TOKEN = os.getenv("CRYPTOBOT_TOKEN")

PLATEGA_API_URL = os.getenv("PLATEGA_API_URL")
PLATEGA_API_KEY = os.getenv("PLATEGA_API_KEY")
PLATEGA_SHOP_ID = os.getenv("PLATEGA_SHOP_ID")

PRICES = {
    1: int(os.getenv("PRICE_1_MONTH", "499")),
    3: int(os.getenv("PRICE_3_MONTH", "1299")),
    6: int(os.getenv("PRICE_6_MONTH", "2299")),
}

TRIAL_DAYS = int(os.getenv("TRIAL_DAYS", "3"))
REFERRAL_BONUS_DAYS = int(os.getenv("REFERRAL_BONUS_DAYS", "7"))
TIMEZONE = os.getenv("TIMEZONE", "Europe/Moscow")
