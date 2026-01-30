from code_agent.github import (
    get_repo, get_issue, create_pr, get_pr, 
    get_review_status, get_ci_status, wait_for_ci
)
from code_agent.workspace import Workspace
from code_agent.llm import analyze_issue, generate_code_fix
from code_agent.file_editor import get_project_context, apply_change
import re

MAX_RETRIES = 3  # Макс. попыток исправления ошибок

def run_agent(repo_url: str, issue_number: int):
    """Запускает Code Agent для решения Issue"""
    repo = get_repo(repo_url)
    issue = get_issue(repo, issue_number)

    branch = f"issue-{issue_number}"

    ws = Workspace(repo_url)
    ws.clone()
    ws.checkout_branch(branch)

    print(f"[Agent] Анализирую Issue #{issue_number}: {issue.title}")
    
    # Собираем контекст проекта
    project_context = get_project_context(ws.dir)
    
    # Анализируем Issue и получаем план
    plan = analyze_issue(issue.body, project_context)
    print(f"[Agent] План:\n{plan}")
    
    # Извлекаем пути файлов из плана
    files_to_edit = extract_files_from_plan(plan, ws.dir)
    print(f"[Agent] Нужно отредактировать файлы: {files_to_edit}")
    
    # Генерируем исправления для каждого файла
    for file_path in files_to_edit:
        rel_path = file_path.relative_to(ws.dir)
        if file_path.exists():
            old_content = file_path.read_text()
        else:
            old_content = ""
        
        new_content = generate_code_fix(plan, str(rel_path), old_content)
        apply_change(file_path, new_content)
        print(f"[Agent] Обновлён: {rel_path}")

    # Коммитим изменения
    ws.commit_all(f"Fix: #{issue_number} - {issue.title}")
    ws.push(branch)

    # Создаём PR
    pr = create_pr(
        repo,
        branch=branch,
        title=f"[Agent] Fix: {issue.title}",
        body=f"Closes #{issue_number}\n\n## Plan\n{plan}",
    )

    print(f"[Agent] PR создан: {pr.html_url}")

    # Основной цикл: CI + Review + Исправления
    pr = run_review_and_fix_cycle(repo, pr, branch, plan, ws, issue_number)

    ws.cleanup()
    return pr


def run_review_and_fix_cycle(repo, pr, branch, plan, ws, issue_number):
    """
    Запускает цикл: CI → Review → Исправления → Новый коммит
    """
    import time
    
    retry_count = 0
    
    while retry_count < MAX_RETRIES:
        print(f"\n[Cycle] Итерация {retry_count + 1}/{MAX_RETRIES}")
        
        # Ждём завершения CI (только если это первая итерация или после нашего коммита)
        print("[Cycle] Ожидаю завершения CI...")
        ci_status = wait_for_ci(pr, timeout=600)  # 10 минут timeout
        print(f"[CI] Статус: {ci_status}")
        
        if ci_status == "timeout":
            print("[CI] Timeout при ожидании CI результатов")
            return pr
        
        # Ждём Review от Reviewer Agent (с polling)
        print("[Cycle] Ожидаю Review от Reviewer Agent...")
        review_status = wait_for_review(pr, timeout=300, poll_interval=5)
        print(f"[Review] Статус: {review_status}")
        
        # Анализируем результаты
        if review_status == "APPROVED":
            print("[Success] PR одобрен!")
            return pr
        
        if review_status == "CHANGES_REQUESTED":
            print("[Review] Reviewer запросил изменения")
            current_pr = get_pr(repo, branch)
            if current_pr:
                review_list = list(current_pr.get_reviews())
                if review_list:
                    review = review_list[-1]
                    feedback = review.body
                    print(f"[Review] Комментарий:\n{feedback}")
                    
                    # Генерируем fix на основе feedback
                    fix_plan = plan + f"\n\n## Feedback от reviewer:\n{feedback}"
                    
                    if not apply_review_feedback(fix_plan, ws, branch):
                        print("[Error] Не удалось применить исправления")
                        retry_count += 1
                        if retry_count < MAX_RETRIES:
                            continue
                        else:
                            return pr
                    
                    print("[Agent] Исправления закоммичены и запушены")
                    retry_count += 1
                    
                    # Обновляем PR объект и продолжаем цикл
                    pr = get_pr(repo, branch)
                    if pr:
                        continue
        
        if review_status == "timeout":
            print("[Review] Timeout при ожидании Review (Reviewer Agent не ответил)")
            print("[Warning] Завершение с текущим статусом")
            return pr
        
        # Неожиданный статус
        print(f"[Cycle] Неожиданный статус: {review_status}")
        return pr
    
    print(f"[Warning] Достигнут лимит попыток ({MAX_RETRIES})")
    return pr


def wait_for_review(pr, timeout: int = 300, poll_interval: int = 5):
    """
    Ждёт Review от Reviewer Agent
    Возвращает: "APPROVED", "CHANGES_REQUESTED", "COMMENTED", "timeout"
    """
    import time
    
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        status = get_review_status(pr)
        
        if status in ["APPROVED", "CHANGES_REQUESTED", "COMMENTED"]:
            return status
        
        print(f"[Review] Ожидаю Review... ({int(time.time() - start_time)}s)")
        time.sleep(poll_interval)
    
    return "timeout"


def apply_review_feedback(fix_plan: str, ws: Workspace, branch: str) -> bool:
    """
    Применяет исправления на основе feedback
    Возвращает True если успешно закоммичено и запушено
    """
    try:
        # Клонируем ещё раз или просто обновляем
        ws.checkout_branch(branch)
        
        # Получаем текущие файлы в workspace
        files_to_edit = extract_files_from_plan(fix_plan, ws.dir)
        
        for file_path in files_to_edit:
            rel_path = file_path.relative_to(ws.dir)
            if file_path.exists():
                old_content = file_path.read_text()
            else:
                old_content = ""
            
            new_content = generate_code_fix(fix_plan, str(rel_path), old_content)
            apply_change(file_path, new_content)
            print(f"[Agent] Обновлён (fix): {rel_path}")
        
        # Коммитим и пушим в тот же branch
        ws.commit_all("Fix: Address review feedback and CI issues")
        ws.push(branch)
        
        return True
    except Exception as e:
        print(f"[Error] Ошибка при применении исправлений: {e}")
        return False


def extract_files_from_plan(plan: str, workspace_dir) -> list:
    """Извлекает пути файлов из плана"""
    pattern = r'([a-zA-Z0-9._/\-]+\.[a-zA-Z0-9]+)'
    matches = re.findall(pattern, plan)
    
    files = []
    for match in matches:
        file_path = workspace_dir / match[0]
        if file_path.exists() or not file_path.exists():
            files.append(file_path)
    
    return list(set(files))
