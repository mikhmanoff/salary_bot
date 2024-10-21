import gspread
from googleapiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials
from config.settings import CREDENTIALS_FILE

# === Инициализация Google Drive и Google Sheets API ===
def get_google_services():
    scope = [
        'https://www.googleapis.com/auth/drive', 
        'https://www.googleapis.com/auth/spreadsheets.readonly', 
        "https://spreadsheets.google.com/feeds"
    ]
    
    # Получаем креды из JSON-файла
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
    
    # Инициализация сервисов для Google Drive и Google Sheets API
    drive_service = build('drive', 'v3', credentials=creds)
    sheets_service = build('sheets', 'v4', credentials=creds)
    
    # Инициализация gspread для работы с Google Sheets
    gspread_client = gspread.authorize(creds)
    
    return drive_service, sheets_service, gspread_client

# === Логика подключения к Google Таблице ===
def get_google_sheet(sheet_id):
    # Получаем сервисы
    _, _, gspread_client = get_google_services()
    
    # Открываем таблицу по ID
    return gspread_client.open_by_key(sheet_id)
