"""Result[T]: failures as values — access, mapping, and wrong-access errors."""

import dataclasses

import pytest

from guide.core.errors import AppError, FailureKind
from guide.core.result import Err, Ok, UnwrapError


def test_ok_holds_value_and_flags_success() -> None:
    result = Ok(41)
    assert result.is_ok() is True
    assert result.is_err() is False
    assert result.value == 41


def test_err_holds_failure_and_flags_failure() -> None:
    failure = AppError(FailureKind.NOT_FOUND, "missing")
    result = Err(failure)
    assert result.is_ok() is False
    assert result.is_err() is True
    assert result.failure is failure


def test_value_on_err_raises_and_failure_on_ok_raises() -> None:
    with pytest.raises(UnwrapError):
        _ = Err(AppError(FailureKind.INTERNAL, "x")).value
    with pytest.raises(UnwrapError):
        _ = Ok(1).failure


def test_map_transforms_ok_and_passes_err_through() -> None:
    assert Ok(2).map(lambda n: n * 10).value == 20

    failure = AppError(FailureKind.CONFLICT, "clash")
    passed = Err(failure).map(lambda n: n * 10)
    assert passed.is_err() is True
    assert passed.failure is failure


def test_unwrap_or_returns_value_or_fallback() -> None:
    assert Ok("real").unwrap_or("fallback") == "real"
    assert Err(AppError(FailureKind.NOT_FOUND, "x")).unwrap_or("fallback") == "fallback"


def test_result_fits_declared_union_for_any_t() -> None:
    from guide.core.result import Result

    ok_side: Result[int] = Ok(3)
    err_side: Result[int] = Err(AppError(FailureKind.INTERNAL, "x"))
    assert ok_side.unwrap_or(0) == 3
    assert err_side.unwrap_or(0) == 0


def test_variants_are_frozen() -> None:
    result = Ok(1)
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.value = 2  # type: ignore[misc]
