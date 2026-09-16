from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    secret_key: str
    database_url: str = "sqlite:///./gastos.db"
    access_token_expire_minutes: int = 30
    log_level: str = "INFO"
    mcp_demo_email: str = "demo@curso.com"
    mcp_demo_password: str = "demo1234"
    mcp_issuer_url: str = "http://127.0.0.1:8000"
    mcp_resource_url: str = "http://127.0.0.1:8000/mcp"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
