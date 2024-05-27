from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    alembic_database_url: str = ""
    database_url: str = ""
    number_of_fake_accounts: int = 0
    registry_base_url: str = ""
    registration_url: str = ""
    registration_timeout: int = 0
    base_url: str = ""
    swift: str = ""
    bank_name: str = ""
    bank_region: str = ""
    bank_country: str = ""
    toy_network_queue_name: str = ""
    public_key_path: str = ""
    private_key_path: str = ""

    model_config = SettingsConfigDict(env_file=".env")


@lru_cache
def get_settings() -> Settings:
    return Settings()
