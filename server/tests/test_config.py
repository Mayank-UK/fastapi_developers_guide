"""AppConfig behavior: FDG_ prefix parsing, defaults, immutability, caching,
and the startup fail-fast that refuses dev-default secrets outside dev."""

import pytest
from pydantic import ValidationError

from guide.core.config import AppConfig, get_config

FDG_VARS = (
    "FDG_ENV",
    "FDG_DEBUG",
    "FDG_DATABASE_URL",
    "FDG_REDIS_URL",
    "FDG_MONGO_URL",
    "FDG_LOG_LEVEL",
)

REAL_JWT_SECRET = "a-real-production-jwt-secret-with-plenty-of-entropy"
REAL_SESSION_SECRET = "a-real-production-session-secret-different-from-jwt"


def test_env_prefix_is_parsed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FDG_ENV", "prod")
    monkeypatch.setenv("FDG_DEBUG", "true")
    monkeypatch.setenv("FDG_LOG_LEVEL", "warning")
    monkeypatch.setenv("FDG_JWT_SECRET", REAL_JWT_SECRET)
    monkeypatch.setenv("FDG_SESSION_SECRET", REAL_SESSION_SECRET)
    config = AppConfig()
    assert config.env == "prod"
    assert config.debug is True
    assert config.log_level == "warning"
    assert config.jwt_secret == REAL_JWT_SECRET


def test_unprefixed_env_is_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENV", "prod")
    assert AppConfig().env == "dev"


def test_defaults_apply(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in FDG_VARS:
        monkeypatch.delenv(name, raising=False)
    config = AppConfig()
    assert config.env == "dev"
    assert config.debug is False
    assert config.database_url == "postgresql+asyncpg://postgres:guide@localhost:5432/guide"
    assert config.redis_url == "redis://localhost:6379"
    assert config.mongo_url == "mongodb://localhost:27017"
    assert config.log_level == "info"


def test_config_is_frozen() -> None:
    config = AppConfig()
    with pytest.raises(ValidationError):
        config.env = "prod"


def test_get_config_is_cached() -> None:
    get_config.cache_clear()
    try:
        assert get_config() is get_config()
    finally:
        get_config.cache_clear()


def test_dev_boots_with_the_default_secrets() -> None:
    """The dev direction of the fail-fast: defaults are legal in dev."""
    config = AppConfig()  # env defaults to "dev" — no secrets overridden
    assert config.env == "dev"
    assert config.jwt_secret == "dev-only-jwt-secret-override-me-32+chars"
    assert config.session_secret == "dev-only-session-secret-override-me-32+chars"


def test_non_dev_with_dev_default_secrets_fails_fast() -> None:
    """Outside dev, dev-default secrets refuse construction naming the vars."""
    with pytest.raises(ValidationError, match=r"env='prod'.*FDG_JWT_SECRET.*FDG_SESSION_SECRET"):
        AppConfig(env="prod")


@pytest.mark.parametrize("env", ["prod", "staging", "test"])
def test_every_non_dev_env_refuses_the_dev_defaults(env: str) -> None:
    """The gate is `env != dev`, not a hardcoded prod literal."""
    with pytest.raises(ValidationError, match="refuses dev-default signing secrets"):
        AppConfig(env=env)


def test_non_dev_with_one_default_secret_left_names_only_that_var() -> None:
    """Partial compliance still fails, naming exactly the missing rail."""
    with pytest.raises(ValidationError, match=r"FDG_SESSION_SECRET") as exc_info:
        AppConfig(env="prod", jwt_secret=REAL_JWT_SECRET)
    assert "FDG_JWT_SECRET" not in str(exc_info.value)


def test_non_dev_with_real_secrets_boots() -> None:
    """The pass direction: real secrets make any env legal."""
    config = AppConfig(
        env="prod", jwt_secret=REAL_JWT_SECRET, session_secret=REAL_SESSION_SECRET
    )
    assert config.env == "prod"
    assert config.jwt_secret == REAL_JWT_SECRET


def test_create_app_surfaces_the_fail_fast_at_app_factory_time(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The boot-time proof: an app built outside dev without real secrets
    dies at create_app() (get_config() → AppConfig() → validator)."""
    monkeypatch.setenv("FDG_ENV", "prod")
    monkeypatch.delenv("FDG_JWT_SECRET", raising=False)
    monkeypatch.delenv("FDG_SESSION_SECRET", raising=False)
    get_config.cache_clear()
    from guide.main import create_app

    try:
        with pytest.raises(ValidationError, match="FDG_JWT_SECRET"):
            create_app()
    finally:
        monkeypatch.delenv("FDG_ENV", raising=False)
        get_config.cache_clear()
