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
GOOGLE_SHEET_NAME = 'Январь'
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
    await state.update_data(employee_id=employee_id)  # Сохраняем номер табеля в состоянии
    
    # Логируем данные для отладки
    user_data = await state.get_data()
    print(f"Employee ID saved: {user_data['employee_id']}")  # Для отладки
    
    await message.reply("Введите последние 4 цифры вашего паспорта:")
    await state.set_state(AuthStates.waiting_for_passport_digits)  # Переход к следующему состоянию

# === Логика обработки выбора месяца ===
async def ask_for_period(message: types.Message, state: FSMContext):
    await message.reply("Выберите месяц, за который хотите посмотреть зарплату:\n\n1. Январь\n2. Февраль\n3. Март\n4. Апрель\n5. Май\n6. Июнь\n7. Июль\n8. Август\n9. Сентябрь\n10. Октябрь\n11. Ноябрь\n12. Декабрь")
    await state.set_state(AuthStates.waiting_for_period)

    
# === Обработка выбранного месяца ===
@router.message(AuthStates.waiting_for_period)
async def period_handler(message: types.Message, state: FSMContext):
    month = message.text
    month_map = {
        "1": "Январь",
        "2": "Февраль",
        "3": "Март",
        "4": "Апрель",
        "5": "Май",
        "6": "Июнь",
        "7": "Июль",
        "8": "Август",
        "9": "Сентябрь",
        "10": "Октябрь",
        "11": "Ноябрь",
        "12": "Декабрь"
    }
    
    if month not in month_map:
        await message.reply("Неверный выбор. Пожалуйста, выберите номер месяца от 1 до 12.")
        return
    
    selected_month = month_map[month]
    await state.update_data(selected_month=selected_month)
    
    # Получаем данные состояния (номер табеля и выбранный месяц)
    user_data = await state.get_data()
    employee_id = user_data['employee_id']
    
    # Подключаемся к соответствующему листу в Google Sheet на основе выбранного месяца
    sheet = get_google_sheet(GOOGLE_SHEET_ID, selected_month)
    
    # Получаем и показываем данные сотрудника
    await display_employee_data(message, employee_id, selected_month)
    
    # Сбрасываем состояние
    await state.clear()

async def display_employee_data(message: types.Message, employee_id: str, selected_month: str):
    # Подключаемся к Google Sheet на основе выбранного месяца
    sheet = get_google_sheet(GOOGLE_SHEET_ID, selected_month)
    
    # Получаем данные сотрудника по номеру табеля
    employee_data = get_employee_data(sheet, employee_id)
    
    if employee_data:
        # Формируем сообщение с информацией о пользователе
        response_message = (
            f"Авторизация успешна!\n\n"
            f"ФИО: {employee_data['ФИО']}\n"
            f"Зарплата за {selected_month}: {employee_data['Зарплата']}\n"
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
        print(f"Authorized: Employee ID: {employee_id}")  # Логирование для отладки
        return employee_id  # Авторизация прошла успешно, возвращаем номер табеля
    else:
        await message.reply("Неверные данные, попробуйте снова.")
        print(f"Authorization failed: Employee ID: {employee_id}, Passport: {passport_digits}")  # Логирование
        return None

# === Обработка введенных цифр паспорта ===
@router.message(AuthStates.waiting_for_passport_digits)
async def passport_digits_handler(message: types.Message, state: FSMContext):
    employee_id = await authorize_user(message, state)  # Пытаемся авторизовать пользователя
    
    if employee_id:
        # Если авторизация прошла успешно, запрашиваем у пользователя выбор месяца
        print("Authorization successful!")  # Логирование для отладки
        await ask_for_period(message, state)
    else:
        # Если авторизация не прошла, сбрасываем состояние
        print("Authorization failed.")  # Логирование для отладки
        await state.clear()

# Запуск бота
async def main():
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())