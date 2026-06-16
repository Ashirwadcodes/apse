from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    KOREA_NTB_API_KEY: str
    KOREA_NTB_BASE_URL: str
    KOREA_NTB_TTL_SECONDS: int = 86400
    CACHE_TTL_SECONDS: int = 86400

    model_config = {"env_file": ".env"}


settings = Settings()
