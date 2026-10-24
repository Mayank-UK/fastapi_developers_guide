"""The content registry: validated topics + groups, single topic-id source.

``ContentRegistry`` validates EVERYTHING at construction and refuses to
exist otherwise — the module-level production instance is imported by
``create_app``, so broken content fails the process at startup (import
time), never at request time. Validation runs exactly once per registry;
tests construct fixture registries the same way, so bad fixtures fail in
the test that built them, not downstream.

Validation rules (each failure raises ``RegistryError`` naming the rule):
duplicate topic ids · duplicate section ids within a topic · duplicate
block ids within a topic · references to unknown groups · duplicate topic
orders · demo block ids not matching ``<area>:<name>`` (lowercase kebab) ·
sections with fewer than 2 blocks · sections without a text block ·
must-source code blocks lacking a non-empty ``source`` · must-source code
blocks with an empty ``snippet`` · empty text blocks · list blocks with
fewer than 3 or more than 8 items · list blocks with an empty item.
"""

import re
from collections.abc import Sequence
from typing import Final

from guide.content.models import (
    MUST_SOURCE_LANGUAGES,
    CodeBlock,
    ContentSummary,
    DemoBlock,
    ListBlock,
    TextBlock,
    Topic,
    TopicGroup,
)
from guide.content.topics.advanced_architecture import TOPIC as ADVANCED_ARCHITECTURE_TOPIC
from guide.content.topics.api_design import TOPIC as API_DESIGN_TOPIC
from guide.content.topics.api_documentation import TOPIC as API_DOCUMENTATION_TOPIC
from guide.content.topics.architecture import TOPIC as ARCHITECTURE_TOPIC
from guide.content.topics.authentication import TOPIC as AUTHENTICATION_TOPIC
from guide.content.topics.authorization import TOPIC as AUTHORIZATION_TOPIC
from guide.content.topics.background_jobs import TOPIC as BACKGROUND_JOBS_TOPIC
from guide.content.topics.best_practices import TOPIC as BEST_PRACTICES_TOPIC
from guide.content.topics.caching import TOPIC as CACHING_TOPIC
from guide.content.topics.databases_sql import TOPIC as DATABASES_SQL_TOPIC
from guide.content.topics.debugging import TOPIC as DEBUGGING_TOPIC
from guide.content.topics.dependency_management import TOPIC as DEPENDENCY_MANAGEMENT_TOPIC
from guide.content.topics.deployment import TOPIC as DEPLOYMENT_TOPIC
from guide.content.topics.environments import TOPIC as ENVIRONMENTS_TOPIC
from guide.content.topics.exception_handling import TOPIC as EXCEPTION_HANDLING_TOPIC
from guide.content.topics.fastapi_dependencies import TOPIC as FASTAPI_DEPENDENCIES_TOPIC
from guide.content.topics.fastapi_fundamentals import TOPIC as FASTAPI_FUNDAMENTALS_TOPIC
from guide.content.topics.files_media import TOPIC as FILES_MEDIA_TOPIC
from guide.content.topics.graphql import TOPIC as GRAPHQL_TOPIC
from guide.content.topics.grpc import TOPIC as GRPC_TOPIC
from guide.content.topics.http_web import TOPIC as HTTP_WEB_TOPIC
from guide.content.topics.internationalization import TOPIC as INTERNATIONALIZATION_TOPIC
from guide.content.topics.messaging import TOPIC as MESSAGING_TOPIC
from guide.content.topics.middleware import TOPIC as MIDDLEWARE_TOPIC
from guide.content.topics.mongodb import TOPIC as MONGODB_TOPIC
from guide.content.topics.observability import TOPIC as OBSERVABILITY_TOPIC
from guide.content.topics.performance import TOPIC as PERFORMANCE_TOPIC
from guide.content.topics.pydantic import TOPIC as PYDANTIC_TOPIC
from guide.content.topics.python_language import TOPIC as PYTHON_LANGUAGE_TOPIC
from guide.content.topics.python_runtime import TOPIC as PYTHON_RUNTIME_TOPIC
from guide.content.topics.realtime import TOPIC as REALTIME_TOPIC
from guide.content.topics.redis import TOPIC as REDIS_TOPIC
from guide.content.topics.reliability import TOPIC as RELIABILITY_TOPIC
from guide.content.topics.request_response import TOPIC as REQUEST_RESPONSE_TOPIC
from guide.content.topics.routing import TOPIC as ROUTING_TOPIC
from guide.content.topics.scaling import TOPIC as SCALING_TOPIC
from guide.content.topics.security import TOPIC as SECURITY_TOPIC
from guide.content.topics.sql_schema import TOPIC as SQL_SCHEMA_TOPIC
from guide.content.topics.sqlalchemy_orm import TOPIC as SQLALCHEMY_ORM_TOPIC
from guide.content.topics.testing import TOPIC as TESTING_TOPIC
from guide.content.topics.third_party import TOPIC as THIRD_PARTY_TOPIC
from guide.content.topics.validation import TOPIC as VALIDATION_TOPIC
from guide.content.topics.webhooks import TOPIC as WEBHOOKS_TOPIC

