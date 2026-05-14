"""
Testes automatizados para validacao de prompts.
"""

import sys
from pathlib import Path

import pytest
import yaml

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils import validate_prompt_structure

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "bug_to_user_story_v2.yml"
PROMPT_KEY = "bug_to_user_story_v2"


def load_prompts(file_path: str):
    """Carrega prompts do arquivo YAML."""
    with open(file_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_optimized_prompt():
    """Carrega o prompt otimizado v2."""
    data = load_prompts(str(PROMPT_PATH))
    assert data is not None, "Arquivo YAML do prompt v2 nao pode estar vazio."
    assert PROMPT_KEY in data, f"Arquivo deve conter a chave raiz '{PROMPT_KEY}'."
    return data[PROMPT_KEY]


def prompt_text(prompt_data: dict) -> str:
    """Une os campos textuais relevantes para as assercoes."""
    parts = [
        prompt_data.get("description", ""),
        prompt_data.get("system_prompt", ""),
        prompt_data.get("user_prompt", ""),
        " ".join(prompt_data.get("techniques_applied", [])),
    ]
    return "\n".join(parts).lower()


class TestPrompts:
    def test_prompt_has_system_prompt(self):
        """Verifica se o campo 'system_prompt' existe e nao esta vazio."""
        prompt_data = load_optimized_prompt()

        is_valid, errors = validate_prompt_structure(prompt_data)

        assert "system_prompt" in prompt_data
        assert prompt_data["system_prompt"].strip()
        assert is_valid, errors

    def test_prompt_has_role_definition(self):
        """Verifica se o prompt define uma persona."""
        text = prompt_text(load_optimized_prompt())

        role_terms = [
            "gerente de produto",
            "product manager",
            "product owner",
            "voce e",
            "você é",
        ]

        assert any(term in text for term in role_terms)

    def test_prompt_mentions_format(self):
        """Verifica se o prompt exige formato Markdown ou User Story padrao."""
        text = prompt_text(load_optimized_prompt())

        assert "markdown" in text
        assert "como um" in text
        assert "eu quero" in text
        assert "para que" in text
        assert "critérios de aceitação" in text or "criterios de aceitacao" in text

    def test_prompt_has_few_shot_examples(self):
        """Verifica se o prompt contem exemplos de entrada/saida."""
        text = prompt_text(load_optimized_prompt())

        assert "few-shot" in text or "few shot" in text
        assert text.count("exemplo") >= 2
        assert "entrada:" in text
        assert "saida:" in text or "saída:" in text

    def test_prompt_no_todos(self):
        """Garante que nao ha marcadores pendentes no texto."""
        text = prompt_text(load_optimized_prompt())

        assert "[todo]" not in text
        assert "todo:" not in text

    def test_minimum_techniques(self):
        """Verifica se pelo menos 2 tecnicas foram listadas no YAML."""
        prompt_data = load_optimized_prompt()
        techniques = prompt_data.get("techniques_applied", [])

        assert isinstance(techniques, list)
        assert len(techniques) >= 2
        assert any("few" in technique.lower() for technique in techniques)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
