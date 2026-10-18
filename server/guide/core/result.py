"""``Result[T]``: failures as values, not exceptions.

Use cases return ``Ok(value)`` or ``Err(AppError(...))`` so control flow stays
explicit and the presentation edge decides how a failure maps onto HTTP
(the domain never throws across layers). The variant types are frozen
dataclasses; accessing the wrong payload (``.value`` on ``Err``, ``.failure``
on ``Ok``) raises ``UnwrapError`` — a programming error, loudly surfaced.

Typing note: ``Err`` carries no phantom ``T`` parameter, so ``Err(...)`` fits
any ``Result[T]`` without variance gymnastics; ``.value``/``.failure`` are
declared on both variants (typed ``Never`` where impossible) so attribute
access on the union stays mypy-strict-clean while still raising at runtime.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Never, final

from guide.core.errors import AppError


class UnwrapError(Exception):
    """Raised on accessing the payload a Result variant does not hold."""


@final
@dataclass(frozen=True, slots=True)
class Ok[T]:
    """The success variant; holds exactly one value."""

    value: T

    def is_ok(self) -> bool:
        return True

    def is_err(self) -> bool:
        return False

    @property
    def failure(self) -> Never:
        """Always raises: an Ok holds no failure."""
        raise UnwrapError(".failure accessed on Ok")

    def map[U](self, fn: Callable[[T], U]) -> "Ok[U]":
        """Transform the success value."""
        return Ok(fn(self.value))

    def unwrap_or(self, fallback: T) -> T:
        """Return the success value (the fallback is unused on Ok)."""
        return self.value


@final
@dataclass(frozen=True, slots=True)
class Err:
    """The failure variant; holds exactly one AppError."""

    failure: AppError

    def is_ok(self) -> bool:
        return False

    def is_err(self) -> bool:
        return True

    @property
    def value(self) -> Never:
        """Always raises: an Err holds no value."""
        raise UnwrapError(".value accessed on Err")

    def map[U](self, fn: Callable[[Never], U]) -> "Err":
        """Pass-through: an Err never invokes the transform.

        ``Callable[[Never], U]`` accepts any callable (parameters are
        contravariant and Never is the bottom type), so calling ``.map`` on
        ``Ok[T] | Err`` type-checks and joins to ``Ok[U] | Err``.
        """
        return self

    def unwrap_or[U](self, fallback: U) -> U:
        """Return the fallback (an Err holds no value)."""
        return fallback


type Result[T] = Ok[T] | Err
