import os
from dotenv import load_dotenv

# Загрузка переменных из .env
load_dotenv()

# Настройки приложения
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
GOOGLE_SHEET_ID = os.getenv('GOOGLE_SHEET_ID')
CREDENTIALS_FILE = os.getenv('CREDENTIALS_FILE')
FOLDER_ID = os.getenv('FOLDER_ID')
