"""Automated Registrar & Session Handler for Routeway AI."""

import asyncio
import os
import re
import sys
import time
from typing import Dict, Any, Optional
import requests

from .auth_helper import RoutewayAuthHelper

BASE_URL = "https://routeway.ai"


class RoutewayRegistrar:
    """Automates registration, hCaptcha handling via Camoufox, and OTP verification."""

    def __init__(self, proxy: Optional[str] = None):
        self.proxy = proxy

    async def run_email_registration(
        self,
        email: str,
        otp_callback=None,
        timeout: int = 45
    ) -> Dict[str, Any]:
        """
        Drives Camoufox with optional proxy to trigger invisible hCaptcha,
        send OTP, receive OTP, and verify session.
        """
        from camoufox.async_api import AsyncCamoufox

        # Reject gmail for email OTP as Routeway requires Google SSO for @gmail.com
        if email.lower().endswith("@gmail.com"):
            raise ValueError(
                "Routeway blocks direct email OTP for @gmail.com (enforces Google SSO). "
                "Please use a custom domain, Outlook, or disposable email."
            )

        launch_kwargs = {"headless": True}
        if self.proxy:
            # Format: http://user:pass@host:port or host:port
            proxy_config = {}
            if "@" in self.proxy:
                proto_part, auth_host = self.proxy.split("://") if "://" in self.proxy else ("http", self.proxy)
                user_pass, host_port = auth_host.split("@")
                user, password = user_pass.split(":")
                proxy_config["server"] = f"{proto_part}://{host_port}"
                proxy_config["username"] = user
                proxy_config["password"] = password
            else:
                proxy_config["server"] = self.proxy if "://" in self.proxy else f"http://{self.proxy}"
            launch_kwargs["proxy"] = proxy_config

        otp_sent = False
        captcha_passed = False
        error_msg = None

        async with AsyncCamoufox(**launch_kwargs) as browser:
            page = await browser.new_page()

            # Intercept API calls
            async def on_response(res):
                nonlocal otp_sent, captcha_passed, error_msg
                if "send-verification-otp" in res.url:
                    if res.status == 200:
                        otp_sent = True
                        captcha_passed = True
                    else:
                        try:
                            data = await res.json()
                            error_msg = data.get("message")
                        except Exception:
                            pass

            page.on("response", on_response)

            print(f"[*] Navigating to {BASE_URL}/auth ...")
            await page.goto(f"{BASE_URL}/auth", timeout=35000)
            await asyncio.sleep(2)

            # Fill email
            email_inp = await page.wait_for_selector('dialog.uyLEMW_card input[type="email"]', timeout=8000)
            await email_inp.fill(email.strip())
            await asyncio.sleep(1)

            # Click Continue with email
            submit_btn = await page.wait_for_selector('dialog.uyLEMW_card button:has-text("Continue with email")', timeout=5000)
            print("[*] Submitting email and triggering invisible hCaptcha...")
            await submit_btn.click()

            # Wait for invisible captcha resolution or OTP dispatch
            t0 = time.time()
            while time.time() - t0 < timeout:
                if otp_sent:
                    print("[✓] Invisible hCaptcha passed! Verification OTP sent to email.")
                    break
                if error_msg:
                    raise RuntimeError(f"Routeway returned error: {error_msg}")
                await asyncio.sleep(1)

            if not otp_sent:
                # Check if visual challenge appeared
                has_challenge = any("challenge" in f.url for f in page.frames)
                if has_challenge:
                    raise RuntimeError(
                        "hCaptcha triggered an interactive visual challenge due to IP reputation. "
                        "Please provide a residential/ISP proxy via --proxy <URL>."
                    )
                raise TimeoutError("Timeout waiting for OTP email dispatch.")

            # If an OTP callback was supplied, ask/poll for code
            if otp_callback:
                code = await otp_callback()
                if code:
                    print(f"[*] Entering 6-digit OTP: {code} ...")
                    # Fill OTP input
                    otp_inputs = await page.query_selector_all('input[maxlength="1"], input[type="text"]')
                    if len(otp_inputs) == 6:
                        for idx, char in enumerate(str(code)):
                            await otp_inputs[idx].fill(char)
                    else:
                        code_field = await page.wait_for_selector('input[name="otp"], input[placeholder*="code"], input[placeholder*="OTP"]', timeout=5000)
                        await code_field.fill(str(code))

                    await asyncio.sleep(2)
                    cookies = await page.context.cookies()
                    return {
                        "status": "success",
                        "email": email,
                        "cookies": cookies
                    }

            return {
                "status": "otp_sent",
                "email": email
            }
