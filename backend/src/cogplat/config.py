"""Environment and application-data configuration."""

from __future__ import annotations

import os
import platform
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime settings passed to the application factory."""

    api_token: str
    data_dir: Path
    ollama_base_url: str = "http://127.0.0.1:11434"
    openai_compat_base_url: str = "https://api.openai.com/v1"
    default_max_input_tokens: int = 8192
    default_reserve_output_tokens: int = 1024
    workflows_enabled: bool = True


def resolve_data_dir(
    environ: Mapping[str, str] | None = None,
    home: Path | None = None,
    system: str | None = None,
) -> Path:
    """Resolve the per-user data directory, honoring an explicit override."""

    env = os.environ if environ is None else environ
    override = env.get("COGPLAT_DATA_DIR")
    if override:
        return Path(override).expanduser()

    user_home = Path.home() if home is None else Path(home)
    operating_system = platform.system() if system is None else system

    if operating_system == "Windows":
        base = Path(env.get("APPDATA", user_home / "AppData" / "Roaming"))
    elif operating_system == "Darwin":
        base = user_home / "Library" / "Application Support"
    else:
        base = Path(env.get("XDG_DATA_HOME", user_home / ".local" / "share"))

    return base / "CognitivePlatform"


def load_settings(environ: Mapping[str, str] | None = None) -> Settings:
    """Load settings and fail closed when the per-launch API token is absent."""

    env = os.environ if environ is None else environ
    token = env.get("COGPLAT_API_TOKEN", "").strip()
    if not token:
        raise RuntimeError(
            "COGPLAT_API_TOKEN must be set before starting the backend. "
            "The desktop shell will provide a per-launch token."
        )

    return Settings(
        api_token=token,
        data_dir=resolve_data_dir(env),
        ollama_base_url=env.get("COGPLAT_OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
        openai_compat_base_url=env.get(
            "COGPLAT_OPENAI_COMPAT_BASE_URL", "https://api.openai.com/v1"
        ),
        default_max_input_tokens=int(env.get("COGPLAT_DEFAULT_MAX_INPUT_TOKENS", "8192")),
        default_reserve_output_tokens=int(env.get("COGPLAT_DEFAULT_RESERVE_OUTPUT_TOKENS", "1024")),
        workflows_enabled=env.get("COGPLAT_WORKFLOWS_ENABLED", "true").strip().lower() not in {"0", "false", "no", "off"},
    )


def ensure_data_dir(data_dir: Path) -> Path:
    """Create and return the configured application-data directory."""

    resolved = Path(data_dir).expanduser()
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved
