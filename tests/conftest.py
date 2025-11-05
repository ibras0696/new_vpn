import os

# Минимальный набор переменных окружения, чтобы pydantic Settings успешно инициализировались.
os.environ.setdefault("BOT_TOKEN", "test-token")
os.environ.setdefault("ADMIN_ID", "1")
os.environ.setdefault("XRAY_DOMAIN", "example.com")
os.environ.setdefault("XRAY_API_HOST", "host.docker.internal")
