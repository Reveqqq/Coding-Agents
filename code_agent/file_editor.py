import os
from pathlib import Path

def get_project_context(workspace_dir: Path) -> str:
    """Собирает контекст проекта для анализа"""
    context_parts = []
    
    # package.json
    pkg = workspace_dir / "package.json"
    if pkg.exists():
        context_parts.append(f"=== package.json ===\n{pkg.read_text()}")
    
    # README
    readme = workspace_dir / "README.md"
    if readme.exists():
        content = readme.read_text()[:1000]  # первые 1000 символов
        context_parts.append(f"=== README ===\n{content}")
    
    return "\n\n".join(context_parts)

def find_files_to_edit(workspace_dir: Path, file_patterns: list) -> list:
    """Находит файлы для редактирования по паттернам"""
    found_files = []
    for pattern in file_patterns:
        for match in workspace_dir.glob(pattern):
            if match.is_file():
                found_files.append(match)
    return found_files

def apply_change(file_path: Path, new_content: str) -> bool:
    """Применяет изменения к файлу"""
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(new_content)
        return True
    except Exception as e:
        print(f"Error writing {file_path}: {e}")
        return False

def get_file_diff(old_content: str, new_content: str) -> str:
    """Генерирует unified diff между версиями"""
    import difflib
    old_lines = old_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)
    diff = difflib.unified_diff(old_lines, new_lines, lineterm='')
    return ''.join(diff)
