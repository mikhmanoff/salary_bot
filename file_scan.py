from googleapiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials
from aiogram import Bot, Dispatcher
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import F

CREDENTIALS_FILE = 'credentials.json'  # Ваш файл с ключами
folder_id = '1BNATGC0XG8taXXGRQJKhDK0H5V9I-ebe'  # ID папки, где хранятся файлы с данными
TELEGRAM_TOKEN = '7675134427:AAHICyIgG53cSQBHRQ3BpYBgtFC6b_6oxgY'  # Ваш Telegram токен

# === Инициализация Google Drive и Google Sheets API ===
def get_drive_service():
    scope = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/spreadsheets.readonly']
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
    drive_service = build('drive', 'v3', credentials=creds)
    sheets_service = build('sheets', 'v4', credentials=creds)
    return drive_service, sheets_service


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


# === Обработчик команды /start ===
async def start_command(message: Message, bot: Bot):
    drive_service, _ = get_drive_service()
    
    # Получаем список файлов в указанной папке
    files = list_files_in_folder(drive_service, folder_id)

    # Список файлов с данными, кроме файла с авторизацией
    auth_file_id = '1fAxmOI-UoABBuzqA_7sETuLhI7MT_Wg6UJUTzyuZyT0'  # ID файла с авторизацией
    
    # Исключаем файл с авторизацией из списка
    files_without_auth = [file for file in files if file['id'] != auth_file_id]

    if files_without_auth:
        keyboard_builder = InlineKeyboardBuilder()

        # Добавляем кнопки с именем и ID файла, кроме файла авторизации
        for file in files_without_auth:
            # Отображаем имя файла и его ID на кнопке
            button_text = f"{file['name']} (ID: {file['id']})"
            keyboard_builder.add(InlineKeyboardButton(text=button_text, callback_data=f"file_{file['id']}"))

        await message.answer('Выберите файл для просмотра листов:', reply_markup=keyboard_builder.as_markup())
    else:
        await message.answer('Файлы в папке не найдены.')


# === Обработчик callback кнопок для выбора файла и получения листов ===
async def handle_callback(callback_query: CallbackQuery, bot: Bot):
    data = callback_query.data

    if data.startswith('file_'):
        file_id = data.split('_')[1]

        # Получаем листы из выбранного файла Google Sheets
        sheets = get_sheets_from_file(file_id)

        if sheets:
            keyboard_builder = InlineKeyboardBuilder()
            for sheet in sheets:
                keyboard_builder.add(InlineKeyboardButton(text=sheet, callback_data=f"sheet_{sheet}"))

            await callback_query.message.edit_text(f'Файл с ID: {file_id}\nВыберите лист:', reply_markup=keyboard_builder.as_markup())
        else:
            await callback_query.message.edit_text('Листы не найдены.')

    await callback_query.answer()


# === Инициализация бота и диспетчера ===
async def main():
    bot = Bot(token=TELEGRAM_TOKEN)
    dp = Dispatcher()

    # Регистрируем обработчики команд и callback
    dp.message.register(start_command, Command(commands=['start']))
    dp.callback_query.register(handle_callback)

    # Запускаем polling
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
