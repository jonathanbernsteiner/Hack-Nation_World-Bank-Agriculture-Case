"""Typed settings read from the environment. Unset values are None; import never raises.
Values are never logged."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

_REPO_ENV = Path(__file__).resolve().parents[2] / ".env"
if not os.environ.get("VERCEL") and _REPO_ENV.is_file():
    load_dotenv(_REPO_ENV)


_FALSE_VALUES = {"false", "0", "no", "off"}


def _env(name: str) -> str | None:
    value = os.environ.get(name)
    return value if value else None


@dataclass(frozen=True)
class Settings:
    database_url: str | None
    supabase_url: str | None
    anthropic_api_key: str | None
    anthropic_translate_model: str | None
    anthropic_extract_model: str | None
    elevenlabs_api_key: str | None
    elevenlabs_agent_id: str | None
    elevenlabs_agent_llm: str | None
    elevenlabs_webhook_secret: str | None
    elevenlabs_webhook_id: str | None
    hotline_tool_secret: str | None
    hotline_admin_secret: str | None
    demo_user: str | None
    demo_password: str | None
    ledger_pin_salt: str | None
    price_include_synthetic: bool
    public_base_url: str | None


def load_settings() -> Settings:
    return Settings(
        database_url=_env("DATABASE_URL"),
        supabase_url=_env("SUPABASE_URL"),
        anthropic_api_key=_env("ANTHROPIC_API_KEY"),
        anthropic_translate_model=_env("ANTHROPIC_TRANSLATE_MODEL"),
        anthropic_extract_model=_env("ANTHROPIC_EXTRACT_MODEL"),
        elevenlabs_api_key=_env("ELEVENLABS_API_KEY"),
        elevenlabs_agent_id=_env("ELEVENLABS_AGENT_ID"),
        elevenlabs_agent_llm=_env("ELEVENLABS_AGENT_LLM"),
        elevenlabs_webhook_secret=_env("ELEVENLABS_WEBHOOK_SECRET"),
        elevenlabs_webhook_id=_env("ELEVENLABS_WEBHOOK_ID"),
        hotline_tool_secret=_env("HOTLINE_TOOL_SECRET"),
        hotline_admin_secret=_env("HOTLINE_ADMIN_SECRET"),
        demo_user=_env("DEMO_USER"),
        demo_password=_env("DEMO_PASSWORD"),
        ledger_pin_salt=_env("LEDGER_PIN_SALT"),
        price_include_synthetic=(_env("PRICE_INCLUDE_SYNTHETIC") or "true").strip().lower() not in _FALSE_VALUES,
        public_base_url=_env("PUBLIC_BASE_URL"),
    )


settings = load_settings()