DEMO_ID_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[a-z0-9-]+:[a-z0-9-]+$")
"""Demo block ids are ``<area>:<name>`` (e.g. ``runtime:async``) — the client's lookup key."""

LIST_ITEMS_MIN: Final[int] = 3
LIST_ITEMS_MAX: Final[int] = 8
"""List blocks carry 3–8 items (block-selection standard): enough to be a real
enumeration, few enough to stay one scannable unit."""


class RegistryError(Exception):
    """A registry violated a validation rule; the message names it."""


def _validate(topics: Sequence[Topic], groups: Sequence[TopicGroup]) -> None:
    """Run every rule; raise RegistryError on the first violation."""
    known_group_ids = {group.id for group in groups}

    seen_topic_ids: set[str] = set()
    seen_orders: dict[int, str] = {}
    for topic in topics:
        if topic.id in seen_topic_ids:
            raise RegistryError(f"duplicate topic id: {topic.id!r}")
        seen_topic_ids.add(topic.id)

        if topic.group not in known_group_ids:
            raise RegistryError(
                f"unknown group: topic {topic.id!r} references group {topic.group!r} "
                "that the registry does not define"
            )

        if topic.order in seen_orders:
            raise RegistryError(
                f"duplicate topic order: {topic.order} used by "
                f"{seen_orders[topic.order]!r} and {topic.id!r}"
            )
        seen_orders[topic.order] = topic.id

        seen_section_ids: set[str] = set()
        seen_block_ids: set[str] = set()
        for section in topic.sections:
            if section.id in seen_section_ids:
                raise RegistryError(
                    f"duplicate section id: {section.id!r} in topic {topic.id!r}"
                )
            seen_section_ids.add(section.id)

            if len(section.blocks) < 2:
                raise RegistryError(
                    f"section too short: {section.id!r} in topic {topic.id!r} "
                    "needs at least 2 blocks"
                )
            if not any(isinstance(block, TextBlock) for block in section.blocks):
                raise RegistryError(
                    f"section without text block: {section.id!r} in topic {topic.id!r}"
                )

            for block in section.blocks:
                if block.id in seen_block_ids:
                    raise RegistryError(
                        f"duplicate block id: {block.id!r} in topic {topic.id!r}"
                    )
                seen_block_ids.add(block.id)

                if isinstance(block, TextBlock) and not block.text.strip():
                    raise RegistryError(f"empty text block: {block.id!r}")

                if isinstance(block, CodeBlock):
                    must_source = block.language in MUST_SOURCE_LANGUAGES
                    if must_source and not (block.source and block.source.strip()):
                        raise RegistryError(
                            f"unsourced code block: {block.id!r} language "
                            f"{block.language!r} requires a non-empty source path"
                        )
                    if must_source and not block.snippet.strip():
                        raise RegistryError(
                            f"empty snippet: {block.id!r} language {block.language!r} "
                            "requires a non-empty snippet"
                        )

                if isinstance(block, DemoBlock) and not DEMO_ID_PATTERN.match(block.id):
                    raise RegistryError(
                        f"invalid demo id: {block.id!r} must match "
                        "<area>:<name> with lowercase kebab segments"
                    )

                if isinstance(block, ListBlock):
                    if not LIST_ITEMS_MIN <= len(block.items) <= LIST_ITEMS_MAX:
                        raise RegistryError(
                            f"list block size: {block.id!r} has {len(block.items)} "
                            f"items; the standard allows {LIST_ITEMS_MIN}–{LIST_ITEMS_MAX}"
                        )
                    if any(not item.strip() for item in block.items):
                        raise RegistryError(
                            f"empty list item: {block.id!r} every item needs a "
                            "non-empty 'Lead term — explanation.'"
                        )


