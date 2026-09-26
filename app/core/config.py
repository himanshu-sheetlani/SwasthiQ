from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "SwasthiQ Backend"
    VERSION: str = "0.1.0"

    class Config:
        env_file = ".env"

settings = Settings()
