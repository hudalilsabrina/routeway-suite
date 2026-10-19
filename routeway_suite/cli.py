"""Command Line Interface for Routeway AI Suite."""

import argparse
import json
import os
import sys
from typing import Optional
from .client import RoutewayClient
from .auth_helper import RoutewayAuthHelper

CONFIG_PATH = os.path.expanduser("~/.routeway_config.json")


def load_config() -> dict:
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_config(data: dict) -> None:
    current = load_config()
    current.update(data)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(current, f, indent=2)


def get_api_key(args: argparse.Namespace) -> str:
    key = getattr(args, "key", None) or os.getenv("ROUTEWAY_API_KEY") or load_config().get("api_key")
    if not key:
        print("[!] No Routeway API key found. Pass --key <KEY>, set ROUTEWAY_API_KEY, or run: routeway save-key <KEY>")
        sys.exit(1)
    return key


def cmd_save_key(args: argparse.Namespace) -> None:
    if not args.key_value:
        print("[!] Please supply an API key.")
        sys.exit(1)
    save_config({"api_key": args.key_value.strip()})
    print(f"[✓] Routeway API key saved to {CONFIG_PATH}")


def cmd_models(args: argparse.Namespace) -> None:
    print("\n" + "=" * 80)
    print("           🌐 ROUTEWAY AI MODEL EXPLORER (280+ Models Unified)")
    print("=" * 80)

    # Use dummy key for models since /v1/models is public
    key = getattr(args, "key", None) or os.getenv("ROUTEWAY_API_KEY") or load_config().get("api_key") or "dummy"
    client = RoutewayClient(api_key=key)

    try:
        models = client.filter_models(
            provider=args.provider,
            free_only=args.free,
            search=args.search
        )
    except Exception as e:
        print(f"[x] Error querying models: {e}")
        sys.exit(1)

    print(f"Total matching models: {len(models)}")
    print(f"{'MODEL ID':<35} {'PROVIDER':<15} {'PRICE (IN/OUT 1M)':<20}")
    print("-" * 80)

    for m in models:
        mid = m.get("id", "")
        owned = m.get("owned_by", "")
        pricing = m.get("pricing", {})
        inp = pricing.get("input", {}).get("price_per_million_t", "-")
        out = pricing.get("output", {}).get("price_per_million_t", "-")
        if inp == 0 and out == 0:
            price_str = "FREE"
        elif inp != "-" and out != "-":
            price_str = f"${inp} / ${out}"
        else:
            price_str = "Custom / Per Image"

        print(f" • {mid:<33} {owned:<15} {price_str:<20}")

    print("=" * 80 + "\n")


def cmd_balance(args: argparse.Namespace) -> None:
    key = get_api_key(args)
    client = RoutewayClient(api_key=key)

    print("[*] Checking account balance...")
    try:
        res = client.get_balance()
        balance = res.get("balance", 0.0)
        print("\n" + "=" * 45)
        print("          💰 ROUTEWAY ACCOUNT BALANCE")
        print("=" * 45)
        print(f" • Current Credit Balance: ${balance:.4f} USD")
        print("=" * 45 + "\n")
    except Exception as e:
        print(f"[x] Failed to retrieve balance: {e}")
        sys.exit(1)


def cmd_keys(args: argparse.Namespace) -> None:
    key = get_api_key(args)
    client = RoutewayClient(api_key=key)

    if args.action == "list":
        print("[*] Fetching API keys...")
        try:
            keys = client.list_keys()
            print("\n" + "=" * 75)
            print("                🔑 ACCOUNT API KEYS")
            print("=" * 75)
            print(f"{'ID':<6} {'LABEL':<22} {'KEY':<24} {'TODAY USAGE':<12}")
            print("-" * 75)
            for k in keys:
                kid = k.get("api_key_id", "-")
                lbl = k.get("label", "unlabeled")
                masked = k.get("key", "")
                usage = k.get("usage_today", 0)
                print(f" {kid:<5} {lbl:<22} {masked:<24} ${usage}")
            print("=" * 75 + "\n")
        except Exception as e:
            print(f"[x] Error listing keys: {e}")
            sys.exit(1)

    elif args.action == "create":
        if not args.label:
            print("[!] Please specify a label with --label <NAME>")
            sys.exit(1)
        print(f"[*] Creating new API key with label '{args.label}'...")
        try:
            res = client.create_key(label=args.label, daily_limit=args.limit)
            new_key = res.get("key")
            kid = res.get("api_key_id")
            print("\n" + "=" * 60)
            print("           🎉 API KEY CREATED SUCCESSFULLY")
            print("=" * 60)
            print(f" • Key ID : {kid}")
            print(f" • Label  : {args.label}")
            print(f" • Key    : {new_key}")
            print("=" * 60)
            print("⚠️  Warning: Store this key immediately. It is only shown once!\n")
        except Exception as e:
            print(f"[x] Error creating key: {e}")
            sys.exit(1)

    elif args.action == "delete":
        if not args.id:
            print("[!] Please specify a key ID with --id <ID>")
            sys.exit(1)
        print(f"[*] Deleting key ID {args.id}...")
        try:
            client.delete_key(args.id)
            print(f"[✓] Key ID {args.id} deleted successfully.")
        except Exception as e:
            print(f"[x] Error deleting key: {e}")
            sys.exit(1)


