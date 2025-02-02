from openai import APIError

from src.common.exceptions import KnownException


def handle_openai_client_error(e: APIError, model: str) -> None:
    # OpenAI Model Not Found
    if e.code == "model_not_found":
        raise KnownException(
            f"Model '{model}' not found, or you do not have access to it."
        )

    # OpenAI model not supporting 'system' prompt.
    # TODO: Test if system prompt update is required for o3
    if "does not support 'system' with this model" in e.message:
        raise KnownException(f"Model '{model}' is not supported.")

    # OpenAI model not supporting 'tools'
    if "'tools is not supported in this model" in e.message:
        raise KnownException(f"Model '{model}' is not supported.")

    # Deepseek Model Not Found
    if "Model Not Exists" in e.message:
        raise KnownException(f"Model '{model}' not found.")

    # Deepseek model not supporting 'tools'
    if "does not support Function Calling" in e.message:
        raise KnownException(f"Model '{model}' is not supported.")
