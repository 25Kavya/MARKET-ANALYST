import json
import os
import time

import requests

from phase1.logging_config import get_logger

logger = get_logger(__name__)

_GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
_MAX_RETRIES = 2
_BACKOFF_SECONDS = 1
_TIMEOUT_SECONDS = 10
_DEFAULT_MODEL = "llama-3.1-8b-instant"


class GroqError(Exception):
    pass


def _is_retryable(exc):
    if isinstance(exc, requests.exceptions.HTTPError):
        status = exc.response.status_code if exc.response is not None else None
        return status is not None and status >= 500
    return isinstance(exc, (requests.exceptions.ConnectionError, requests.exceptions.Timeout))


def call_groq(system_prompt, user_prompt, model=None):
    """Call Groq's chat completions endpoint in JSON mode and return the
    parsed response dict. Only genuine transport/5xx errors are retried —
    a 4xx or a malformed JSON body is a real failure, not a transient one,
    and is raised immediately rather than wasting time retrying it."""
    model = model or os.getenv("GROQ_MODEL", _DEFAULT_MODEL)
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise GroqError("GROQ_API_KEY is not configured")

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0,
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    start = time.monotonic()
    logger.info("groq_client.call_groq request model=%s", model)

    last_error = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            response = requests.post(_GROQ_URL, headers=headers, json=payload, timeout=_TIMEOUT_SECONDS)
            response.raise_for_status()
            body = response.json()
            content = body["choices"][0]["message"]["content"]
            parsed = json.loads(content)

            elapsed = time.monotonic() - start
            logger.info("groq_client.call_groq ok model=%s elapsed=%.2fs", model, elapsed)
            return parsed
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.HTTPError) as exc:
            last_error = exc
            if not _is_retryable(exc):
                logger.error("groq_client.call_groq non-retryable failure model=%s error=%s", model, exc)
                raise GroqError(f"Groq call failed: {exc}") from exc

            logger.warning(
                "groq_client.call_groq attempt %d/%d failed model=%s error=%s",
                attempt, _MAX_RETRIES, model, exc,
            )
            if attempt < _MAX_RETRIES:
                time.sleep(_BACKOFF_SECONDS * attempt)
        except (KeyError, IndexError, json.JSONDecodeError) as exc:
            logger.error("groq_client.call_groq malformed response model=%s error=%s", model, exc)
            raise GroqError(f"Groq returned a malformed response: {exc}") from exc

    logger.error("groq_client.call_groq exhausted retries model=%s error=%s", model, last_error)
    raise GroqError(f"Groq call failed after {_MAX_RETRIES} attempts: {last_error}") from last_error
