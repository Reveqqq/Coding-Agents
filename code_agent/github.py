import os
import time
from github import Github

def get_client():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise ValueError("GITHUB_TOKEN не установлен")
    return Github(token)

def get_repo(repo_url: str):
    """Получает объект репозитория по URL"""
    name = repo_url.replace("https://github.com/", "").rstrip("/")
    return get_client().get_repo(name)

def get_issue(repo, issue_number: int):
    """Получает Issue по номеру"""
    return repo.get_issue(number=issue_number)

def create_pr(repo, branch, title, body):
    """Создаёт PR"""
    return repo.create_pull(
        title=title,
        body=body,
        head=branch,
        base="main",
    )

def get_pr(repo, branch: str):
    """Получает PR по branch"""
    prs = repo.get_pulls(state="open", head=f"{repo.owner.login}:{branch}")
    for pr in prs:
        if pr.head.ref == branch:
            return pr
    return None

def get_last_review(pr):
    """Получает последний review"""
    reviews = list(pr.get_reviews())
    if reviews:
        return reviews[-1]
    return None

def get_review_status(pr):
    """
    Возвращает статус review:
    - "APPROVED" → готово
    - "CHANGES_REQUESTED" → нужны исправления
    - "PENDING" → ещё не проверено
    - None → нет review
    """
    review = get_last_review(pr)
    if review:
        return review.state
    return None

def get_ci_status(pr):
    """
    Получает статус CI check
    Возвращает:
    - "success"
    - "failure"
    - "pending"
    - None
    """
    commits = list(pr.get_commits())
    if not commits:
        return None
    
    last_commit = commits[-1]
    check_runs = last_commit.get_check_runs()
    
    # Собираем статусы всех check-ов
    statuses = [run.conclusion for run in check_runs if run.conclusion]
    
    if not statuses:
        return "pending"
    
    # Если есть хотя бы один failed — failure
    if "failure" in statuses:
        return "failure"
    
    # Если все success
    if all(s == "success" for s in statuses):
        return "success"
    
    return "pending"

def wait_for_ci(pr, timeout: int = 600, poll_interval: int = 10):
    """
    Ждёт завершения CI
    timeout в секундах (по умолчанию 10 минут)
    poll_interval - интервал проверки в секундах
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        status = get_ci_status(pr)
        if status in ["success", "failure"]:
            return status
        elapsed = int(time.time() - start_time)
        print(f"[CI] Ждём CI... (status={status}, {elapsed}s)")
        time.sleep(poll_interval)
    
    return "timeout"
