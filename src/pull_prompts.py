"""
Script para fazer pull de prompts do LangSmith Prompt Hub.

Este script:
1. Conecta ao LangSmith usando credenciais do .env
2. Faz pull do prompt inicial publicado no Hub
3. Salva localmente em prompts/bug_to_user_story_v1.yml
"""

import sys
from pathlib import Path
from dotenv import load_dotenv
from utils import save_yaml, check_env_vars, print_section_header

load_dotenv()

SOURCE_PROMPT_NAME = "leonanluppi/bug_to_user_story_v1"
OUTPUT_PATH = Path("prompts/bug_to_user_story_v1.yml")


def _get_template_from_message(message) -> str:
    """Extrai o texto de uma mensagem de prompt LangChain."""
    prompt = getattr(message, "prompt", None)

    if prompt is not None and hasattr(prompt, "template"):
        return prompt.template

    if hasattr(message, "template"):
        return message.template

    if hasattr(message, "content"):
        return message.content

    return str(message)


def _pull_prompt(prompt_name: str):
    """Faz pull usando a API disponivel na versao instalada."""
    try:
        from langchain import hub as langchain_hub
    except ImportError:
        langchain_hub = None

    if langchain_hub is not None:
        return langchain_hub.pull(prompt_name)

    from langsmith import Client

    return Client().pull_prompt(prompt_name)


def _serialize_prompt(prompt_name: str, prompt) -> dict:
    """Converte um prompt LangChain em YAML simples usado pelo projeto."""
    prompt_key = prompt_name.split("/")[-1]
    messages = getattr(prompt, "messages", [])
    metadata = getattr(prompt, "metadata", None) or {}
    tags = getattr(prompt, "tags", None) or metadata.get("tags", [])

    system_prompt = ""
    user_prompt = "{bug_report}"

    if messages:
        for message in messages:
            class_name = message.__class__.__name__.lower()
            template = _get_template_from_message(message).strip()

            if "system" in class_name:
                system_prompt = template
            elif "human" in class_name or "user" in class_name:
                user_prompt = template
    elif hasattr(prompt, "template"):
        system_prompt = prompt.template.strip()

    return {
        prompt_key: {
            "description": metadata.get(
                "description",
                "Prompt inicial para converter relatos de bugs em User Stories.",
            ),
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "version": "v1",
            "source": prompt_name,
            "tags": tags or ["bug-analysis", "user-story", "product-management"],
        }
    }


def pull_prompts_from_langsmith() -> bool:
    """Faz pull do prompt v1 e salva em YAML."""
    print(f"Puxando prompt do LangSmith Hub: {SOURCE_PROMPT_NAME}")
    prompt = _pull_prompt(SOURCE_PROMPT_NAME)

    prompt_data = _serialize_prompt(SOURCE_PROMPT_NAME, prompt)

    if save_yaml(prompt_data, str(OUTPUT_PATH)):
        print(f"Prompt salvo em: {OUTPUT_PATH}")
        return True

    return False


def main():
    """Funcao principal."""
    print_section_header("PULL DE PROMPTS DO LANGSMITH")

    if not check_env_vars(["LANGSMITH_API_KEY"]):
        return 1

    try:
        return 0 if pull_prompts_from_langsmith() else 1
    except Exception as exc:
        print(f"Erro ao fazer pull do prompt: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
