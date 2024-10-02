from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import Command
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
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
#p.include_router(router)


# === Создаем группу состояний для FSM ===
class AuthStates(StatesGroup):
    waiting_for_employee_id = State()
    waiting_for_passport_digits = State()
    waiting_for_salary_type = State()
    waiting_for_period_start = State()
    waiting_for_period_end = State()
    waiting_for_month = State()  # Для выбора зарплаты за месяц

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


# === Логика создания callback-кнопок для выбора типа данных ===
def create_salary_type_buttons():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Зарплата за месяц", callback_data="salary_month")],
        [InlineKeyboardButton(text="Зарплата с начала года", callback_data="salary_year")],
        [InlineKeyboardButton(text="Зарплата за период", callback_data="salary_period")]
    ])
    return keyboard

# === Логика создания callback-кнопок с названиями месяцев ===
def create_month_buttons(month_sheets):
    keyboard = []  # Создаем пустой список для кнопок
    for month in month_sheets:
        button = InlineKeyboardButton(text=month, callback_data=f"month_{month}")
        keyboard.append([button])  # Каждую кнопку добавляем как отдельный массив (одна кнопка на строке)
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

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
        await message.reply("Авторизация успешна! Выберите тип данных:", reply_markup=create_salary_type_buttons())
        await state.set_state(AuthStates.waiting_for_salary_type)
    else:
        await message.reply("Неверные данные, попробуйте снова.")
        await state.clear()

# === Обработка выбора типа данных ===
@router.callback_query(StateFilter(AuthStates.waiting_for_salary_type), lambda c: c.data in ["salary_month", "salary_year", "salary_period"])
async def salary_type_handler(callback_query: types.CallbackQuery, state: FSMContext):
    salary_type = callback_query.data
    sheet = get_google_sheet(GOOGLE_SHEET_ID)
    month_sheets = get_month_sheets(sheet)

    # Получаем employee_id из состояния
    user_data = await state.get_data()
    employee_id = user_data['employee_id']
    
    if salary_type == "salary_month":
        # Изменяем сообщение, удаляя кнопки и обновляя текст
        await callback_query.message.edit_text("Вы выбрали просмотр зарплаты за определенный месяц.")
        # Переходим к выбору конкретного месяца
        await callback_query.message.answer("Выберите месяц:", reply_markup=create_month_buttons(month_sheets))
        await state.set_state(AuthStates.waiting_for_month)
    
    elif salary_type == "salary_year":
        # Изменяем сообщение, удаляя кнопки и обновляя текст
        await callback_query.message.edit_text("Вы выбрали просмотр зарплаты за все месяцы в этом году.")
        # Суммируем все месяцы до текущего момента
        await sum_salary(callback_query.message, month_sheets, employee_id)  # Передаем employee_id
        await state.clear()
    
    elif salary_type == "salary_period":
        # Изменяем сообщение, удаляя кнопки и обновляя текст
        await callback_query.message.edit_text("Вы выбрали просмотр зарплаты за определенный период.")
        # Переходим к выбору начала и конца периода
        await callback_query.message.answer("Выберите начало периода:", reply_markup=create_month_buttons(month_sheets))
        await state.set_state(AuthStates.waiting_for_period_start)

# === Обработка выбора месяца для зарплаты за месяц ===
@router.callback_query(StateFilter(AuthStates.waiting_for_month), lambda c: c.data.startswith("month_"))
async def month_salary_handler(callback_query: types.CallbackQuery, state: FSMContext):
    selected_month = callback_query.data.split("_")[1]
    user_data = await state.get_data()
    employee_id = user_data['employee_id']
    
    # Изменяем сообщение с кнопками
    await callback_query.message.edit_text(f"Вы выбрали месяц {selected_month}.")

    # Получаем данные за конкретный месяц
    sheet = get_google_sheet(GOOGLE_SHEET_ID).worksheet(selected_month)
    employee_data = get_employee_data(sheet, employee_id)

    if employee_data:
        # Используем метод .get() для безопасного доступа к значениям
        salary = employee_data.get('Зарплата', 'Не указано')
        taxes = employee_data.get('Налоги и удержания', 'Не указано')
        net = employee_data.get('На руки', 'Не указано')
        fio = employee_data.get('ФИО', 'Не указано')

        response_message = (
            f"ФИО: {fio}\n"
            f"Зарплата за {selected_month}: {salary}\n"
            f"Налоги и удержания: {taxes}\n"
            f"На руки: {net}\n"
        )
        await callback_query.message.answer(response_message)
    else:
        await callback_query.message.answer("Ошибка: Не удалось найти данные о пользователе.")

    await state.clear()

