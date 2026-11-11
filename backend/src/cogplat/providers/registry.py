"""Default provider registry."""

from cogplat.config import Settings
from cogplat.providers.ollama import OllamaProvider
from cogplat.providers.openai_compat import OpenAICompatibleProvider


def build_registry(settings: Settings):
    return {
        "ollama": OllamaProvider(settings.ollama_base_url),
        "openai_compat": OpenAICompatibleProvider(settings.openai_compat_base_url),
    }
