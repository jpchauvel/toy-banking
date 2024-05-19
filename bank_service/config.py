from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = ""
    number_of_fake_accounts: int = 0
    registry_url: str = ""
    swift: str = ""
    bank_nake: str = ""
    bank_region: str = ""
    bank_country: str = ""

    model_config = SettingsConfigDict(env_file=".env")


@lru_cache
def get_settings() -> Settings:
    return Settings()
