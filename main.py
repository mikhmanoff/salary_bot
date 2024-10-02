from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

import asyncio

import gspread
from oauth2client.service_account import ServiceAccountCredentials

# === Глобальные переменные ===
GOOGLE_SHEET_ID = '1HUI5nJSgX004J1ocZTKm0kxxW1qQg227Ox10hgv4XY0'  # ID твоей Google Таблицы
CREDENTIALS_FILE = 'credentials.json'
TELEGRAM_BOT_TOKEN = '7675134427:AAHICyIgG53cSQBHRQ3BpYBgtFC6b_6oxgY'  # Укажи свой токен бота

# Инициализация бота и диспетчера
bot = Bot(token=TELEGRAM_BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()

# === Создаем группу состояний для FSM ===
class AuthStates(StatesGroup):
    waiting_for_employee_id = State()
    waiting_for_passport_digits = State()
    waiting_for_period = State()

# === Логика подключения к Google Таблице ===
def get_google_sheet(sheet_id):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
    client = gspread.authorize(creds)
    return client.open_by_key(sheet_id)

# === Логика получения листов (кроме первого) ===
def get_month_sheets(sheet):
    worksheets = sheet.worksheets()
    month_sheets = [ws.title for ws in worksheets[1:]]  # Пропускаем первый лист
    return month_sheets

# === Логика получения строки данных о пользователе ===
def get_employee_data(sheet, employee_id):
    data = sheet.get_all_records()
    for record in data:
        if str(record['Номер табеля']) == employee_id:
            return record
    return None

# === Логика проверки авторизации пользователя ===
def check_auth(sheet, employee_id, passport_digits):
    data = sheet.get_all_records()
    for record in data:
        if 'Номер табеля' in record and 'Последние цифры паспорта' in record:
            if str(record['Номер табеля']) == employee_id and str(record['Последние цифры паспорта']) == passport_digits:
                return True
    return False

# === Логика создания callback-кнопок с названиями месяцев ===
def create_month_buttons(month_sheets):
    keyboard = []  # Создаем пустой список для кнопок
    for month in month_sheets:
        # Добавляем кнопки в список
        button = InlineKeyboardButton(text=month, callback_data=f"month_{month}")
        keyboard.append([button])  # Каждую кнопку добавляем как отдельный массив (одна кнопка на строке)
    return InlineKeyboardMarkup(inline_keyboard=keyboard)  # Передаем список кнопок в InlineKeyboardMarkup


# === Обработка команды /start ===
@router.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    await message.reply("Добро пожаловать! Выберите одну из опций:", reply_markup=main_menu)

# === Обработка кнопки FAQ ===
@router.message(lambda message: message.text == "FAQ")
async def faq(message: types.Message):
    await message.reply("Этот бот позволяет вам получить информацию о зарплате. Для начала нажмите 'Авторизоваться' и введите ваш номер табеля и последние 4 цифры паспорта.")

# === Обработка кнопки Авторизоваться ===
@router.message(lambda message: message.text == "Авторизоваться")
async def start_authorization(message: types.Message, state: FSMContext):
    await message.reply("Введите ваш номер табеля:")
    await state.set_state(AuthStates.waiting_for_employee_id)

# === Обработка введенного номера табеля ===
@router.message(AuthStates.waiting_for_employee_id)
async def employee_id_handler(message: types.Message, state: FSMContext):
    employee_id = message.text
    await state.update_data(employee_id=employee_id)
    
    await message.reply("Введите последние 4 цифры вашего паспорта:")
    await state.set_state(AuthStates.waiting_for_passport_digits)

# === Обработка введенных последних цифр паспорта ===
@router.message(AuthStates.waiting_for_passport_digits)
async def passport_digits_handler(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    employee_id = user_data['employee_id']
    passport_digits = message.text

    # Проверка авторизации через Google Sheets
    sheet = get_google_sheet(GOOGLE_SHEET_ID).worksheet('Авторизация')
    if check_auth(sheet, employee_id, passport_digits):
        await message.reply("Авторизация успешна! Выберите месяц для получения данных о зарплате:")

        # Получаем список листов (кроме первого) и выводим их в виде кнопок
        month_sheets = get_month_sheets(get_google_sheet(GOOGLE_SHEET_ID))
        keyboard = create_month_buttons(month_sheets)

        await message.reply("Выберите месяц:", reply_markup=keyboard)
        await state.set_state(AuthStates.waiting_for_period)
    else:
        await message.reply("Неверные данные, попробуйте снова.")
        await state.clear()

# === Обработка нажатий на callback-кнопки с месяцами ===
@router.callback_query(lambda c: c.data and c.data.startswith("month_"))
async def period_handler(callback_query: types.CallbackQuery, state: FSMContext):
    selected_month = callback_query.data.split("_")[1]  # Извлекаем месяц из callback data

    # Обновляем данные состояния
    await state.update_data(selected_month=selected_month)
    
    user_data = await state.get_data()
    employee_id = user_data['employee_id']

    # Получаем лист Google Sheet для выбранного месяца
    sheet = get_google_sheet(GOOGLE_SHEET_ID).worksheet(selected_month)
    
    # Отображаем данные сотрудника
    await display_employee_data(callback_query.message, employee_id, selected_month)
    
    await state.clear()

# === Логика отображения данных о зарплате ===
async def display_employee_data(message: types.Message, employee_id: str, selected_month: str):
    sheet = get_google_sheet(GOOGLE_SHEET_ID).worksheet(selected_month)
    employee_data = get_employee_data(sheet, employee_id)
    
    if employee_data:
        response_message = (
            f"ФИО: {employee_data['ФИО']}\n"
            f"Зарплата за {selected_month}: {employee_data['Зарплата']}\n"
            f"Налоги и удержания: {employee_data['Налоги и удержания']}\n"
            f"На руки: {employee_data['На руки']}\n"
        )
        await message.reply(response_message)
    else:
        await message.reply("Ошибка: Не удалось найти данные о пользователе.")

# === Клавиатура ===
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="FAQ"), KeyboardButton(text="Авторизоваться")]
    ],
    resize_keyboard=True
)

# Запуск бота
async def main():
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
