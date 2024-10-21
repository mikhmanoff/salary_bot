from googleapiclient.discovery import build
from aiogram import Bot, Dispatcher, Router
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from config.settings import TELEGRAM_BOT_TOKEN
from handlers import start, auth, salary

import asyncio
import os

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
GOOGLE_SHEET_ID = os.getenv('GOOGLE_SHEET_ID')
CREDENTIALS_FILE = os.getenv('CREDENTIALS_FILE')
FOLDER_ID = os.getenv('FOLDER_ID')

# Инициализация бота и диспетчера
bot = Bot(token=TELEGRAM_BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

router = Router()
#p.include_router(router)


# === Создаем группу состояний для FSM ===
class AuthStates(StatesGroup):
    waiting_for_employee_id = State()
    waiting_for_passport_digits = State()
    waiting_for_salary_type = State()
    waiting_for_period_start = State()
    waiting_for_period_end = State()
    waiting_for_month = State()  # Для выбора зарплаты за месяц

# === Получаем список файлов в папке (за исключением файла с авторизационными данными) ===
def list_files_in_folder(service, folder_id):
    # Используем запрос, чтобы получить список файлов в указанной папке Google Drive
    query = f"'{folder_id}' in parents and trashed=false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    return results.get('files', [])

# === Получаем список листов в файле Google Sheets ===
def get_sheets_from_file(file_id):
    # Подключаем Google Sheets API для работы с таблицами
    _, sheets_service = get_drive_service()

    # Получаем метаданные о таблице
    spreadsheet = sheets_service.spreadsheets().get(spreadsheetId=file_id).execute()
    sheets = spreadsheet.get('sheets', [])

    # Собираем названия листов
    sheet_names = [sheet['properties']['title'] for sheet in sheets]
    return sheet_names

# === Логика получения списка файлов после авторизации ===
def list_files_exclude_auth(service, folder_id, auth_file_id):
    files = list_files_in_folder(service, folder_id)
    # Исключаем файл с авторизацией из списка
    return [file for file in files if file['id'] != auth_file_id]

# === Логика получения списка файлов после авторизации ===
def list_files_exclude_auth(service, folder_id, auth_file_id):
    files = list_files_in_folder(service, folder_id)
    # Исключаем файл с авторизацией из списка
    return [file for file in files if file['id'] != auth_file_id]

# === Клавиатура ===
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="FAQ"), KeyboardButton(text="Авторизоваться")]
    ],
    resize_keyboard=True
)

# Регистрация роутеров
dp.include_router(start.router)
dp.include_router(auth.router)
dp.include_router(salary.router)

# Запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())