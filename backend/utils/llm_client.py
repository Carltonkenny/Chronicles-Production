import logging
import httpx
import asyncio
from config import CONFIG

logger = logging.getLogger("chronicles-llm")

PROVIDERS = {}


def _init_providers():
    if PROVIDERS:
        return
    PROVIDERS["openrouter"] = {
        "base_url": getattr(CONFIG, "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1/chat/completions"),
        "api_key": getattr(CONFIG, "OPENROUTER_API_KEY", ""),
        "default_model": getattr(CONFIG, "OPENROUTER_MODEL", "nousresearch/hermes-3-llama-3.1-405b:free"),
    }
    PROVIDERS["pollinations"] = {
        "base_url": CONFIG.POLLINATIONS_BASE_URL,
        "api_key": CONFIG.POLLINATIONS_API_KEY,
        "default_model": CONFIG.POLLINATIONS_MODEL,
    }


def _build_headers(provider: dict) -> dict:
    headers = {"Content-Type": "application/json"}
    if provider["api_key"]:
        headers["Authorization"] = f"Bearer {provider['api_key']}"
    return headers


def resolve_model(task: str = "default") -> tuple[str, str]:
    _init_providers()
    task_models = getattr(CONFIG, "TASK_MODELS", {})
    model_id = task_models.get(task)
    if not model_id:
        provider_name = getattr(CONFIG, "LLM_PROVIDER", "openrouter")
        provider = PROVIDERS.get(provider_name, PROVIDERS["pollinations"])
        model_id = provider["default_model"]
        return provider_name, model_id
    for pname in ("openrouter", "pollinations"):
        provider = PROVIDERS.get(pname)
        if provider and model_id.startswith(pname):
            return pname, model_id
    provider_name = getattr(CONFIG, "LLM_PROVIDER", "openrouter")
    return provider_name, model_id


async def call_llm(
    system: str,
    user: str,
    max_tokens: int = 3000,
    temperature: float = None,
    task: str = "default",
) -> str:
    if temperature is None:
        temperature = CONFIG.WRITER_TEMPERATURE

    _init_providers()
    primary_name = getattr(CONFIG, "LLM_PROVIDER", "openrouter")
    fallback_name = "pollinations" if primary_name == "openrouter" else "openrouter"

    provider_names = [primary_name, fallback_name]

    for pname in provider_names:
        provider = PROVIDERS.get(pname)
        if not provider or not provider.get("base_url"):
            continue

        model_name, _ = resolve_model(task)
        if not model_name.startswith(pname):
            model_name = provider["default_model"]

        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        headers = _build_headers(provider)
        last_error = None

        async with httpx.AsyncClient(timeout=CONFIG.REQUEST_TIMEOUT) as client:
            for attempt in range(1, CONFIG.MAX_RETRIES + 1):
                try:
                    response = await client.post(
                        provider["base_url"],
                        json=payload,
                        headers=headers,
                    )
                    response.raise_for_status()
                    data = response.json()
                    content = data.get("choices", [{}])[0].get("message", {}).get("content")
                    if not content:
                        raise KeyError("Empty or missing content in response")
                    logger.info(f"LLM: {pname}/{model_name} -> {len(content)} chars")
                    return content

                except (httpx.HTTPError, KeyError) as e:
                    last_error = e
                    logger.warning(
                        f"LLM {pname} attempt {attempt}/{CONFIG.MAX_RETRIES} failed: {type(e).__name__}"
                    )
                    if attempt < CONFIG.MAX_RETRIES:
                        wait_time = 2 ** (attempt - 1)
                        await asyncio.sleep(wait_time)

        logger.warning(f"Provider {pname} exhausted, switching to next...")

    raise RuntimeError(
        f"LLM call failed after all providers. Last error: {type(last_error).__name__}: {repr(last_error)}"
    )
