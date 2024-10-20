from enum import Enum
from pydantic_settings import BaseSettings


class VectorStoreProvider(str, Enum):
    REDIS = "redis"
    CHROMA = "chroma"


class Settings(BaseSettings):
    VECTOR_STORE_PROVIDER: VectorStoreProvider = VectorStoreProvider.REDIS

    OPENAI_API_KEY: str

    REDIS_URL: str

    # @model_validator(mode="after")
    # def check_redis_url(self):
    #     if self.VECTOR_STORE_PROVIDER == "redis" and not self.REDIS_URL:
    #         raise ValueError(
    #             'REDIS_URL is required when VECTOR_STORE_PROVIDER is "redis"'
    #         )
    #     return self


settings = Settings()  # type: ignore
