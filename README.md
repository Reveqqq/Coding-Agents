# AI Code Agent + Reviewer System

Полностью автоматизированная система для решения GitHub Issues с использованием AI. Система реализует итеративный SDLC-цикл: Code Agent создаёт PR, Reviewer Agent проверяет результаты и CI, а Code Agent автоматически исправляет ошибки по feedback.

## Возможности

- **Автоматическое решение Issues** — Code Agent анализирует Issue и генерирует решение
- **AI Review** — Reviewer Agent проверяет качество кода, соответствие Issue и результаты CI
- **Итеративное исправление** — Автоматический retry-цикл: CI failure → исправления → новый commit
- **Один PR, несколько коммитов** — Чистая история без PR-спама
- **GitHub Actions интеграция** — Автоматический запуск всех шагов
- **LLM-powered** — Использует Groq / OpenAI для анализа и генерации кода

## Быстрый старт

### 1. Клонируем репозиторий

```bash
git clone https://github.com/albertzagibin/MegaSchool.git
cd MegaSchool
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Настраиваем переменные окружения

Создаём файл `.env`:

```bash
# GitHub API
GITHUB_TOKEN=ghp_xxxxxxxxxxxx

# LLM (Groq или OpenAI)
OPENAI_API_KEY=gsk_xxxxx...
OPENAI_BASE_URL=https://api.groq.com/openai/v1
OPENAI_MODEL=openai/gpt-oss-120b

# Docker (опционально)
DOCKER_IMAGE=code-agent:latest
```

Или экспортируем в shell:

```bash
export GITHUB_TOKEN="ghp_..."
export OPENAI_API_KEY="gsk_..."
export OPENAI_BASE_URL="https://api.groq.com/openai/v1"
export OPENAI_MODEL="openai/gpt-oss-120b"
```

### 3. Настройка Reviewer Agent в репозитории

В репозитории проекта, где будут создаваться PR:

1. скопировать scripts/reviewer.py
2. добавить workflow .github/workflows/pr-reviewer.yml
3. задать secrets: OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL

Подробные шаги см. раздел «Установка Reviewer Agent в форке» ниже.

### 4. Запускаем Code Agent

**Через Docker:**
```bash
chmod +x run-docker.sh
./run-docker.sh https://github.com/Reveqqq/weektodo 1
```

**Запуск локально:**
```bash
python -m code_agent.cli --repo https://github.com/user/repo --issue 42
```
**Для локального запсука необходимо прописать все экспорты в bash**

## Архитектура

```
GitHub Issue
  ↓
Code Agent создаёт PR (issue-N branch)
  ↓
CI запускается
  ↓
Reviewer Agent проверяет результаты + CI статус
  ↓
Вердикт: APPROVED или REQUEST_CHANGES
  ↓
Если REQUEST_CHANGES:
  Code Agent читает feedback
  ↓
  Генерирует исправления
  ↓
  Новый commit в ТОТ ЖЕ branch
  ↓
  Git push в issue-N branch
  ↓
  CI автоматически триггерится
  ↓
  Reviewer снова проверяет
  ↓
  REPEAT пока не APPROVED или MAX_RETRIES
```

## Компоненты

### Code Agent

**Где:** `code_agent/` папка  
**Язык:** Python + LangChain  

**Что делает:**
1. Читает GitHub Issue по номеру
2. Клонирует репозиторий во временную директорию
3. Анализирует Issue и контекст проекта через LLM
4. Генерирует план решения
5. Извлекает файлы для изменения из плана
6. Для каждого файла:
   - Читает текущее содержимое
   - Генерирует исправления через LLM
   - Применяет изменения
7. Коммитит все изменения
8. Пушит ветку `issue-N` в origin
9. Создаёт Pull Request
10. **Ожидает** Review и CI результатов
11. Если REQUEST_CHANGES — читает feedback и повторяет

**Файлы:**
- `agent.py` — основной цикл, логика исправлений
- `llm.py` — клиент LLM 
- `file_editor.py` — работа с файлами, парсинг проектов
- `github.py` — GitHub API (PyGithub wrapper)
- `workspace.py` — управление git и temp директориями
- `cli.py` — CLI интерфейс

### Reviewer Agent

**Где:** `reviewer.py` в **форке проекта** (`.github/workflows/pr-reviewer.yml`)  
**Язык:** Python + LangChain  

**Что делает:**
1. Получает информацию о PR из GitHub webhook
2. Читает все изменённые файлы (diff)
3. Извлекает Issue из PR description (`Closes #N`)
4. Анализирует diff и Issue через LLM
5. Читает статус CI checks
6. Генерирует review report с анализом
7. Выносит вердикт:
   - `APPROVED` — всё хорошо
   - `REQUEST_CHANGES` — найдены проблемы
   - `COMMENTED` — только замечание

