from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    google_api_key: str = ""
    anthropic_model: str = "claude-opus-4-5-20251101"
    openai_model: str = "gpt-5.2"
    gemini_model: str = "gemini-2.5-pro"
    synthesis_provider: str = "anthropic"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
