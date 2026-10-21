import os


class Config:
    DATABASE = os.environ.get("DATABASE", "service_desk.db")
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
    JWT_EXPIRES_MINUTES = int(os.environ.get("JWT_EXPIRES_MINUTES", "60"))
    PASSWORD_ITERATIONS = 100_000