# === Обработка выбора начала периода ===
@router.callback_query(StateFilter(AuthStates.waiting_for_period_start), lambda c: c.data.startswith("month_"))
async def period_start_handler(callback_query: types.CallbackQuery, state: FSMContext):
    selected_month = callback_query.data.split("_")[1]

    # Изменяем сообщение, убираем кнопки
    await callback_query.message.edit_text(f"Начало периода выбрано: **{selected_month}**", parse_mode="Markdown")

    await state.update_data(period_start=selected_month)
    sheet = get_google_sheet(GOOGLE_SHEET_ID)
    month_sheets = get_month_sheets(sheet)

    # Переход к выбору конца периода
    await callback_query.message.answer("Выберите конец периода:", reply_markup=create_month_buttons(month_sheets))
    await state.set_state(AuthStates.waiting_for_period_end)

# === Обработка выбора конца периода ===
@router.callback_query(StateFilter(AuthStates.waiting_for_period_end), lambda c: c.data.startswith("month_"))
async def period_end_handler(callback_query: types.CallbackQuery, state: FSMContext):
    selected_month = callback_query.data.split("_")[1]
    user_data = await state.get_data()
    period_start = user_data['period_start']
    employee_id = user_data['employee_id']

    # Изменяем сообщение, убираем кнопки
    await callback_query.message.edit_reply_markup(reply_markup=None)

    # Отправляем отдельное сообщение о выборе конца периода
    await callback_query.message.answer(f"Конец периода выбрано: **{selected_month}**", parse_mode="Markdown")

    # Добавляем задержку в 2 секунды (можно изменить значение)
    await asyncio.sleep(0.5)

    # Отправляем сообщение с выбранным диапазоном, выделяя месяцы жирным
    await callback_query.message.answer(f"Вы выбрали просмотр зарплаты с месяца **{period_start}** по месяц **{selected_month}**.", parse_mode="Markdown")

    # Добавляем еще одну задержку перед суммированием (по желанию)
    await asyncio.sleep(0.5)

    # Суммируем зарплату за период
    await sum_salary_period(callback_query.message, period_start, selected_month, employee_id)
    await state.clear()

# === Логика для суммирования зарплаты за период ===
async def sum_salary_period(message: types.Message, period_start: str, period_end: str, employee_id: str):
    sheet = get_google_sheet(GOOGLE_SHEET_ID)
    month_sheets = get_month_sheets(sheet)
    start_index = month_sheets.index(period_start)
    end_index = month_sheets.index(period_end) + 1
    selected_months = month_sheets[start_index:end_index]

    total_salary = 0
    total_taxes = 0
    total_net = 0

    for month in selected_months:
        employee_data = get_employee_data(sheet.worksheet(month), employee_id)
        if employee_data:
            # Используем .get() для безопасного доступа к данным
            salary = employee_data.get('Зарплата', '0').replace('\xa0', '').replace(',', '.')
            taxes = employee_data.get('Налоги и удержания', '0').replace('\xa0', '').replace(',', '.')
            net = employee_data.get('На руки', '0').replace('\xa0', '').replace(',', '.')

            total_salary += float(salary)
            total_taxes += float(taxes)
            total_net += float(net)

    # Форматируем суммы с разделением тысяч
    formatted_salary = f"{total_salary:,.2f}".replace(',', "'")
    formatted_taxes = f"{total_taxes:,.2f}".replace(',', "'")
    formatted_net = f"{total_net:,.2f}".replace(',', "'")

    await message.reply(f"Зарплата за период с {period_start} по {period_end}:\n"
                        f"Зарплата: {formatted_salary}\n"
                        f"Налоги и удержания: {formatted_taxes}\n"
                        f"На руки: {formatted_net}")


# === Логика для суммирования зарплаты с начала года ===
async def sum_salary(message: types.Message, month_sheets, employee_id):
    total_salary = 0
    total_taxes = 0
    total_net = 0
    
    sheet = get_google_sheet(GOOGLE_SHEET_ID)  # Получаем объект Google Sheet

    for month in month_sheets:
        employee_data = get_employee_data(sheet.worksheet(month), employee_id)
        if employee_data:
            # Используем .get() для безопасного доступа к данным
            salary = employee_data.get('Зарплата', '0').replace('\xa0', '').replace(',', '.')
            taxes = employee_data.get('Налоги и удержания', '0').replace('\xa0', '').replace(',', '.')
            net = employee_data.get('На руки', '0').replace('\xa0', '').replace(',', '.')
            
            # Преобразуем строки в float и складываем
            total_salary += float(salary)
            total_taxes += float(taxes)
            total_net += float(net)

    # Форматируем суммы с разделением тысяч
    formatted_salary = f"{total_salary:,.2f}".replace(',', "'")
    formatted_taxes = f"{total_taxes:,.2f}".replace(',', "'")
    formatted_net = f"{total_net:,.2f}".replace(',', "'")

    await message.reply(f"Зарплата с начала года: {formatted_salary}\n"
                        f"Налоги и удержания: {formatted_taxes}\n"
                        f"На руки: {formatted_net}")


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
