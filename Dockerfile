FROM python:3.11-slim

WORKDIR /app

# Установка зависимостей системы
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Копирование requirements и установка Python зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода агента
COPY code_agent/ code_agent/
COPY reviewer.py .

# Создание точки входа для CLI
ENTRYPOINT ["python", "-m", "code_agent.cli"]

# Дефолтный help если аргументы не переданы
CMD ["--help"]
