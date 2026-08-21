from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+psycopg2://autoparty:autoparty@db:5432/autoparty"
    JWT_SECRET: str = "change-me-in-production-autoparty-demo-secret"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

    SEARCH_PRICE_KGS: int = 200
    SEARCH_CURRENCY: str = "KGS"
    PUBLIC_URL: str = "http://localhost"
    UPLOAD_DIR: str = "/data/uploads"
    MAX_UPLOAD_MB: int = 5
    ORDER_EXPIRE_DAYS: int = 7

    # TODO: replace demo payment flow with O!Bank payment API/webhook
    DEMO_PAYMENT_REDIRECT_URL: str = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    # TODO: replace seller registration placeholder with real seller registration service
    SELLER_REGISTRATION_URL: str = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    DEMO_PASSWORD: str = "qweasdzxc"

    DISTRIBUTION_HIGH_DELAY_SECONDS: int = 0
    DISTRIBUTION_MEDIUM_DELAY_SECONDS: int = 10
    DISTRIBUTION_LOW_DELAY_SECONDS: int = 30
    DISTRIBUTION_HIGH_THRESHOLD: float = 70.0
    DISTRIBUTION_MEDIUM_THRESHOLD: float = 40.0


settings = Settings()