class ContentRegistry:
    """Immutable, fully validated set of topics and groups."""

    def __init__(self, topics: Sequence[Topic], groups: Sequence[TopicGroup]) -> None:
        """Validate then hold the content; RegistryError aborts construction."""
        _validate(topics, groups)
        self._topics: Final[tuple[Topic, ...]] = tuple(topics)
        self._groups: Final[tuple[TopicGroup, ...]] = tuple(groups)
        self._topics_by_id: Final[dict[str, Topic]] = {topic.id: topic for topic in self._topics}

    def summaries(self) -> list[ContentSummary]:
        """One summary per topic (registry order), with section counts."""
        return [
            ContentSummary(
                id=topic.id,
                title=topic.title,
                subtitle=topic.subtitle,
                group=topic.group,
                order=topic.order,
                section_count=len(topic.sections),
            )
            for topic in self._topics
        ]

    def topic_by_id(self, topic_id: str) -> Topic | None:
        """The full topic, or None when the id is unknown."""
        return self._topics_by_id.get(topic_id)

    def groups(self) -> list[TopicGroup]:
        """All groups (registry order)."""
        return list(self._groups)


# The production registry. Constructing it runs every validation rule at
# import time — this is the startup fail-fast create_app relies on. Topic
# modules live under content/topics/ (one per topic, importing their TOPIC
# here); groups register alongside their first topic.
production_registry: Final[ContentRegistry] = ContentRegistry(
    groups=[
        TopicGroup(id="foundations", title="Foundations", order=1),
        TopicGroup(id="framework", title="Framework", order=2),
        TopicGroup(id="request-handling", title="Request handling", order=3),
        TopicGroup(id="apis", title="APIs", order=4),
        TopicGroup(id="data", title="Data", order=5),
        TopicGroup(id="state-auth", title="State & auth", order=6),
        TopicGroup(id="media-realtime", title="Media & realtime", order=7),
        TopicGroup(id="platform", title="Platform", order=8),
        TopicGroup(id="ship", title="Ship", order=9),
        TopicGroup(id="capstones", title="Capstones", order=10),
    ],
    topics=[
        PYTHON_LANGUAGE_TOPIC,
        PYTHON_RUNTIME_TOPIC,
        HTTP_WEB_TOPIC,
        FASTAPI_FUNDAMENTALS_TOPIC,
        PYDANTIC_TOPIC,
        FASTAPI_DEPENDENCIES_TOPIC,
        ROUTING_TOPIC,
        MIDDLEWARE_TOPIC,
        REQUEST_RESPONSE_TOPIC,
        VALIDATION_TOPIC,
        API_DESIGN_TOPIC,
        API_DOCUMENTATION_TOPIC,
        GRAPHQL_TOPIC,
        WEBHOOKS_TOPIC,
        GRPC_TOPIC,
        SQL_SCHEMA_TOPIC,
        DATABASES_SQL_TOPIC,
        SQLALCHEMY_ORM_TOPIC,
        MONGODB_TOPIC,
        REDIS_TOPIC,
        CACHING_TOPIC,
        MESSAGING_TOPIC,
        AUTHENTICATION_TOPIC,
        AUTHORIZATION_TOPIC,
        SECURITY_TOPIC,
        FILES_MEDIA_TOPIC,
        INTERNATIONALIZATION_TOPIC,
        REALTIME_TOPIC,
        BACKGROUND_JOBS_TOPIC,
        EXCEPTION_HANDLING_TOPIC,
        DEPENDENCY_MANAGEMENT_TOPIC,
        ARCHITECTURE_TOPIC,
        OBSERVABILITY_TOPIC,
        TESTING_TOPIC,
        DEBUGGING_TOPIC,
        ENVIRONMENTS_TOPIC,
        DEPLOYMENT_TOPIC,
        PERFORMANCE_TOPIC,
        RELIABILITY_TOPIC,
        SCALING_TOPIC,
        BEST_PRACTICES_TOPIC,
        THIRD_PARTY_TOPIC,
        ADVANCED_ARCHITECTURE_TOPIC,
    ],
)
