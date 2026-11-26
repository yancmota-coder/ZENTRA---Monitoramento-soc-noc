from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "ZENTRA NOC API"
    app_env: str = "production"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    zabbix_url: str = ""
    zabbix_user: str = ""
    zabbix_password: str = ""
    zabbix_token: str = ""
    zabbix_verify_tls: bool = True
    zabbix_timeout: float = 15.0
    wazuh_url: str = ""
    wazuh_user: str = ""
    wazuh_password: str = ""
    wazuh_verify_tls: bool = True
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def origins(self) -> list[str]:
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]

settings = Settings()
