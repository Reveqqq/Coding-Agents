import argparse
import os
from code_agent.agent import run_agent

def main():
    parser = argparse.ArgumentParser(description="AI Code Agent - автоматическое решение Issues")
    parser.add_argument("--repo", required=True, help="URL репозитория (https://github.com/user/repo)")
    parser.add_argument("--issue", type=int, required=True, help="Номер Issue")
    parser.add_argument("--token", help="GitHub token (или GITHUB_TOKEN env var)")
    parser.add_argument("--openai-key", help="OpenAI API key (или OPENAI_API_KEY env var)")
    parser.add_argument("--openai-base-url", help="OpenAI Base url (или OPENAI_BASE_URL env var)")
    parser.add_argument("--openai-model", help="OpenAI model (или OPENAI_MODEL env var)")
    
    args = parser.parse_args()

    # Проверяем токены
    if args.token:
        os.environ["GITHUB_TOKEN"] = args.token
    
    if not os.environ.get("GITHUB_TOKEN"):
        raise ValueError("Требуется GITHUB_TOKEN (передайте --token или установите env var)")
    
    if args.openai_key:
        os.environ["OPENAI_API_KEY"] = args.openai_key
    
    if not os.environ.get("OPENAI_API_KEY"):
        print("Warning: OPENAI_API_KEY не установлен - будет использован базовый режим gpt-4o-mini")

    if args.openai_base_url:
        os.environ["OPENAI_BASE_URL"] = args.openai_key

    if not os.environ.get("OPENAI_BASE_URL"):
        raise ValueError("Требуется OPENAI_BASE_URL (передайте --openai-base-url или установите env var)")
    
    if args.openai_model:
        os.environ["OPENAI_MODEL"] = args.openai_key

    if not os.environ.get("OPENAI_MODEL"):
        raise ValueError("Требуется OPENAI_MODEL (передайте --openai-model или установите env var)")

    

    print(f"   Code Agent starting...")
    print(f"   Repo: {args.repo}")
    print(f"   Issue: #{args.issue}")
    
    run_agent(repo_url=args.repo, issue_number=args.issue)

if __name__ == "__main__":
    main()
