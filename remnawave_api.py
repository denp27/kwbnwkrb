import aiohttp
import uuid
from config import PANEL_URL, PANEL_USERNAME, PANEL_PASSWORD, INBOUND_ID, SUBSCRIPTION_DOMAIN

class RemnawaveAPI:
    def __init__(self):
        self.base_url = PANEL_URL.rstrip('/')
        self.token = None
    
    async def _get_token(self) -> str:
        """Получает JWT токен для авторизации в Remnawave"""
        if self.token:
            return self.token
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/api/admin/token",
                json={"username": PANEL_USERNAME, "password": PANEL_PASSWORD}
            ) as resp:
                data = await resp.json()
                self.token = data.get("access_token")
                return self.token
    
    async def create_user(self, telegram_id: int, username: str, days: int) -> str:
        """
        Создает пользователя в панели Remnawave
        Возвращает subscription link для выдачи клиенту
        """
        token = await self._get_token()
        user_uuid = str(uuid.uuid4())
        expiry = None  # Будет управляться через подписки
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Создаем пользователя
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/api/users",
                headers=headers,
                json={
                    "username": f"user_{telegram_id}",
                    "uuid": user_uuid,
                    "inbound_id": INBOUND_ID,
                    "expire": expiry
                }
            ) as resp:
                if resp.status not in (200, 201):
                    raise Exception(f"Failed to create user: {await resp.text()}")
        
        # Формируем ссылку для подписки (формат для Sing-box / Happ / v2rayNG)
        subscription_link = f"{SUBSCRIPTION_DOMAIN}/sub/{user_uuid}"
        return subscription_link
    
    async def get_user_status(self, telegram_id: int) -> dict:
        """Получает статус пользователя из панели"""
        token = await self._get_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}/api/users",
                headers=headers
            ) as resp:
                users = await resp.json()
                for user in users:
                    if user.get("username") == f"user_{telegram_id}":
                        return {
                            "enabled": user.get("enable", True),
                            "expire": user.get("expire"),
                            "usage": user.get("usage", 0)
                        }
        return None

remnawave = RemnawaveAPI()
