from streamlit_cookies_controller.cookie_controller import CookieController
from datetime import datetime

class CookieHandler():
    def __init__(self):
        self.cookies = CookieController()

    def set_cookie(self, key: str, token: str, expiry: datetime):
        self.cookies.set(key, token, expires=expiry)

    def get_cookie(self, key: str) -> str | None:
        return self.cookies.get(name=key)

    def clear_cookie(self, key: str):
        self.cookies.remove(key)