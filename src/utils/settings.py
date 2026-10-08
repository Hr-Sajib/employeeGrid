from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    DB_CONNECTION: str
    OPENROUTER_API_KEY: str
    OPENROUTER_MODEL: str = "openai/gpt-oss-120b"


settings = Settings()
