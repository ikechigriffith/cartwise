from dataclasses import dataclass

from app.config import get_settings


@dataclass(frozen=True)
class RetailerCredentials:
    username: str | None
    password: str | None

    @property
    def available(self) -> bool:
        return bool(self.username and self.password)


def get_retailer_credentials(retailer_key: str) -> RetailerCredentials:
    settings = get_settings()
    key = retailer_key.lower().replace(" ", "_").replace("-", "_")

    if key == "pricesmart":
        return RetailerCredentials(settings.pricesmart_username, settings.pricesmart_password)
    if key in {"jta", "jta_supermarkets", "jta_supermarket"}:
        return RetailerCredentials(settings.jta_username, settings.jta_password)

    return RetailerCredentials(None, None)
