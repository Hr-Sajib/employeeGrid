from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    DB_CONNECTION: str
    OPENROUTER_API_KEY: str
    JINA_API_KEY: str

    ENVIRONMENT: str = "development"   # the container sets "production"
    PUBLIC_ORIGIN: str = ""            # e.g. https://chat.example.com: the only origin allowed to open the chat socket

    AGENT_LOG_LEVEL: str = "INFO"   # set to DEBUG in .env to log full prompts, replies and results

    # models
    OPENROUTER_MODEL: str = "openai/gpt-oss-120b"        # tools agent + synthesizer
    ROUTER_MODEL: str = "openai/gpt-oss-20b"
    VERIFIER_MODEL: str = "qwen/qwen3-235b-a22b-2507"    # different family on purpose
    EMBEDDING_MODEL: str = "qwen/qwen3-embedding-4b"
    EMBEDDING_DIM: int = 1024
    RERANK_MODEL: str = "jina-reranker-v3.5"

    # retrieval
    RAG_CANDIDATES: int = 20        # chunks fetched from the vector search
    RAG_TOP_K: int = 5              # chunks kept after reranking
    RERANK_MIN_SCORE: float = 0.0   # chunks scoring below this are dropped

    @model_validator(mode="after")
    def no_debug_logs_in_production(self):
        if self.ENVIRONMENT == "production" and self.AGENT_LOG_LEVEL.upper() == "DEBUG":
            raise ValueError("AGENT_LOG_LEVEL=DEBUG is not allowed in production: debug logs contain employee data")
        return self


settings = Settings()
