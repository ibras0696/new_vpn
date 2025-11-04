FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

ARG XRAY_VERSION=1.8.14

WORKDIR /app

# Устанавливаем системные зависимости, необходимые для сборки некоторых пакетов
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential libjpeg62-turbo-dev zlib1g-dev curl unzip ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Устанавливаем бинарь XRay CLI (для управления API)
RUN curl -fsSL -o /tmp/xray.zip https://github.com/XTLS/Xray-core/releases/download/v${XRAY_VERSION}/Xray-linux-64.zip && \
    unzip /tmp/xray.zip -d /tmp/xray && \
    install -m 755 /tmp/xray/xray /usr/local/bin/xray && \
    mkdir -p /usr/local/share/xray && \
    install -m 644 /tmp/xray/*.dat /usr/local/share/xray/ && \
    rm -rf /tmp/xray /tmp/xray.zip

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
