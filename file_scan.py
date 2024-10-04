from googleapiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials

# Указываем нужные переменные
CREDENTIALS_FILE = 'credentials.json'  # Ваш файл с ключами
folder_id = '1BNATGC0XG8taXXGRQJKhDK0H5V9I-ebe'

# Инициализация Google Drive API
def get_drive_service():
    scope = ['https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
    service = build('drive', 'v3', credentials=creds)
    return service

# Получаем список файлов в папке
def list_files_in_folder(service, folder_id):
    query = f"'{folder_id}' in parents and trashed=false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    return results.get('files', [])

# Основной код
def main():
    service = get_drive_service()
    files = list_files_in_folder(service, folder_id)

    if files:
        for file in files:
            # Выводим имя файла и его ID
            print(f"Файл: {file['name']}, ID: {file['id']}")
    else:
        print('Файлы в папке не найдены.')

if __name__ == '__main__':
    main()
