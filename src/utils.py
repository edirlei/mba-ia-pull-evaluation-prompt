"""
Funções auxiliares para o projeto de otimização de prompts.
"""

import os
import sys
import time
import yaml
import json
from typing import Dict, Any, Optional, Callable, TypeVar
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

T = TypeVar("T")
_LAST_LLM_CALL_TS = 0.0

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def load_yaml(file_path: str) -> Optional[Dict[str, Any]]:
    """
    Carrega arquivo YAML.

    Args:
        file_path: Caminho do arquivo YAML

    Returns:
        Dicionário com conteúdo do YAML ou None se erro
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return data
    except FileNotFoundError:
        print(f"❌ Arquivo não encontrado: {file_path}")
        return None
    except yaml.YAMLError as e:
        print(f"❌ Erro ao parsear YAML: {e}")
        return None
    except Exception as e:
        print(f"❌ Erro ao carregar arquivo: {e}")
        return None


def save_yaml(data: Dict[str, Any], file_path: str) -> bool:
    """
    Salva dados em arquivo YAML.

    Args:
        data: Dados para salvar
        file_path: Caminho do arquivo de saída

    Returns:
        True se sucesso, False caso contrário
    """
    try:
        output_file = Path(file_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True, sort_keys=False, indent=2)

        return True
    except Exception as e:
        print(f"❌ Erro ao salvar arquivo: {e}")
        return False


def check_env_vars(required_vars: list) -> bool:
    """
    Verifica se variáveis de ambiente obrigatórias estão configuradas.

    Args:
        required_vars: Lista de variáveis obrigatórias

    Returns:
        True se todas configuradas, False caso contrário
    """
    missing_vars = []

    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        print("❌ Variáveis de ambiente faltando:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nConfigure-as no arquivo .env antes de continuar.")
        return False

    return True


def format_score(score: float, threshold: float = 0.9) -> str:
    """
    Formata score com indicador visual de aprovação.

    Args:
        score: Score entre 0.0 e 1.0
        threshold: Limite mínimo para aprovação

    Returns:
        String formatada com score e símbolo
    """
    symbol = "✓" if score >= threshold else "✗"
    return f"{score:.2f} {symbol}"


def print_section_header(title: str, char: str = "=", width: int = 50):
    """
    Imprime cabeçalho de seção formatado.

    Args:
        title: Título da seção
        char: Caractere para a linha
        width: Largura da linha
    """
    print("\n" + char * width)
    print(title)
    print(char * width + "\n")


def validate_prompt_structure(prompt_data: Dict[str, Any]) -> tuple[bool, list]:
    """
    Valida estrutura básica de um prompt.

    Args:
        prompt_data: Dados do prompt

    Returns:
        (is_valid, errors) - Tupla com status e lista de erros
    """
    errors = []

    required_fields = ['description', 'system_prompt', 'version']
    for field in required_fields:
        if field not in prompt_data:
            errors.append(f"Campo obrigatório faltando: {field}")

    system_prompt = prompt_data.get('system_prompt', '').strip()
    if not system_prompt:
        errors.append("system_prompt está vazio")

    if 'TODO' in system_prompt:
        errors.append("system_prompt ainda contém TODOs")

    techniques = prompt_data.get('techniques_applied', [])
    if len(techniques) < 2:
        errors.append(f"Mínimo de 2 técnicas requeridas, encontradas: {len(techniques)}")

    return (len(errors) == 0, errors)


def extract_json_from_response(response_text: str) -> Optional[Dict[str, Any]]:
    """
    Extrai JSON de uma resposta de LLM que pode conter texto adicional.

    Args:
        response_text: Texto da resposta do LLM

    Returns:
        Dicionário extraído ou None se não encontrar JSON válido
    """
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        start = response_text.find('{')
        end = response_text.rfind('}') + 1

        if start != -1 and end > start:
            try:
                json_str = response_text[start:end]
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass

    return None


def get_llm(model: Optional[str] = None, temperature: float = 0.0):
    """
    Retorna uma instância de LLM configurada baseada no provider.

    Args:
        model: Nome do modelo (opcional, usa LLM_MODEL do .env por padrão)
        temperature: Temperatura para geração (padrão: 0.0 para determinístico)

    Returns:
        Instância de ChatOpenAI ou ChatGoogleGenerativeAI

    Raises:
        ValueError: Se provider não for suportado ou API key não configurada
    """
    provider = os.getenv('LLM_PROVIDER', 'openai').lower()
    model_name = model or os.getenv('LLM_MODEL', 'gpt-4o-mini')

    if provider == 'openai':
        from langchain_openai import ChatOpenAI

        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY não configurada no .env\n"
                "Obtenha uma chave em: https://platform.openai.com/api-keys"
            )

        return ChatOpenAI(
            model=model_name,
            temperature=temperature,
            api_key=api_key
        )

    elif provider == 'google':
        from langchain_google_genai import ChatGoogleGenerativeAI

        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            raise ValueError(
                "GOOGLE_API_KEY não configurada no .env\n"
                "Obtenha uma chave em: https://aistudio.google.com/app/apikey"
            )

        return ChatGoogleGenerativeAI(
            model=model_name,
            temperature=temperature,
            google_api_key=api_key
        )

    else:
        raise ValueError(
            f"Provider '{provider}' não suportado.\n"
            f"Use 'openai' ou 'google' na variável LLM_PROVIDER do .env"
        )


def get_eval_llm(temperature: float = 0.0):
    """
    Retorna LLM configurado especificamente para avaliação (usa EVAL_MODEL).

    Args:
        temperature: Temperatura para geração

    Returns:
        Instância de LLM configurada para avaliação
    """
    eval_model = os.getenv('EVAL_MODEL', 'gpt-4o')
    return get_llm(model=eval_model, temperature=temperature)


def is_retryable_rate_limit_error(error: Exception) -> bool:
    """
    Verifica se um erro parece ser de quota/rate limit temporario.
    """
    error_msg = str(error).lower()
    retryable_terms = [
        "resource_exhausted",
        "quota exceeded",
        "rate limit",
        "too many requests",
        "429",
    ]
    return any(term in error_msg for term in retryable_terms)


def throttle_llm_calls():
    """
    Aplica intervalo minimo entre chamadas para providers mais sensiveis a rate limit.
    """
    global _LAST_LLM_CALL_TS

    provider = os.getenv("LLM_PROVIDER", "openai").lower()
    if provider not in {"google", "gemini"}:
        return

    min_interval = float(os.getenv("LLM_MIN_INTERVAL_SECONDS", "3.5"))
    if _LAST_LLM_CALL_TS <= 0:
        return

    elapsed = time.monotonic() - _LAST_LLM_CALL_TS
    if elapsed < min_interval:
        wait_time = min_interval - elapsed
        print(f"      Aguardando {wait_time:.1f}s para respeitar o limite do provider...")
        time.sleep(wait_time)


def invoke_with_retry(
    operation: Callable[[], T],
    description: str = "LLM call",
    max_retries: int = 6,
    base_delay: float = 8.0,
) -> T:
    """
    Executa uma operacao com retry/backoff para erros temporarios de quota/rate limit.
    """
    global _LAST_LLM_CALL_TS

    for attempt in range(max_retries):
        throttle_llm_calls()

        try:
            result = operation()
            _LAST_LLM_CALL_TS = time.monotonic()
            return result
        except Exception as exc:
            if not is_retryable_rate_limit_error(exc) or attempt == max_retries - 1:
                raise

            wait_time = min(base_delay * (2 ** attempt), 90.0)
            print(
                f"      {description} atingiu limite temporario do provider. "
                f"Tentando novamente em {wait_time:.0f}s "
                f"({attempt + 1}/{max_retries})..."
            )
            time.sleep(wait_time)

    raise RuntimeError(f"{description} falhou apos {max_retries} tentativas.")
