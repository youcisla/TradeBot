"""openrouter_gateway.py — fallback LLM via OpenRouter.

When the primary DeepSeek endpoint is unavailable, the ``OpenRouterGateway``
fires requests to OpenRouter.ai using the OpenAI-compatible REST API.

Gated by ``settings.OPENROUTER_FALLBACK_ENABLED``.  Returns empty string
and logs a warning on any error — never raises.

Usage::

    from llm.openrouter_gateway import OpenRouterGateway

    gw = OpenRouterGateway()
    response = await gw.complete(messages=[
        {"role": "system", "content": "You are a trading assistant."},
        {"role": "user",   "content": "Analyse EURUSD confluence..."},
    ])
"""

from __future__ import annotations

import asyncio
import logging
from typing import Sequence

logger = logging.getLogger(__name__)

_TIMEOUT_SECONDS = 20
_DEFAULT_MODEL = "mistralai/mistral-7b-instruct"


class OpenRouterGateway:
    """Async LLM gateway backed by OpenRouter.ai."""

    def __init__(self) -> None:
        self._enabled: bool = False
        self._api_key: str = ""
        self._base_url: str = "https://openrouter.ai/api/v1"
        self._model: str = _DEFAULT_MODEL
        self._try_init()

    def _try_init(self) -> None:
        try:
            from config import settings
            self._enabled = bool(getattr(settings, "OPENROUTER_FALLBACK_ENABLED", False))
            self._api_key = getattr(settings, "OPENROUTER_API_KEY", "") or ""
            self._base_url = getattr(settings, "OPENROUTER_BASE_URL", self._base_url)
            self._model = getattr(settings, "OPENROUTER_MODEL", self._model)
        except Exception as exc:  # noqa: BLE001
            logger.debug("OpenRouterGateway config load failed: %s", exc)

    async def complete(
        self,
        messages: Sequence[dict],
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 512,
    ) -> str:
        """Send a chat completion request to OpenRouter.

        Returns the assistant message content string on success.
        Returns empty string on any error.
        """
        if not self._enabled:
            logger.debug("OpenRouterGateway disabled")
            return ""

        if not self._api_key:
            logger.warning("OpenRouterGateway: OPENROUTER_API_KEY not set")
            return ""

        target_model = model or self._model

        try:
            return await asyncio.wait_for(
                self._post(messages, target_model, temperature, max_tokens),
                timeout=_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            logger.warning("OpenRouterGateway: request timed out after %ss", _TIMEOUT_SECONDS)
            return ""
        except Exception as exc:  # noqa: BLE001
            logger.warning("OpenRouterGateway.complete error: %s", exc)
            return ""

    async def _post(
        self,
        messages: Sequence[dict],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        try:
            import aiohttp
        except ImportError:
            logger.warning("aiohttp not installed; pip install aiohttp")
            return ""

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/neuralFX-tradingbot",
            "X-Title": "NeuralFX TradingBot",
        }
        payload = {
            "model": model,
            "messages": list(messages),
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self._base_url}/chat/completions",
                json=payload,
                headers=headers,
            ) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    logger.warning(
                        "OpenRouterGateway HTTP %s: %s", resp.status, body[:300]
                    )
                    return ""
                data = await resp.json()

        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            logger.warning("OpenRouterGateway: unexpected response shape: %s", exc)
            return ""
