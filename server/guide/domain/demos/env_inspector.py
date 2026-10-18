"""The env-inspector payload: a live read of the REAL AppConfig, redacted.

``build_env_inspector_payload`` shapes the panel topic 36's ``env:inspector``
serves INLINE in the pydantic-settings section: the environment name, one row
per ``AppConfig`` field (type from ``model_fields`` metadata, the frozen
instance's effective value, and an honest source attribution), the config's
own mechanics facts, and the flags sub-panel over the scenario store — the
repo's REAL runtime feature-flag mechanism, read through its live snapshot.

Two honesty rules shape the builder. Attribution is REAL introspection, never
a guess: each row asks ``EnvSettingsSource`` — the same source
pydantic-settings itself consults — whether this process's environment
provides the field; a field the source does not provide fell back to its
declared default, and the payload says which. And secret-bearing fields are
redacted BEFORE the payload exists as a value at all: the row carries the
word ``redacted`` plus a bare length hint, so no serialization path — JSON,
repr, log — can carry a live secret. The endpoint test pins that by serializing
the whole panel and asserting the live values appear nowhere in it.
"""

from collections.abc import Mapping
from typing import Any, Final, Literal

from pydantic_settings import EnvSettingsSource

from guide.core.config import AppConfig
from guide.core.scenario import ScenarioState
from guide.core.serialization import CamelModel

ENV_PREFIX: Final = "FDG_"
"""The prefix AppConfig's SettingsConfigDict declares — facts row + env names."""

SECRET_NAME_SUFFIXES: Final[tuple[str, ...]] = (
    "_secret",
    "_key",
    "_password",
)
"""A field whose name ends in any of these is secret-bearing and gets redacted."""

REDACTED_VALUE: Final = "redacted"
"""The only value a secret-bearing row ever carries — set, never rendered."""

SCENARIO_GET_PATH: Final = "/api/demo/scenario"
SCENARIO_PATCH_PATH: Final = "/api/demo/scenario"
"""The scenario store's real endpoints — the flags sub-panel's read and write."""


class SettingRow(CamelModel):
    """One AppConfig field: env-var name, type, effective value, source.

    ``value`` is the frozen instance's value stringified — or ``redacted``
    for secret-bearing fields, where only the ``shape_hint`` (a bare length)
    survives. ``source`` is real introspection: ``env`` when the environment
    source provides the field, ``default`` when it fell back.
    """

    name: str
    env_var: str
    type: str
    value: str
    source: Literal["env", "default"]
    secret: bool
    redacted: bool
    shape_hint: str | None = None


class ConfigFactsRow(CamelModel):
    """The config's own mechanics, read off the class — not restated."""

    env_prefix: str
    frozen: bool
    cache: str


class FlagsPanelRow(CamelModel):
    """The scenario sub-panel: the live flag snapshot + the real endpoints."""

    get_endpoint: str
    patch_endpoint: str
    data_mode: str
    inject_failure: str
    note: str


class EnvInspectorPanel(CamelModel):
    """Wire shape of ``GET /api/demo/env`` — the inspector's contract."""

    environment: str
    env_var: str
    facts: ConfigFactsRow
    settings: list[SettingRow]
    source_note: str
    redaction_note: str
    flags: FlagsPanelRow


SOURCE_NOTE: Final = (
    "Attribution is real introspection, not a guess: every row asks the same "
    "EnvSettingsSource pydantic-settings consults whether this process's "
    "environment provides the field — 'env' rows had a variable, 'default' "
    "rows fell back to the declared default. The value shown is always the "
    "frozen instance's effective value."
)

REDACTION_NOTE: Final = (
    "Secret-bearing fields (any *_secret / *_key / *_password — here "
    "jwt_secret and session_secret) are redacted server-side before this "
    "payload is built: the value never crosses the wire, only a length hint "
    "does. The endpoint test serializes the whole panel and asserts the live "
    "values appear nowhere in it."
)

FLAGS_NOTE: Final = (
    "The scenario store is this repo's real runtime feature-flag mechanism: "
    "dataMode switches demo data between fake and live stores, injectFailure "
    "switches healthy/error/latency behavior. PATCH is partial and "
    "enum-validated; state is per-app."
)

CACHE_FACT: Final = "one instance per process (get_config is lru_cache'd)"


def _env_provided() -> dict[str, Any]:
    """What the real environment source would provide, by field name.

    This is the exact source pydantic-settings consults (same class, same
    config), so the answer cannot drift from how AppConfig was built.
    """
    return dict(EnvSettingsSource(AppConfig)())


def _is_secret(name: str) -> bool:
    """Secret-bearing by name pattern — suffixes, not a hand-kept list."""
    return name.endswith(SECRET_NAME_SUFFIXES)


def build_env_inspector_payload(
    config: AppConfig,
    scenario: ScenarioState,
    env_provided: Mapping[str, Any] | None = None,
) -> EnvInspectorPanel:
    """Build the panel over the REAL config + the live scenario snapshot.

    ``env_provided`` lets tests pin attribution without touching the process
    environment; when omitted the real ``EnvSettingsSource`` is consulted —
    the same introspection the note on the wire describes.
    """
    provided = dict(env_provided) if env_provided is not None else _env_provided()
    settings: list[SettingRow] = []
    for name, field in AppConfig.model_fields.items():
        raw = getattr(config, name)
        secret = _is_secret(name)
        annotation: Any = field.annotation
        type_name = getattr(annotation, "__name__", str(annotation))
        if secret:
            value = REDACTED_VALUE
            shape_hint = f"{len(raw)} chars, hidden"
        else:
            value = str(raw)
            shape_hint = None
        source: Literal["env", "default"] = "env" if name in provided else "default"
        settings.append(
            SettingRow(
                name=name,
                env_var=f"{ENV_PREFIX}{name.upper()}",
                type=type_name,
                value=value,
                source=source,
                secret=secret,
                redacted=secret,
                shape_hint=shape_hint,
            )
        )
    return EnvInspectorPanel(
        environment=config.env,
        env_var=f"{ENV_PREFIX}ENV",
        facts=ConfigFactsRow(
            env_prefix=ENV_PREFIX,
            frozen=config.model_config.get("frozen") is True,
            cache=CACHE_FACT,
        ),
        settings=settings,
        source_note=SOURCE_NOTE,
        redaction_note=REDACTION_NOTE,
        flags=FlagsPanelRow(
            get_endpoint=SCENARIO_GET_PATH,
            patch_endpoint=SCENARIO_PATCH_PATH,
            data_mode=scenario.data_mode,
            inject_failure=scenario.inject_failure,
            note=FLAGS_NOTE,
        ),
    )
