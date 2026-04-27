from app.core.config import Settings


def test_settings_load_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./test.db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6380/1")

    settings = Settings()

    assert settings.environment == "test"
    assert settings.database_url == "sqlite:///./test.db"
    assert settings.redis_url == "redis://localhost:6380/1"
