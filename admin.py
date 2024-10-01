# === Импорты ===
from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
import asyncio
import re

import gspread
from oauth2client.service_account import ServiceAccountCredentials

# === Глобальные переменные ===
CREDENTIALS_FILE = 'credentials.json'  # Файл учетных данных сервисного аккаунта
TELEGRAM_BOT_TOKEN = '7675134427:AAHICyIgG53cSQBHRQ3BpYBgtFC6b_6oxgY'  # Токен вашего Telegram-бота
SERVICE_ACCOUNT_EMAIL = 'service-account@salary-bot-test.iam.gserviceaccount.com'  # Email сервисного аккаунта
EXPECTED_HEADERS = ["Номер табеля", "ФИО", "Зарплата", "Налоги и удержания", "На руки"]
EXPECTED_AUTH_HEADERS = ["Номер табеля", "Последние цифры паспорта", "ФИО"]

# === Список разрешённых пользователей ===
AUTHORIZED_USERS = [64621696]  # Здесь указываем ID пользователей, которым разрешено пользоваться командами

# Инициализация бота и диспетчера
bot = Bot(token=TELEGRAM_BOT_TOKEN)
storage = MemoryStorage()  # Инициализируем MemoryStorage для хранения состояний
dp = Dispatcher(storage=storage)
router = Router()

# === Проверка авторизован ли пользователь ===
async def is_user_authorized(user_id, message: types.Message):
    if user_id in AUTHORIZED_USERS:
        # Если пользователь авторизован
        print("Администратор авторизован")  # Выводим в консоль
        await message.reply("Администратор авторизован")  # Сообщаем пользователю
        return True
    else:
        # Если пользователь не авторизован
        print(f"Несанкционированный вход от пользователя {user_id}")  # Выводим в консоль
        await message.reply("У вас нет прав для использования этой команды")  # Сообщаем пользователю
        return False

# === Логика подключения к Google Таблице ===
def get_google_sheet(sheet_id):
    # Устанавливаем связь с Google Sheets API
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    # Загружаем учетные данные из файла
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
    
    # Подключаемся к Google Sheets
    client = gspread.authorize(creds)
    
    # Открываем таблицу по ID
    sheet = client.open_by_key(sheet_id)
    
    return sheet

# === Извлечение ID таблицы из ссылки ===
def extract_table_id(table_url):
    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", table_url)
    if match:
        return match.group(1)
    return None

# === Проверка структуры листа с указанием координат ===
def check_sheet_structure(sheet):
    # Получаем первую строку (заголовки) листа
    headers = sheet.row_values(1)
    
    # Проверяем, все ли ожидаемые заголовки присутствуют
    missing_headers = []
    incorrect_cells = []
    
    for idx, (expected_header, cell_value) in enumerate(zip(EXPECTED_HEADERS, headers)):
        if expected_header != cell_value:
            # Определяем координаты ячейки
            column_letter = chr(65 + idx)  # A, B, C и т.д.
            cell_position = f"{column_letter}1"
            missing_headers.append(f"{expected_header} ({cell_value} вместо '{expected_header}')")
            incorrect_cells.append(f"{cell_position}: {cell_value}")
    
    if missing_headers:
        # Возвращаем False, список недостающих заголовков и координаты ячеек с ошибками
        return False, missing_headers, incorrect_cells
    else:
        return True, [], []  # Если всё в порядке, возвращаем True и пустые списки

# === Проверка структуры листа "Авторизация" с указанием координат ===
def check_auth_sheet_structure(sheet):
    # Получаем первую строку (заголовки) листа
    headers = sheet.row_values(1)
    
    # Проверяем, все ли ожидаемые заголовки присутствуют
    missing_headers = []
    incorrect_cells = []
    
    for idx, (expected_header, cell_value) in enumerate(zip(EXPECTED_AUTH_HEADERS, headers)):
        if expected_header != cell_value:
            # Определяем координаты ячейки
            column_letter = chr(65 + idx)  # A, B, C и т.д.
            cell_position = f"{column_letter}1"
            missing_headers.append(f"{expected_header} ({cell_value} вместо '{expected_header}')")
            incorrect_cells.append(f"{cell_position}: {cell_value}")
    
    if missing_headers:
        # Возвращаем False, список недостающих заголовков и координаты ячеек с ошибками
        return False, missing_headers, incorrect_cells
    else:
        return True, [], []  # Если всё в порядке, возвращаем True и пустые списки
    
# === Проверка заполненности данных только для первых 3 столбцов на листе "Авторизация" ===
def check_auth_data_filled(sheet):
    # Получаем все строки, начиная со второй (1-я строка - это заголовки)
    rows = sheet.get_all_values()[1:]  # Пропускаем заголовки
    
    incomplete_rows = []  # Список строк с неполными данными
    
    for row_idx, row in enumerate(rows, start=2):  # Строки нумеруются с 2, так как 1-я - это заголовки
        # Проверяем заполненность только первых 3 столбцов
        first_three_columns = row[:3]  # Берем только первые три столбца
        if any(cell.strip() == "" for cell in first_three_columns):  # Проверяем, что все ячейки заполнены
            incomplete_rows.append(row_idx)  # Если есть пустая ячейка, добавляем номер строки
    
    if incomplete_rows:
        return False, incomplete_rows
    else:
        return True, []

