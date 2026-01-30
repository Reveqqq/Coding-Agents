import subprocess
import tempfile
import shutil
import os
from pathlib import Path
from urllib.parse import urlparse, urlunparse

class Workspace:
    def __init__(self, repo_url: str):
        self.repo_url = repo_url
        self.dir = Path(tempfile.mkdtemp())
        self.git_config_done = False
        self.github_token = os.environ.get("GITHUB_TOKEN")

    def clone(self):
        """Клонирует репозиторий"""
        clone_url = self._get_authenticated_url(self.repo_url)
        subprocess.run(["git", "clone", clone_url, "."], cwd=self.dir, check=True)
        self._configure_git()

    def _get_authenticated_url(self, url: str) -> str:
        """Добавляет token в URL для HTTPS клонирования"""
        if not self.github_token or not url.startswith("https://"):
            return url
        
        # Парсим URL
        parsed = urlparse(url)
        # Добавляем token в netloc
        netloc_with_auth = f"x-access-token:{self.github_token}@{parsed.netloc}"
        # Собираем новый URL
        authenticated_url = urlunparse((
            parsed.scheme,
            netloc_with_auth,
            parsed.path,
            parsed.params,
            parsed.query,
            parsed.fragment
        ))
        return authenticated_url

    def _configure_git(self):
        """Конфигурирует git для коммитов и пушей"""
        if self.git_config_done:
            return
        
        subprocess.run(
            ["git", "config", "user.email", "ai-agent@example.com"],
            cwd=self.dir,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "AI Code Agent"],
            cwd=self.dir,
            check=True,
        )
        
        # Настройка origin URL с token если есть
        if self.github_token:
            authenticated_url = self._get_authenticated_url(self.repo_url)
            subprocess.run(
                ["git", "remote", "set-url", "origin", authenticated_url],
                cwd=self.dir,
                check=True,
            )
        
        self.git_config_done = True

    def checkout_branch(self, branch):
        """Переключается на ветку, создаёт если не существует"""
        # Сначала пытаемся переключиться на существующую
        result = subprocess.run(
            ["git", "checkout", branch], 
            cwd=self.dir,
            capture_output=True
        )
        if result.returncode != 0:
            # Если не существует — создаём
            subprocess.run(
                ["git", "checkout", "-b", branch], 
                cwd=self.dir, 
                check=True
            )

    def commit_all(self, message):
        """Коммитит все изменения"""
        subprocess.run(["git", "add", "."], cwd=self.dir, check=True)
        try:
            subprocess.run(["git", "commit", "-m", message], cwd=self.dir, check=True)
        except:
            pass  # ничего не изменилось

    def push(self, branch):
        """Пушит ветку в origin"""
        subprocess.run(
            ["git", "push", "-u", "origin", branch],
            cwd=self.dir,
            check=True,
        )

    def get_files_in_dir(self, pattern: str = "**/*"):
        """Получает список файлов в директории"""
        return list(self.dir.glob(pattern))

    def cleanup(self):
        """Удаляет временную директорию"""
        shutil.rmtree(self.dir, ignore_errors=True)
