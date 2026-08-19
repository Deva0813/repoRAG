from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    mongo_uri: str = "mongodb://localhost:27017/"
    db_name: str = "reporag"
    jwt_access_secret: str = "access_test"
    jwt_refresh_secret: str = "refresh_test"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    refresh_token_expire_days_max: int = 30
    cookie_secure: bool = True
    bcrypt_rounds: int = 12
    redis_url:str = ""
    public_key:str = "generate"
    private_key:str = "generate"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()

__all__=["settings"]
