#!/usr/bin/env python3
"""
AI Reviewer Agent - запускается в GitHub Actions в форке проекта
Анализирует PR и выносит решение
"""
import os
import json
import re
from github import Github

# Проверяем доступность LLM
HAS_LLM = False
if os.environ.get("OPENAI_API_KEY"):
    try:
        from langchain_openai import ChatOpenAI
        HAS_LLM = True
    except ImportError:
        print("[Reviewer] Warning: langchain_openai not installed, using basic mode")
        HAS_LLM = False


def get_llm():
    """Создаёт LLM клиент ChatOpenAI"""
    return ChatOpenAI(
        model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        api_key=os.environ.get("OPENAI_API_KEY"),
        base_url=os.environ.get("OPENAI_BASE_URL")
    )

def extract_json(text: str) -> dict:
    """Извлекает JSON из ответа LLM даже если он в ```json блоке"""
    text = text.strip()

    # убираем markdown блоки
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n", "", text)
        text = text.rstrip("`").strip()

    # пробуем найти JSON внутри текста
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        text = match.group(0)

    return json.loads(text)

def generate_review_comment(diff: str, issue_body: str) -> dict:
    """Генерирует review комментарий с анализом PR через LangChain ChatOpenAI"""
    if not HAS_LLM:
        return {"summary": "Basic review (LLM not available)", "issues": [], "decision": "COMMENT"}
    
    llm = get_llm()
    
    prompt = (
        "Ты - code reviewer для GitHub.\n\n"
        "Issue была:\n"
        f"{issue_body}\n\n"
        "Изменения в PR (diff):\n"
        f"{diff}\n\n"
        "Дай краткую оценку в JSON формате:\n"
        "Верни ТОЛЬКО чистый JSON. "
        "НЕ используй markdown, НЕ используй ```json блоки.\n\n"
        "{\n  \"summary\": \"1-2 предложения об изменениях\",\n  \"issues\": [],\n  \"decision\": \"APPROVE\" or \"REQUEST_CHANGES\"\n}"
    )

    try:
        response = llm.invoke(prompt)
        text = response.content.strip()
        return extract_json(text)
    except Exception as e:
        print(f"[Reviewer] LLM error: {e}")
        return {"summary": str(text), "issues": [], "decision": "COMMENT"}

def get_ci_conclusion_from_event(event: dict) -> str:
    """
    Возвращает результат CI из workflow_run payload
    """
    if "workflow_run" in event:
        return event["workflow_run"].get("conclusion", "unknown")

    return "unknown"


def get_pr_info():
    """Получает информацию о PR из GitHub Actions события"""
    token = os.environ.get("GITHUB_TOKEN")
    repo_name = os.environ.get("GITHUB_REPOSITORY")
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    event_name = os.environ.get("GITHUB_EVENT_NAME")

    if not event_path or not os.path.exists(event_path):
        raise ValueError("GITHUB_EVENT_PATH не установлен или не существует")

    with open(event_path, "r") as f:
        event = json.load(f)

    gh = Github(token)
    repo = gh.get_repo(repo_name)
    if "pull_request" in event:
        pr_number = event["pull_request"]["number"]
        pr = repo.get_pull(pr_number)
        return repo, pr, event
    # берём SHA коммита и ищем PR
    sha = None

    if "workflow_run" in event:
        sha = event["workflow_run"]["head_sha"]
    elif "after" in event:
        sha = event["after"]

    if not sha:
        raise ValueError("Не удалось определить SHA коммита")

    pulls = repo.get_pulls(state="open")
    for pr in pulls:
        if pr.head.sha == sha:
            return repo, pr, event

    raise ValueError("PR для данного commit SHA не найден")

def get_issue_body(repo, pr):
    """Получает тело Issue, которое закрывает этот PR"""
    # Ищем Closes #123 в описании PR
    match = re.search(r'Closes\s+#(\d+)', pr.body or "")
    if match:
        issue_num = int(match.group(1))
        try:
            issue = repo.get_issue(issue_num)
            return issue.body
        except:
            pass
    return pr.body or "No issue found"

def get_pr_diff(pr):
    """Получает diff всех файлов в PR"""
    diff_parts = []
    for file in pr.get_files():
        diff_parts.append(f"\n### {file.filename}")
        diff_parts.append(f"Status: {file.status}")
        if file.patch:
            diff_parts.append(f"```diff\n{file.patch}\n```")
        else:
            diff_parts.append("(binary or no changes)")
    return "\n".join(diff_parts)

def generate_review(repo, pr, event):
    """Генерирует review комментарий"""

    ci_conclusion = get_ci_conclusion_from_event(event)

    # LLM анализ
    if HAS_LLM:
        issue_body = get_issue_body(repo, pr)
        diff = get_pr_diff(pr)

        try:
            result = generate_review_comment(diff, issue_body)
            summary = result.get("summary", "")
            issues = result.get("issues", [])
            decision = result.get("decision", "COMMENT")
        except Exception as e:
            summary = f"Error analyzing with LLM: {e}"
            issues = []
            decision = "COMMENT"
    else:
        summary = "PR successfully analyzed by AI Reviewer"
        issues = []
        decision = "COMMENT"

    # CI decision override
    if ci_conclusion in ["queued", "in_progress", None]:
        decision = "COMMENT"
        summary = "CI ещё не завершён. Ревью будет обновлено после завершения CI."
    elif ci_conclusion != "success":
        decision = "REQUEST_CHANGES"
        summary = (
            f"CI failed (`{ci_conclusion}`).\n\n"
            "Исправь ошибки тестов / линтера перед повторным ревью."
        )

    # Comment 
    comment_lines = [
        "## 🤖 AI Reviewer Report",
        "",
        f"**Summary:** {summary}",
        "",
        f"### CI Status: `{ci_conclusion.upper()}`",
        ""
    ]

    if issues:
        comment_lines.append("### Issues Found:")
        for issue in issues:
            comment_lines.append(f"- {issue}")
        comment_lines.append("")

    comment_lines.extend([
        f"### Decision: `{decision}`",
        "_Review performed by AI Code Reviewer_"
    ])

    return "\n".join(comment_lines), decision


def main():
    try:
        repo, pr, event = get_pr_info()
        pr_number = pr.number
        
        print(f"[Reviewer] Анализирую PR #{pr_number}: {pr.title}")
        
        # Генерируем review
        comment_body, decision = generate_review(repo, pr, event)    
        
        # Пытаемся создать официальный review
        event_map = {
            "APPROVE": "APPROVE",
            "REQUEST_CHANGES": "REQUEST_CHANGES",
            "COMMENT": "COMMENT"
        }
        
        try:
            pr.create_review(
                body=comment_body,
                event=event_map.get(decision, "COMMENT")
            )
            print(f"[Reviewer] Review создан с решением: {decision}")
        except Exception as e:
            print(f"[Reviewer] Review не создан (fallback на комментарий): {e}")

    except Exception as e:
        print(f"[Reviewer] ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

if __name__ == "__main__":
    main()