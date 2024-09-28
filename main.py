# Импорты и инициализация
from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
import asyncio

import gspread
from oauth2client.service_account import ServiceAccountCredentials

# === Глобальные переменные ===
GOOGLE_SHEET_ID = '1HUI5nJSgX004J1ocZTKm0kxxW1qQg227Ox10hgv4XY0'  # ID твоей Google Таблицы
GOOGLE_SHEET_NAME = 'Лист1'
CREDENTIALS_FILE = 'credentials.json'
TELEGRAM_BOT_TOKEN = '7675134427:AAHICyIgG53cSQBHRQ3BpYBgtFC6b_6oxgY'

# Инициализация бота и диспетчера
bot = Bot(token=TELEGRAM_BOT_TOKEN)
storage = MemoryStorage()  # Инициализируем MemoryStorage для хранения состояний
dp = Dispatcher(storage=storage)
router = Router()

# === Создаем группу состояний для FSM ===
class AuthStates(StatesGroup):
    waiting_for_employee_id = State()  # Ожидание ввода номера табеля
    waiting_for_passport_digits = State()  # Ожидание ввода последних 4 цифр паспорта
    waiting_for_period = State()  # Ожидание выбора периода

# === Логика получения строки данных о пользователе ===
def get_employee_data(sheet, employee_id):
    data = sheet.get_all_records()  # Получаем все записи из таблицы
    
    for record in data:
        if str(record['Номер табеля']) == employee_id:
            # Возвращаем данные о пользователе, если совпал номер табеля
            return record
    return None  # Возвращаем None, если данные не найдены

# === Логика подключения к Google Таблице ===
def get_google_sheet(sheet_id, sheet_name):
    # Устанавливаем связь с Google Sheets API
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    # Загружаем учетные данные из файла
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
    
    # Подключаемся к Google Sheets
    client = gspread.authorize(creds)
    
    # Открываем таблицу по ID
    sheet = client.open_by_key(sheet_id)
    
    # Открываем лист по имени
    worksheet = sheet.worksheet(sheet_name)
    
    return worksheet

# === Логика проверки авторизации пользователя ===
def check_auth(sheet, employee_id, passport_digits):
    data = sheet.get_all_records()  # Получаем все записи из таблицы
    
    for record in data:
        if str(record['Номер табеля']) == employee_id and str(record['Последние цифры паспорта']) == passport_digits:
            return True  # Авторизация прошла успешно
    return False  # Авторизация не пройдена

# === Обработка команды /start ===
@router.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    await message.reply("Введите ваш номер табеля:")
    await state.set_state(AuthStates.waiting_for_employee_id)

# === Обработка введенного номера табеля ===
@router.message(AuthStates.waiting_for_employee_id)
async def employee_id_handler(message: types.Message, state: FSMContext):
    employee_id = message.text
    await state.update_data(employee_id=employee_id)
    await message.reply("Введите последние 4 цифры вашего паспорта:")
    await state.set_state(AuthStates.waiting_for_passport_digits)

async def display_employee_data(message: types.Message, employee_id: str):
    # Подключаемся к Google Sheet
    sheet = get_google_sheet(GOOGLE_SHEET_ID, GOOGLE_SHEET_NAME)
    
    # Получаем данные сотрудника по номеру табеля
    employee_data = get_employee_data(sheet, employee_id)
    
    if employee_data:
        # Формируем сообщение с информацией о пользователе
        response_message = (
            f"Авторизация успешна!\n\n"
            f"ФИО: {employee_data['ФИО']}\n"
            f"Зарплата: {employee_data['Зарплата']}\n"
            f"Налоги и удержания: {employee_data['Налоги и удержания']}\n"
            f"На руки: {employee_data['На руки']}\n"
        )
        await message.reply(response_message)
    else:
        await message.reply("Ошибка: Не удалось найти данные о пользователе.")

# === Функция для проверки авторизации ===
async def authorize_user(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    employee_id = user_data['employee_id']
    passport_digits = message.text

    # Подключаемся к Google Sheet
    sheet = get_google_sheet(GOOGLE_SHEET_ID, GOOGLE_SHEET_NAME)
    
    # Проверяем авторизацию
    if check_auth(sheet, employee_id, passport_digits):
        return employee_id  # Авторизация прошла успешно, возвращаем номер табеля
    else:
        await message.reply("Неверные данные, попробуйте снова.")
        return None

# === Обработка введенных цифр паспорта ===
@router.message(AuthStates.waiting_for_passport_digits)
async def passport_digits_handler(message: types.Message, state: FSMContext):
    employee_id = await authorize_user(message, state)  # Пытаемся авторизовать пользователя
    
    if employee_id:
        # Если авторизация прошла успешно, показываем данные
        await display_employee_data(message, employee_id)
    
    # Сбрасываем состояние
    await state.clear()

# Запуск бота
async def main():
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
