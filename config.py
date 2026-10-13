import json
import os
from pathlib import Path
from dotenv import load_dotenv

# Tải cấu hình từ file .env
load_dotenv()

# Đường dẫn thư mục gốc
BASE_DIR = Path(__file__).resolve().parent
SETTINGS_FILE = BASE_DIR / "guild_settings.json"

# Biến môi trường
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
COMMAND_PREFIX = os.getenv("COMMAND_PREFIX", "!")
DEFAULT_WELCOME_CHANNEL_ID = os.getenv("WELCOME_CHANNEL_ID", "")
DEFAULT_LEAVE_CHANNEL_ID = os.getenv("LEAVE_CHANNEL_ID", "")
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID", "")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET", "")


def load_settings() -> dict:
    """Tải cấu hình riêng của từng server từ file JSON."""
    if not SETTINGS_FILE.exists():
        return {}
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_settings(data: dict) -> None:
    """Lưu cấu hình server vào file JSON."""
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def get_guild_setting(guild_id: int, key: str, default=None):
    """Lấy một cài đặt cụ thể của server."""
    settings = load_settings()
    guild_data = settings.get(str(guild_id), {})
    return guild_data.get(key, default)


def set_guild_setting(guild_id: int, key: str, value) -> None:
    """Cập nhật cài đặt cho một server."""
    settings = load_settings()
    guild_str = str(guild_id)
    if guild_str not in settings:
        settings[guild_str] = {}
    settings[guild_str][key] = value
    save_settings(settings)

