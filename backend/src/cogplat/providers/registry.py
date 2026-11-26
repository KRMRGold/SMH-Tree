"""Default provider registry."""

from cogplat.config import Settings
from cogplat.providers.ollama import OllamaProvider
from cogplat.providers.openai_compat import OpenAICompatibleProvider
from cogplat.providers.openrouter import OpenRouterFreeProvider


def build_registry(settings: Settings):
    return {
        "ollama": OllamaProvider(settings.ollama_base_url),
        "openrouter_free": OpenRouterFreeProvider(),
        "openai_compat": OpenAICompatibleProvider(settings.openai_compat_base_url),
    }
