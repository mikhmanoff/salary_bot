# Импорт необходимых функций и сервисов
from services.google_services import get_google_sheet

# === Логика получения всех листов в Google Таблице ===
def get_month_sheets(sheet):
    worksheets = sheet.worksheets()
    # Возвращаем все листы, убираем лишние пробелы в их названиях, если есть
    month_sheets = [ws.title.strip() for ws in worksheets]
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
