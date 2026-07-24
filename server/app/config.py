from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FOOTSCAN_")

    db_url: str = "sqlite:///./footscan.db"
    data_dir: str = "./data"
    secret_key: str = "dev-secret-change-me"
    token_expire_minutes: int = 480
    admin_email: str = "admin@clinica.local"
    admin_password: str = "admin1234"
    admin_name: str = "Administrador"


settings = Settings()
