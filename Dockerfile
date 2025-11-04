FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Устанавливаем системные зависимости, необходимые для сборки некоторых пакетов
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential libjpeg62-turbo-dev zlib1g-dev && \
    rm -rf /var/lib/apt/lists/*

# Копируем минимальный набор файлов для установки зависимостей
COPY pyproject.toml ./
COPY config.py main.py orm_main.py ./
COPY data ./data
COPY handlers ./handlers
COPY services ./services

RUN pip install --upgrade pip && \
    pip install --no-cache-dir .

# Копируем оставшийся код проекта (скрипты, конфиги, вспомогательные файлы)
COPY . .

# Контейнер по умолчанию запускает Telegram-бота
CMD ["python", "-m", "main"]