def cmd_chat(args: argparse.Namespace) -> None:
    key = get_api_key(args)
    client = RoutewayClient(api_key=key)

    model = args.model
    if args.web and not model.endswith("@online"):
        model = f"{model}@online"

    prompt = args.prompt or "Hello, introduce yourself and list 3 of your core strengths."

    print(f"[*] Dispatching prompt to {model}...")
    messages = []
    if args.system:
        messages.append({"role": "system", "content": args.system})
    messages.append({"role": "user", "content": prompt})

    try:
        if args.no_stream:
            res = client.chat_completion(model=model, messages=messages, stream=False)
            content = res.get("choices", [{}])[0].get("message", {}).get("content", "")
            print(f"\n[Response from {model}]:\n{content}\n")
        else:
            print(f"\n[Response from {model}]:")
            for chunk in client.chat_completion(model=model, messages=messages, stream=True):
                sys.stdout.write(chunk)
                sys.stdout.flush()
            print("\n")
    except Exception as e:
        print(f"[x] Error during chat completion: {e}")
        sys.exit(1)


def cmd_image(args: argparse.Namespace) -> None:
    key = get_api_key(args)
    client = RoutewayClient(api_key=key)

    print(f"[*] Generating image via {args.model} for prompt: '{args.prompt}'...")
    try:
        res = client.generate_image(
            prompt=args.prompt,
            model=args.model,
            size=args.size,
            n=args.n
        )
        data = res.get("data", [])
        print("\n" + "=" * 65)
        print("             🎨 IMAGE GENERATION COMPLETED")
        print("=" * 65)
        for idx, item in enumerate(data):
            url = item.get("url")
            print(f" • Image #{idx + 1}: {url}")
        print("=" * 65 + "\n")
    except Exception as e:
        print(f"[x] Image generation error: {e}")
        sys.exit(1)


def cmd_oauth_link(args: argparse.Namespace) -> None:
    provider = args.provider or "github"
    print(f"[*] Generating 1-click OAuth sign-in link for provider: {provider}...")
    try:
        url = RoutewayAuthHelper.get_oauth_url(provider=provider)
        print("\n" + "=" * 70)
        print(f"        🔗 ROUTEWAY 1-CLICK {provider.upper()} SIGN-IN LINK")
        print("=" * 70)
        print(f"Open this URL in your browser to sign in & get free credits:")
        print(f"\n{url}\n")
        print("=" * 70 + "\n")
    except Exception as e:
        print(f"[x] Failed to generate OAuth link: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Routeway Suite — Unified CLI for 280+ AI models, image gen, and key management."
    )
    parser.add_argument("--key", "-k", help="Routeway API or Management Key")

    subparsers = parser.add_subparsers(dest="subcommand", help="Available subcommands")

    # save-key
    p_sk = subparsers.add_parser("save-key", help="Save API key to ~/.routeway_config.json")
    p_sk.add_argument("key_value", help="Routeway API key")

    # models
    p_mod = subparsers.add_parser("models", help="Explore supported AI models")
    p_mod.add_argument("--provider", "-p", help="Filter by provider (e.g. openai, anthropic, google, deepseek)")
    p_mod.add_argument("--free", "-f", action="store_true", help="Show free models only")
    p_mod.add_argument("--search", "-s", help="Search keyword in model ID/description")

    # balance
    subparsers.add_parser("balance", help="Check account credit balance")

    # keys
    p_keys = subparsers.add_parser("keys", help="Manage API keys")
    p_keys.add_argument("action", choices=["list", "create", "delete"], help="Action to perform")
    p_keys.add_argument("--label", "-l", help="Label for new key")
    p_keys.add_argument("--limit", type=int, help="Daily spend/request limit")
    p_keys.add_argument("--id", type=int, help="Key ID for deletion")

    # chat
    p_chat = subparsers.add_parser("chat", help="Send chat completion request")
    p_chat.add_argument("--model", "-m", default="gpt-4o-mini", help="Model ID (e.g. gpt-4o, claude-sonnet-5.5, kimi-k2.7)")
    p_chat.add_argument("--prompt", help="Prompt text")
    p_chat.add_argument("--system", help="System prompt")
    p_chat.add_argument("--no-stream", action="store_true", help="Disable streaming output")
    p_chat.add_argument("--web", action="store_true", help="Enable online web search tool (@online)")

    # image
    p_img = subparsers.add_parser("image", help="Generate images from text prompt")
    p_img.add_argument("--prompt", "-p", required=True, help="Image prompt")
    p_img.add_argument("--model", "-m", default="juggernaut-lightning-flux", help="Image model ID")
    p_img.add_argument("--size", "-s", default="1024x1024", help="Resolution")
    p_img.add_argument("-n", type=int, default=1, help="Number of images")

    # oauth-link
    p_oa = subparsers.add_parser("oauth-link", help="Generate 1-click OAuth login link")
    p_oa.add_argument("--provider", "-p", default="github", choices=["github", "google", "discord"])

    args = parser.parse_args()

    if not args.subcommand:
        parser.print_help()
        sys.exit(0)

    dispatch = {
        "save-key": cmd_save_key,
        "models": cmd_models,
        "balance": cmd_balance,
        "keys": cmd_keys,
        "chat": cmd_chat,
        "image": cmd_image,
        "oauth-link": cmd_oauth_link,
    }

    dispatch[args.subcommand](args)


if __name__ == "__main__":
    main()