# === Получение всех листов, кроме "Авторизация" ===
def get_other_sheets(sheet, exclude_sheet_name):
    # Получаем все листы в таблице
    sheet_list = sheet.worksheets()
    
    # Фильтруем листы, исключая лист с именем exclude_sheet_name
    other_sheets = [worksheet.title for worksheet in sheet_list if worksheet.title != exclude_sheet_name]
    
    return other_sheets

# === Вывод всех найденных листов ===
async def display_sheets_list(message: types.Message, other_sheets):
    response_message = f"Найдено {len(other_sheets)} листов:\n"
    for i, sheet_name in enumerate(other_sheets, start=1):
        response_message += f"{i}. {sheet_name}\n"
    await message.reply(response_message)

# === Обработка команды /start для администратора ===
@router.message(Command("start"))
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    
    # Проверяем, авторизован ли пользователь
    if not await is_user_authorized(user_id, message):
        return  # Если пользователь не авторизован, выходим из функции
    
    # Приветствие и запрос ссылки на таблицу
    await message.reply("Добро пожаловать! Пожалуйста, отправьте ссылку на таблицу для проверки.")

# === Обработка получения ссылки на таблицу и проверки доступа ===
@router.message()
# === Обработка получения ссылки на таблицу и проверки доступа ===
@router.message()
async def check_table_access_handler(message: types.Message):
    table_url = message.text
    table_id = extract_table_id(table_url)
    
    user_id = message.from_user.id
    
    # Проверяем, авторизован ли пользователь
    if not await is_user_authorized(user_id, message):
        return  # Если пользователь не авторизован, выходим из функции
    
    if not table_id:
        await message.reply("Не удалось извлечь ID таблицы. Убедитесь, что вы отправили правильную ссылку.")
        return

    try:
        # Подключаемся к таблице и получаем её название
        sheet = get_google_sheet(table_id)
        sheet_title = sheet.title  # Название таблицы
        print(f"Успешно подключились к таблице: {sheet_title}")  # Выводим название в консоль
        
        # Проверяем структуру листа "Авторизация"
        auth_worksheet = sheet.worksheet("Авторизация")
        auth_structure_ok, auth_missing_headers, auth_incorrect_cells = check_auth_sheet_structure(auth_worksheet)
        
        if auth_structure_ok:
            await message.reply("Лист 'Авторизация' прошел проверку структуры успешно.")
            
            # Проверка на заполненность данных в листе "Авторизация"
            data_filled_ok, incomplete_rows = check_auth_data_filled(auth_worksheet)
            if data_filled_ok:
                await message.reply("Все данные пользователей на листе 'Авторизация' заполнены.")
            else:
                incomplete_rows_str = ", ".join(map(str, incomplete_rows))
                await message.reply(f"Незаполненные данные найдены в строках: {incomplete_rows_str}")
        else:
            # Формируем сообщение о неправильной структуре листа "Авторизация"
            auth_missing_headers_str = ", ".join([f"{header} ({cell})" for header, cell in zip(auth_missing_headers, auth_incorrect_cells)])
            await message.reply(f"Лист 'Авторизация' не прошел проверку структуры: Недостающие заголовки: {auth_missing_headers_str}")

        # Проверяем наличие листов, кроме "Авторизация"
        other_sheets = get_other_sheets(sheet, "Авторизация")
        failed_sheets = []  # Листы, которые не прошли проверку
        
        if other_sheets:
            for sheet_name in other_sheets:
                worksheet = sheet.worksheet(sheet_name)
                
                # Проверяем структуру каждого листа
                structure_ok, missing_headers, incorrect_cells = check_sheet_structure(worksheet)
                
                if not structure_ok:
                    # Если структура не прошла проверку, добавляем лист в список с ошибками
                    missing_headers_str = ", ".join([f"{header} ({cell})" for header, cell in zip(missing_headers, incorrect_cells)])
                    failed_sheets.append(f"Лист '{sheet_name}': Недостающие заголовки: {missing_headers_str}")
        
        # Выводим список всех листов
        await display_sheets_list(message, other_sheets)
        
        # Формируем ответ в зависимости от результатов проверки структуры
        if failed_sheets:
            # Сообщаем, какие листы не прошли проверку
            response_message = "Следующие листы не прошли проверку структуры:\n\n"
            response_message += "\n".join(failed_sheets)
            await message.reply(response_message)
        else:
            # Сообщаем, что все листы успешно прошли проверку
            await message.reply("Все листы прошли проверку структуры успешно.")
    
    except gspread.exceptions.APIError as e:
        # Если произошла ошибка доступа
        await message.reply("Ошибка доступа к таблице. Убедитесь, что у бота есть права на доступ к таблице.")


# === Запуск бота ===
async def main():
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
