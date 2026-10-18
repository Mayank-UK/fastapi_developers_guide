"""Application configuration via pydantic-settings.

Every knob reads from an ``FDG_``-prefixed environment variable (``FDG_ENV``,
``FDG_DEBUG``, ...) with dev-safe defaults, so the app boots anywhere with
zero secrets and compose overrides stay explicit. Instances are frozen:
settings are read-only after startup. ``get_config()`` caches one instance
per process; tests that vary the environment construct ``AppConfig()``
directly or clear the cache.
"""

from functools import lru_cache
from typing import Self

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEV_ENV: str = "dev"
"""The one environment the dev-default signing secrets may boot in."""


class AppConfig(BaseSettings):
    """Process-wide settings; each field name doubles as its env var name."""

    model_config = SettingsConfigDict(env_prefix="FDG_", frozen=True)

    env: str = "dev"
    debug: bool = False
    database_url: str = "postgresql+asyncpg://postgres:guide@localhost:5432/guide"
    redis_url: str = "redis://localhost:6379"
    mongo_url: str = "mongodb://localhost:27017"
    log_level: str = "info"
    # The two signing secrets (topic 23): dev-only defaults let the stack boot
    # anywhere with zero setup, and NOTHING behind them is secret in dev — but
    # production MUST override both via FDG_JWT_SECRET / FDG_SESSION_SECRET
    # (distinct, high-entropy values); the validator below makes a default
    # secret in a non-dev env a startup failure instead of a quiet liability.
    jwt_secret: str = "dev-only-jwt-secret-override-me-32+chars"
    session_secret: str = "dev-only-session-secret-override-me-32+chars"

    @model_validator(mode="after")
    def _refuse_dev_secrets_outside_dev(self) -> Self:
        """Fail fast: a dev-default ``*_secret`` must never boot outside dev.

        Runs wherever the config is constructed — ``create_app()`` and the
        arq worker both build their config at startup, so a prod deployment
        that forgot ``FDG_JWT_SECRET`` / ``FDG_SESSION_SECRET`` (or any
        future ``*_secret``) dies at boot naming the env vars to set,
        instead of signing cookies and tokens with a public default.
        """
        if self.env == _DEV_ENV:
            return self
        defaults = type(self).model_fields
        unset = [
            f"FDG_{name.upper()}"
            for name, field in defaults.items()
            if name.endswith("_secret") and getattr(self, name) == field.get_default()
        ]
        if unset:
            raise ValueError(
                f"env={self.env!r} refuses dev-default signing secrets: "
                f"{', '.join(unset)} must be set to real high-entropy values "
                f"(distinct from each other) before the app may start"
            )
        return self


@lru_cache(maxsize=1)
def get_config() -> AppConfig:
    """Return the process-wide config instance (one per process)."""
    return AppConfig()
