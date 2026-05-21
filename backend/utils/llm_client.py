import logging
import httpx
import asyncio
from config import CONFIG, TASK_MODELS

logger = logging.getLogger("chronicles-llm")

PROVIDERS = {}


def _init_providers():
    if PROVIDERS:
        return
    PROVIDERS["deepseek"] = {
        "base_url": CONFIG.DEEPSEEK_BASE_URL,
        "api_key": CONFIG.DEEPSEEK_API_KEY,
        "default_model": "deepseek-v4-flash",
        "extra_body": {"thinking": {"type": "disabled"}},
    }
    PROVIDERS["groq"] = {
        "base_url": CONFIG.GROQ_BASE_URL,
        "api_key": CONFIG.GROQ_API_KEY,
        "default_model": "llama-3.3-70b-versatile",
    }
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
    model_id = TASK_MODELS.get(task)
    if not model_id:
        provider_name = getattr(CONFIG, "LLM_PROVIDER", "groq")
        provider = PROVIDERS.get(provider_name, PROVIDERS["groq"])
        model_id = provider["default_model"]
        return provider_name, model_id
    for pname in PROVIDERS:
        provider = PROVIDERS.get(pname)
        if provider and model_id.startswith(f"{pname}:"):
            return pname, model_id.split(":", 1)[1]
    provider_name = getattr(CONFIG, "LLM_PROVIDER", "groq")
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
    primary_name = getattr(CONFIG, "LLM_PROVIDER", "deepseek")
    fallback_name = "groq"

    provider_names = [primary_name, fallback_name]

    for pname in provider_names:
        provider = PROVIDERS.get(pname)
        if not provider or not provider.get("base_url"):
            continue

        if pname == primary_name:
            _, model_name = resolve_model(task)
        else:
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
        if provider.get("extra_body"):
            payload.update(provider["extra_body"])

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
                    status_code = getattr(e, 'response', None)
                    if hasattr(status_code, 'status_code'):
                        sc = status_code.status_code
                        if sc == 429:
                            retry_after = int(status_code.headers.get('Retry-After', 5))
                            logger.warning(f"LLM {pname} rate-limited (429), waiting {retry_after}s")
                            await asyncio.sleep(retry_after)
                            continue
                    logger.warning(
                        f"LLM {pname} attempt {attempt}/{CONFIG.MAX_RETRIES} failed: "
                        f"{getattr(status_code, 'status_code', '?')} "
                        f"{getattr(status_code, 'text', '')[:100]}"
                    )
                    if attempt < CONFIG.MAX_RETRIES:
                        await asyncio.sleep(2 ** (attempt - 1))

        logger.warning(f"Provider {pname} exhausted, switching to next...")

    raise RuntimeError(
        f"LLM call failed after all providers. Last error: {type(last_error).__name__}: {repr(last_error)}"
    )