**Код находится в форке по пути:** `scripts/reviewer.py`

---

## Установка Reviewer Agent в форке

Reviewer Agent должен быть установлен в **форке проекта**, где создаются PR'ы.

### Шаг 1: Скопировать `reviewer.py` в форк

Скопируем скрипт в форк:

```bash
# В вашем форке (например, https://github.com/Reveqqq/weektodo)
mkdir -p scripts
cp reviewer.py scripts/reviewer.py
git add scripts/reviewer.py
git commit -m "Add AI Reviewer Agent"
git push origin main
```

### Шаг 2: Создать GitHub Actions workflow

Создаём файл `.github/workflows/pr-reviewer.yml` в форке:

```yaml
name: AI Reviewer

on:
  workflow_run:
    workflows: ["PR CI"]
    types: [completed]

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install deps
        run: pip install PyGithub openai langchain-openai

      - name: Run reviewer
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          OPENAI_BASE_URL: ${{ secrets.OPENAI_BASE_URL }}
          OPENAI_MODEL: ${{ secrets.OPENAI_MODEL }}
        run: python scripts/reviewer.py
```

### Шаг 3: Добавить secrets в форк

В форке перейти: **Settings → Secrets and variables → Actions**

Добавить secrets:
- `OPENAI_API_KEY` — ключ API LLM
- `OPENAI_BASE_URL` — URL базовой точки
- `OPENAI_MODEL` — модель 

`GITHUB_TOKEN` автоматически предоставляется GitHub Actions.

### Шаг 4: Коммитим workflow

```bash
git add .github/workflows/pr-reviewer.yml
git commit -m "Add AI Reviewer workflow"
git push origin main
```

---

## Использование

### Полный workflow

```bash
# 1. Создаём Issue в форке
# Открываем: https://github.com/Reveqqq/weektodo/issues/new
# Название: "Добавить тёмный режим"
# Описание: "Нужно реализовать toggle для переключения темы..."

# 2. Запускаем Code Agent через Docker
chmod +x run-docker.sh
./run-docker.sh https://github.com/Reveqqq/weektodo 1

# 3. Code Agent создаст PR
# https://github.com/Reveqqq/weektodo/pull/17

# 4. GitHub Actions запускает:
#    - CI workflow (тесты, линт)
#    - Reviewer Agent workflow
#
# 5. Результаты видны в PR:
#    - CI checks ✅ или ❌
#    - Review comment от Reviewer Agent
#    - Decision: APPROVED или REQUEST_CHANGES

# 6. Если REQUEST_CHANGES:
#    - Code Agent читает feedback
#    - Генерирует исправления
#    - Пушит новый commit в issue-42 branch
#    - CI снова запускается
#    - Reviewer снова проверяет
#    - Повтор до APPROVED (макс. 3 попытки)
```

### Примеры команд

**Решить конкретный Issue:**
```bash
python -m code_agent.cli --repo https://github.com/user/repo --issue 42
```

**Через Docker (если нет Python локально):**
```bash
./run-docker.sh https://github.com/user/repo 42
```
Где 42 - ISSUE_NUMBER

---

## Конфигурация

### Code Agent параметры

**В `agent.py`:**
```python
MAX_RETRIES = 3  # макс. попыток исправления
```

