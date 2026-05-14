"""
Script para fazer push de prompts otimizados ao LangSmith Prompt Hub.

Este script:
1. Le o prompt otimizado de prompts/bug_to_user_story_v2.yml
2. Valida a estrutura local
3. Faz push publico para o LangSmith Hub
4. Adiciona metadados, tags e descricao
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from utils import (
    load_yaml,
    check_env_vars,
    print_section_header,
    validate_prompt_structure,
)

load_dotenv()

PROMPT_PATH = Path("prompts/bug_to_user_story_v2.yml")
PROMPT_KEY = "bug_to_user_story_v2"
PROMPT_HUB_NAME = "bug_to_user_story_v2"


def build_prompt_name() -> str:
    """Monta o nome do prompt aceitando workspaces sem namespace explicito."""
    username = os.getenv("USERNAME_LANGSMITH_HUB", "").strip()
    return f"{username}/{PROMPT_HUB_NAME}" if username else PROMPT_HUB_NAME


def push_prompt_to_langsmith(prompt_name: str, prompt_data: dict) -> bool:
    """
    Faz push do prompt otimizado para o LangSmith Hub.

    Args:
        prompt_name: Nome versionado no Hub, ex: usuario/bug_to_user_story_v2
        prompt_data: Dados do prompt carregados do YAML

    Returns:
        True se sucesso, False caso contrario
    """
    try:
        chat_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", prompt_data["system_prompt"]),
                ("human", prompt_data.get("user_prompt", "{bug_report}")),
            ]
        )
        chat_prompt.metadata = {
            "version": prompt_data.get("version", "v2"),
            "techniques_applied": prompt_data.get("techniques_applied", []),
            "description": prompt_data.get("description", ""),
        }
        chat_prompt.tags = prompt_data.get("tags", [])

        description = prompt_data.get(
            "description",
            "Prompt otimizado para converter relatos de bugs em User Stories.",
        )
        tags = prompt_data.get("tags", [])
        techniques = ", ".join(prompt_data.get("techniques_applied", []))
        readme = (
            "# Bug to User Story v2\n\n"
            f"{description}\n\n"
            f"Tecnicas aplicadas: {techniques}\n\n"
            "Entrada esperada: bug_report.\n"
            "Saida esperada: User Story em Markdown com criterios de aceitacao testaveis."
        )

        try:
            from langchain import hub as langchain_hub
        except ImportError:
            langchain_hub = None

        if langchain_hub is not None:
            try:
                url = langchain_hub.push(
                    prompt_name,
                    chat_prompt,
                    new_repo_is_public=True,
                    new_repo_description=description,
                )
            except TypeError:
                url = langchain_hub.push(prompt_name, chat_prompt)
        else:
            from langsmith import Client

            url = Client().push_prompt(
                prompt_name,
                object=chat_prompt,
                is_public=True,
                description=description,
                readme=readme,
                tags=tags,
            )

        print(f"Prompt publicado com sucesso: {prompt_name}")
        if url:
            print(f"URL: {url}")
        return True
    except Exception as exc:
        error_msg = str(exc).lower()
        if "nothing to commit" in error_msg:
            print(f"Prompt ja esta atualizado no LangSmith: {prompt_name}")
            return True
        if "tag" in error_msg and "already exists" in error_msg:
            print(f"Prompt publicado, mas a tag de commit ja existia: {prompt_name}")
            return True
        print(f"Erro ao publicar prompt '{prompt_name}': {exc}")
        return False


def validate_prompt(prompt_data: dict) -> tuple[bool, list]:
    """
    Valida estrutura basica do prompt otimizado.

    Args:
        prompt_data: Dados do prompt

    Returns:
        (is_valid, errors) - Tupla com status e lista de erros
    """
    is_valid, errors = validate_prompt_structure(prompt_data)

    if not prompt_data.get("user_prompt", "").strip():
        errors.append("Campo obrigatorio faltando ou vazio: user_prompt")

    combined_prompt = "\n".join(
        [
            prompt_data.get("system_prompt", ""),
            prompt_data.get("user_prompt", ""),
        ]
    )

    if "{bug_report}" not in combined_prompt:
        errors.append("O prompt deve conter a variavel de entrada {bug_report}")

    if "Exemplo" not in combined_prompt and "Entrada" not in combined_prompt:
        errors.append("O prompt deve conter exemplos few-shot de entrada e saida")

    return (is_valid and len(errors) == 0, errors)


def main():
    """Funcao principal."""
    print_section_header("PUSH DE PROMPTS OTIMIZADOS")

    if not check_env_vars(["LANGSMITH_API_KEY"]):
        return 1

    prompt_file = load_yaml(str(PROMPT_PATH))
    if not prompt_file:
        return 1

    prompt_data = prompt_file.get(PROMPT_KEY, prompt_file)

    is_valid, errors = validate_prompt(prompt_data)
    if not is_valid:
        print("Prompt invalido:")
        for error in errors:
            print(f" - {error}")
        return 1

    prompt_name = build_prompt_name()

    return 0 if push_prompt_to_langsmith(prompt_name, prompt_data) else 1


if __name__ == "__main__":
    sys.exit(main())
