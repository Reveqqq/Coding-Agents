#!/bin/bash

# Скрипт для запуска Code Agent в Docker локально

set -e

# Загружаем переменные из .env если они не установлены
if [ -f .env ]; then
    echo "Загружаем переменные из .env..."
    # Читаем .env и экспортируем (пропускаем комментарии и пустые строки)
    set -a
    source .env
    set +a
fi

# Проверка переменных окружения
if [ -z "$GITHUB_TOKEN" ]; then
    echo "Ошибка: GITHUB_TOKEN не установлен"
    echo "Установите: export GITHUB_TOKEN='ghp_...' или добавьте в .env"
    exit 1
fi

if [ -z "$OPENAI_API_KEY" ]; then
    echo "Warning: OPENAI_API_KEY не установлен (будет использован базовый режим)"
fi

# Проверка аргументов
if [ -z "$1" ] || [ -z "$2" ]; then
    echo "Использование: ./run-docker.sh <REPO_URL> <ISSUE_NUMBER>"
    echo ""
    echo "Пример:"
    echo "  ./run-docker.sh https://github.com/user/repo 42"
    exit 1
fi

REPO_URL="$1"
ISSUE_NUMBER="$2"

echo "🐳 Запуск Code Agent в Docker..."
echo "   Репозиторий: $REPO_URL"
echo "   Issue: #$ISSUE_NUMBER"
echo ""

# Сборка образа
echo "Сборка Docker образа..."
docker build -t code-agent:latest .

# Запуск контейнера
echo "  Запуск контейнера..."
docker run --rm \
    -e GITHUB_TOKEN="$GITHUB_TOKEN" \
    -e OPENAI_API_KEY="$OPENAI_API_KEY" \
    -e OPENAI_BASE_URL="${OPENAI_BASE_URL}" \
    -e OPENAI_MODEL="${OPENAI_MODEL}" \
    code-agent:latest \
    --repo "$REPO_URL" \
    --issue "$ISSUE_NUMBER"

echo "Готово!"
