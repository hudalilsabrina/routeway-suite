"""Routeway AI Client: OpenAI- and Anthropic-compatible unified API interface."""

import json
from typing import Any, Dict, Generator, List, Optional, Union
import requests


class RoutewayClient:
    """Official client for Routeway AI (https://api.routeway.ai/v1)."""
    BASE_URL = "https://api.routeway.ai/v1"

    def __init__(self, api_key: str, timeout: int = 60):
        self.api_key = api_key.strip()
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "RoutewaySuite/1.0"
        })

    # --- 1. Models Catalog ---

    def list_models(self) -> List[Dict[str, Any]]:
        """Fetch complete list of 280+ AI models supported on Routeway."""
        resp = self.session.get(f"{self.BASE_URL}/models", timeout=self.timeout)
        if not resp.ok:
            raise RuntimeError(f"Routeway API Error ({resp.status_code}): {resp.text}")
        data = resp.json()
        return data.get("data", [])

    def filter_models(
        self,
        provider: Optional[str] = None,
        free_only: bool = False,
        search: Optional[str] = None,
        capability: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Filter models by provider, free tag, keyword search, or capability."""
        models = self.list_models()
        filtered = []
        for m in models:
            mid = m.get("id", "").lower()
            mname = m.get("name", "").lower()
            owned = m.get("owned_by", "").lower()

            if free_only and ":free" not in mid and m.get("pricing", {}).get("input", {}).get("price_per_million_t", 1) != 0:
                continue

            if provider and provider.lower() not in owned and provider.lower() not in mid:
                continue

            if search:
                s = search.lower()
                if s not in mid and s not in mname and s not in m.get("description", "").lower():
                    continue

            if capability:
                caps = m.get("capabilities", {})
                if not caps.get(capability, False):
                    continue

            filtered.append(m)
        return filtered

    # --- 2. Chat Completions (OpenAI Compatible) ---

    def chat_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        service_tier: Optional[str] = None,
        reasoning_effort: Optional[str] = None,
        **extra_kwargs
    ) -> Any:
        """
        Send a chat completion request to Routeway AI.
        Supports standard OpenAI format, server tools (@online, @flux-2-turbo),
        service tiers (flex, priority), and reasoning parameters.
        """
        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": stream,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens
        if service_tier:
            payload["service_tier"] = service_tier
        if reasoning_effort:
            payload["reasoning_effort"] = reasoning_effort

        payload.update(extra_kwargs)

        resp = self.session.post(
            f"{self.BASE_URL}/chat/completions",
            json=payload,
            timeout=self.timeout,
            stream=stream
        )

        if not resp.ok:
            raise RuntimeError(f"Routeway API Error ({resp.status_code}): {resp.text}")

        if stream:
            return self._stream_chat_response(resp)

        return resp.json()

    def _stream_chat_response(self, resp: requests.Response) -> Generator[str, None, None]:
        for line in resp.iter_lines():
            if not line:
                continue
            decoded = line.decode("utf-8")
            if decoded.startswith("data: "):
                data_str = decoded[6:].strip()
                if data_str == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_str)
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        yield content
                except Exception:
                    pass

    # --- 3. Anthropic Messages API ---

    def create_message(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        max_tokens: int = 1024,
        system: Optional[str] = None,
        temperature: float = 0.7,
        stream: bool = False
    ) -> Any:
        """Send a request using Anthropic Messages format (/v1/messages)."""
        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": stream
        }
        if system:
            payload["system"] = system

        resp = self.session.post(
            f"{self.BASE_URL}/messages",
            json=payload,
            timeout=self.timeout,
            stream=stream
        )
        if not resp.ok:
            raise RuntimeError(f"Routeway Messages API Error ({resp.status_code}): {resp.text}")

        if stream:
            return resp.iter_lines()
        return resp.json()

    # --- 4. Image Generation ---

    def generate_image(
        self,
        prompt: str,
        model: str = "juggernaut-lightning-flux",
        size: str = "1024x1024",
        n: int = 1,
        response_format: str = "url"
    ) -> Dict[str, Any]:
        """Generate images from text prompt (/v1/images/generations)."""
        payload = {
            "prompt": prompt,
            "model": model,
            "size": size,
            "n": n,
            "response_format": response_format
        }
        resp = self.session.post(
            f"{self.BASE_URL}/images/generations",
            json=payload,
            timeout=self.timeout
        )
        if not resp.ok:
            raise RuntimeError(f"Routeway Image API Error ({resp.status_code}): {resp.text}")
        return resp.json()

    # --- 5. Account & Key Management ---

    def get_balance(self) -> Dict[str, Any]:
        """Check account balance (/v1/account/balance). Requires account:balance scope."""
        resp = self.session.get(f"{self.BASE_URL}/account/balance", timeout=self.timeout)
        if not resp.ok:
            raise RuntimeError(f"Account Balance Error ({resp.status_code}): {resp.text}")
        return resp.json()

    def list_keys(self) -> List[Dict[str, Any]]:
        """List all general API keys for the account (/v1/account/keys)."""
        resp = self.session.get(f"{self.BASE_URL}/account/keys", timeout=self.timeout)
        if not resp.ok:
            raise RuntimeError(f"List Keys Error ({resp.status_code}): {resp.text}")
        return resp.json().get("data", [])

    def create_key(
        self,
        label: str,
        daily_limit: Optional[int] = None,
        minute_limit: Optional[int] = None,
        allowed_models: Optional[List[str]] = None,
        balance: Optional[float] = None
    ) -> Dict[str, Any]:
        """Create a new general API key (/v1/account/keys)."""
        payload: Dict[str, Any] = {"label": label}
        if daily_limit is not None:
            payload["daily_limit"] = daily_limit
        if minute_limit is not None:
            payload["minute_limit"] = minute_limit
        if allowed_models:
            payload["allowed_models"] = allowed_models
        if balance is not None:
            payload["balance"] = balance

        resp = self.session.post(f"{self.BASE_URL}/account/keys", json=payload, timeout=self.timeout)
        if not resp.ok:
            raise RuntimeError(f"Create Key Error ({resp.status_code}): {resp.text}")
        return resp.json().get("data", {})

    def delete_key(self, key_id: int) -> bool:
        """Delete an API key (/v1/account/keys/{key_id})."""
        resp = self.session.delete(f"{self.BASE_URL}/account/keys/{key_id}", timeout=self.timeout)
        if not resp.ok:
            raise RuntimeError(f"Delete Key Error ({resp.status_code}): {resp.text}")
        return True

    def get_activity(self) -> Dict[str, Any]:
        """Fetch account activity logs (/v1/account/activity)."""
        resp = self.session.get(f"{self.BASE_URL}/account/activity", timeout=self.timeout)
        if not resp.ok:
            raise RuntimeError(f"Activity Error ({resp.status_code}): {resp.text}")
        return resp.json()
