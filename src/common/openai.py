from openai import OpenAI


def get_openai_client(provider: str) -> OpenAI:
    if provider == "openai":
        return OpenAI()
    elif provider == "ollama":
        return OpenAI(
            base_url="http://localhost:11434/v1",
            api_key="ollama",
        )
    else:
        raise ValueError(f"Unsupported chat provider: {provider}")
