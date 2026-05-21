import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BOT_TOKEN: str = os.environ["BOT_TOKEN"]
OWNER_ID: int = int(os.environ["OWNER_ID"])
GEMINI_API_KEY: str = os.environ.get("GEMINI_API_KEY", "")
DB_PATH: str = os.environ.get("DB_PATH", "main.db")

BOT_OWNER_USERNAME: str = "@your_username"
