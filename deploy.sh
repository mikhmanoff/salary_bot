#!/bin/bash

# Проверяем, если образ уже существует
if [[ "$(docker images -q telegram-bot:latest 2> /dev/null)" == "" ]]; then
  echo "Собираем Docker образ..."
  docker build -t telegram-bot:latest .
fi

# Проверяем, если контейнер уже запущен
if [[ "$(docker ps -q -f name=telegram-bot)" ]]; then
  echo "Останавливаем существующий контейнер..."
  docker stop telegram-bot
  docker rm telegram-bot
fi

# Запускаем новый контейнер
echo "Запускаем новый контейнер..."
docker run -d --name telegram-bot telegram-bot:latest
