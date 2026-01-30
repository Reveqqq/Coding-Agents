import os
from langchain_openai import ChatOpenAI

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")


def get_llm():
    """Создаёт LLM клиент"""
    return ChatOpenAI(
        model=OPENAI_MODEL,
        api_key=OPENAI_API_KEY,
        base_url=OPENAI_BASE_URL
    )


def analyze_issue(issue_body: str, repo_context: str) -> str:
    """Агент Анализирует Issue и генерирует план решения через LangChain"""
    llm = get_llm()
    prompt = (
        "Ты - помощник для решения GitHub Issues в проекте на Vue.js/JavaScript.\n\n"
        f"Issue:\n{issue_body}\n\n"
        f"Контекст проекта:\n{repo_context}\n\n"
        "Создай лаконичный план решения (5-7 пунктов) и укажи какие файлы нужно изменить."
    )

    response = llm.invoke(prompt)
    return response.content.strip()


def generate_code_fix(plan: str, file_path: str, file_content: str) -> str:
    """Генерирует код для исправления указанного файла"""
    llm = get_llm()
    prompt = (
        "Ты - разработчик, который исправляет код в Vue.js проекте.\n\n"
        "План изменений:\n"
        f"{plan}\n\n"
        f"Файл: {file_path}\n"
        "Текущий код:\n"
        f"{file_content}\n\n"
        "Вернись ТОЛЬКО с новым кодом файла, без комментариев и объяснений. Сохрани стиль кодирования проекта."
    )

    response = llm.invoke(prompt)
    return response.content.lstrip("\n")
