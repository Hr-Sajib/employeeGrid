from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_JWT_SECRET = "dev-only-secret-change-me"

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    DB_CONNECTION: str
    OPENROUTER_API_KEY: str
    JINA_API_KEY: str

    ENVIRONMENT: str = "development"   # the container sets "production"
    PUBLIC_ORIGIN: str = ""            # e.g. https://chat.example.com: the only origin allowed to open the chat socket
    JWT_SECRET: str = DEFAULT_JWT_SECRET   # set a long random value for real use
    JWT_EXPIRE_MINUTES: int = 480

    RATE_LIMIT_PER_MINUTE: int = 10    # chat messages per user per minute
    DAILY_BUDGET_USD: float = 0.50     # model spend per user per UTC day

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
    def production_needs_a_real_secret(self):
        if self.ENVIRONMENT == "production" and (self.JWT_SECRET == DEFAULT_JWT_SECRET or len(self.JWT_SECRET) < 32):
            raise ValueError("ENVIRONMENT=production needs JWT_SECRET set to at least 32 random characters")
        if self.ENVIRONMENT == "production" and self.AGENT_LOG_LEVEL.upper() == "DEBUG":
            raise ValueError("AGENT_LOG_LEVEL=DEBUG is not allowed in production: debug logs contain employee data")
        return self


settings = Settings()
