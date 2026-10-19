"""Authentication and OAuth Session Helper for Routeway AI."""

import requests
from typing import Dict, Any, Optional

BASE_URL = "https://routeway.ai"


class RoutewayAuthHelper:
    """Handles web authentication, Better-Auth endpoints, and OAuth redirects."""

    @staticmethod
    def get_oauth_url(provider: str = "github", redirect_url: str = "/dashboard") -> str:
        """
        Requests OAuth authorization URL from Better-Auth (/api/auth/sign-in/social).
        Supported providers: 'github', 'google', 'discord'.
        """
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
            "Content-Type": "application/json",
            "Origin": BASE_URL,
            "Referer": f"{BASE_URL}/auth"
        }
        payload = {
            "provider": provider.lower(),
            "callbackURL": redirect_url
        }

        resp = requests.post(f"{BASE_URL}/api/auth/sign-in/social", json=payload, headers=headers, timeout=15)
        if not resp.ok:
            raise RuntimeError(f"Social Auth Error ({resp.status_code}): {resp.text}")

        data = resp.json()
        return data.get("url") or resp.headers.get("Location") or ""

    @staticmethod
    def check_session(cookie_str: str) -> Optional[Dict[str, Any]]:
        """Verify an active web session cookie via /api/auth/get-session."""
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Cookie": cookie_str,
            "Origin": BASE_URL
        }
        resp = requests.get(f"{BASE_URL}/api/auth/get-session", headers=headers, timeout=15)
        if resp.ok and resp.text.strip() != "null":
            try:
                return resp.json()
            except Exception:
                pass
        return None
