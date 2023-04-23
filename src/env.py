import os

import dotenv

dotenv.load_dotenv()

APP_ENVIRONMENT = os.environ.get("APP_ENVIRONMENT", "development")


SECRET_KEY = os.environ.get("SECRET_KEY")
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS").split()

# Database
DB_ENGINE = os.environ.get("DB_ENGINE")
DB_HOST = os.environ.get("DB_HOST")
DB_PORT = os.environ.get("DB_PORT")
DB_NAME = os.environ.get("DB_NAME")
DB_USER = os.environ.get("DB_USER")
DB_PASSWORD = os.environ.get("DB_PASSWORD")

# Network security
CSRF_COOKIE_SAMESITE = os.environ.get("CSRF_COOKIE_SAMESITE")
CSRF_COOKIE_HTTPONLY = os.environ.get("CSRF_COOKIE_HTTPONLY")
CSRF_COOKIE_SECURE = os.environ.get("CSRF_COOKIE_SECURE")
CSRF_TRUSTED_ORIGINS = os.environ.get("CSRF_TRUSTED_ORIGINS")
SESSION_COOKIE_SAMESITE = os.environ.get("SESSION_COOKIE_SAMESITE")
SESSION_COOKIE_HTTPONLY = os.environ.get("SESSION_COOKIE_HTTPONLY")
SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE")
SECURE_HSTS_SECONDS = os.environ.get("SECURE_HSTS_SECONDS")
SECURE_HSTS_PRELOAD = os.environ.get("SECURE_HSTS_PRELOAD")
SECURE_SSL_REDIRECT = os.environ.get("SECURE_SSL_REDIRECT")
SECURE_HSTS_INCLUDE_SUBDOMAINS = os.environ.get("SECURE_HSTS_INCLUDE_SUBDOMAINS")

# Channels
REDIS_SERVER = os.environ.get("REDIS_SERVER", "localhost")
REDIS_PORT = os.environ.get("REDIS_PORT", 6379)