**В `github.py`:**
```python
wait_for_ci(pr, timeout=600, poll_interval=10)  # 10 минут ожидания CI
wait_for_review(pr, timeout=300, poll_interval=5)  # 5 минут ожидания Review
```

---

## Требования

### Python пакеты

```
PyGithub>=2.1.1
langchain>=0.1.0
langchain-openai>=0.0.5
```

**Установка:**
```bash
pip install -r requirements.txt
```

### Переменные окружения

| Переменная | Где | Обязательно | Значение |
|------------|-----|-----------|---------|
| `GITHUB_TOKEN` | Code Agent, Reviewer | Да | GitHub PAT (Settings → Developer settings) |
| `OPENAI_API_KEY` | Code Agent, Reviewer | Да | API ключ Groq или OpenAI |
| `OPENAI_BASE_URL` | Code Agent, Reviewer | Да | URL API (Groq или OpenAI) |
| `OPENAI_MODEL` | Code Agent, Reviewer | Да | Название модели |
| `GITHUB_REPOSITORY` | Reviewer (Actions) | Да | Автоматически: `owner/repo` |
| `GITHUB_EVENT_PATH` | Reviewer (Actions) | Да | Автоматически: путь к event.json |

---

## Возможности и ограничения

### Поддерживается

- Анализ любых типов Issues
- Поддержка множества языков
- Автоматический retry при CI failure
- Чтение и парсинг Review feedback
- Итеративное улучшение кода
- Логирование всех этапов

### Текущие ограничения

- Max retries = 3 (фиксировано)
- CI timeout = 10 минут
- Review timeout = 5 минут
- Feedback парсится как plain text
- Сообщения коммитов генерируются LLM но могут быть generic

### Возможные улучшения

1. **Структурированный парсинг CI ошибок** — скачивать и парсить CI logs
2. **Exponential backoff** — умные интервалы между retry
3. **Сохранение состояния** — продолжать после перерыва
4. **Умные сообщения коммитов** — "Fix: Add error handling (attempt 2/3)"
5. **Per-file feedback** — комментарии к конкретным строкам
6. **Автоматический merge** — merge PR после APPROVED
7. **Тестирование Code Agent** - Покрытие кода тестами
8. **Langfuse** - настройка Langfuse для ведения трейсингов и оценки качества LLM

---

## Отладка

### Логи

Оба агента выводят логи с префиксом:
- `[Agent]` — Code Agent
- `[Reviewer]` — Reviewer Agent
- `[Cycle]` — итерационный цикл
- `[CI]` — статус CI
- `[Review]` — статус Review

### Решение проблем

**"GITHUB_TOKEN не установлен"**
```bash
# Проверь .env файл или переменные окружения
echo $GITHUB_TOKEN
```

**"No commits between main and issue-N"**
- Issue не требует изменений (LLM не нашёл файлы)
- Regex не распознал файлы в плане → добавить расширения в `extract_files_from_plan()`

**"CI завис на pending"**
- Увеличить timeout в `wait_for_ci(pr, timeout=900)`
- Проверить, запускается ли CI в форке

**"Reviewer не запустился"**
- Проверить workflow в `.github/workflows/pr-reviewer.yml`
- Убедиться, что secrets установлены в форке
- Смотреть Actions tab в форке

---

## FAQ

**Q: Должен ли Reviewer быть в форке?**  
A: Да. Reviewer читает webhook события форка и публикует комментарии в PR форка.

**Q: Может ли Code Agent быть в форке?**  
A: Нет, Code Agent работает локально. Он просто создаёт PR через GitHub API.

**Q: Почему PR создаётся, а не коммитится в main?**  
A: Для безопасности! Код проходит через CI и Review перед merge.

**Q: Что если CI вечно падает?**  
A: После 3 попыток (MAX_RETRIES) агент останавливается. Нужна ручная диагностика.

**Q: Могу ли я изменить LLM модель?**  
A: Да, установи в `.env`:
```
OPENAI_MODEL=gpt-4-turbo
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1
```

**Q: Как отключить retry?**  
A: Измени `MAX_RETRIES = 0` в `agent.py`

---

Проект создан в учебных целях в рамках МегаШколы.
