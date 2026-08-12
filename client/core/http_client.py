# client/core/http_client.py
import requests
from typing import Optional, Dict, Any


class HttpClient:
    def __init__(self, base_url: str, token: Optional[str] = None):
        self.base_url = base_url
        self.token = token
        self.session = requests.Session()

    def _get_headers(self) -> Dict[str, str]:
        """Получить заголовки для запроса"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        if self.token:
            # Убедитесь, что формат правильный: "Bearer <token>"
            headers["Authorization"] = f"Bearer {self.token}"
            print(f"Токен установлен: {self.token[:20]}...")  # Логируем первые 20 символов
        else:
            print("Токен не установлен!")
        return headers

    def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """GET запрос"""
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()
        print(f"GET {url}")
        print(f"Headers: {headers}")

        response = self.session.get(url, headers=headers, params=params)
        print(f"Status: {response.status_code}")

        if response.status_code == 401:
            print("Ошибка 401 - неверный токен или истек срок действия")
            print(f"Response: {response.text}")

        response.raise_for_status()
        return response.json()