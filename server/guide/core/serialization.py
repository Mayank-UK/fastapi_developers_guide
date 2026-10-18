"""Shared pydantic wire conventions.

Every model that crosses the HTTP boundary derives from ``CamelModel``: python
fields stay snake_case while the wire is camelCase (``data_mode`` ⇄
``dataMode``), parsing accepts BOTH spellings (``populate_by_name``), and
instances are frozen — wire models are immutable snapshots, never mutated
in place. Content models and scenario state both build on this base, so the
camelCase rule is defined exactly once.
"""

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """Base for every wire model: camelCase aliases, both-direction parsing, frozen."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        frozen=True,
    )
