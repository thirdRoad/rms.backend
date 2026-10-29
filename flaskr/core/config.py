import os
import secrets
from datetime import timedelta

# https://flask.palletsprojects.com/en/stable/config/#SECRET_KEY


class Config:
    # Flask-Core
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "asd123")
    DEBUG: bool = False
    TESTING: bool = False
    JSON_SORT_KEYS: bool = False
    MAX_CONTENT_LENGTH: int = 33_554_432

    # SQLAlchemy
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    SQLALCHEMY_ECHO: bool = False
    SQLALCHEMY_DATABASE_URI = os.environ.get("SQLALCHEMY_DATABASE_URI")

    # Flask-Migrate
    FLASK_MIGRATE_TABLE: str = "alembic_version"

    # Flask-Mail
    MAIL_SERVER: str = os.environ.get("MAIL_SERVER")
    MAIL_PORT: int = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_SSL: bool = True
    MAIL_USERNAME: str = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD: str = os.environ.get("MAIL_PASSWORD")

    # Flask-Cache
    CACHE_TYPE: str = os.environ.get("CACHE_TYPE", "simple")
    CACHE_REDIS_URL: str = os.environ.get("REDIS_URL")

    # Flask-JWT
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "321dsa")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=15)
    # JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30) -> we enable next feature.

    # Flask-CORS
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "http://localhost:5173")
    CORS_SUPPORTS_CREDENTIALS: bool = False
    CORS_ALLOW_HEADERS = ["Content-Type", "Authorization"]
    CORS_METHODS = ["GET", "POST", "PATCH", "DELETE"]


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_ECHO = True


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(seconds=5)
    SECRET_KEY = secrets.token_urlsafe(32)
    JWT_SECRET_KEY = secrets.token_urlsafe(32)


# Not yet ready.
class ProductionConfig(Config):
    SECRET_KEY = os.environ.get("SECRET_KEY")
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY")


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "prod": ProductionConfig,
}
