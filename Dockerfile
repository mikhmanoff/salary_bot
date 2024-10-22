# Базовый образ Python
FROM python:3.11-slim

# Установка зависимостей
WORKDIR /app
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода приложения
COPY . /app

# Экспорт переменных среды (если необходимо)
ENV BOT_ENV=production

# Указываем команду для запуска бота
CMD ["python", "main.py"]
