"""The deps-manifest payload: the REAL pyproject.toml + uv.lock, parsed live.

``build_dep_manifest_payload`` shapes the panel topic 31's ``deps:manifest``
serves INLINE in the uv tree/audit section. Both dependency files live inside
``server/`` — the manifest and the lock sit right beside the code they build —
so the running server container bind-mounts them and the demo reads them AT
REQUEST TIME (the env-inspector precedent of introspecting real files, not
restating them). The panel answers four questions honestly:

- Groups — what ``[project] dependencies`` (runtime, ships to prod) versus the
  PEP 735 ``[dependency-groups] dev`` block (tooling, never shipped) declare.
- Locked vs constrained — for EVERY direct dependency, the manifest's range
  beside the lock's exact pin, with the range checked against the pin.
- Drift — a manifest/lock agreement cross-check in the spirit of
  ``uv lock --check``: every name the manifest declares must appear as a
  direct dependency of the ``guide`` entry in the lock, and no extras.
- Direct vs transitive — a one-level slice rooted at ``fastapi`` (the
  ``uv tree`` view, parsed from the lock), plus whole-lock counts.

Two honesty rules shape the builder. Everything shown is PARSED, never
restated: versions, constraints, and the slice come from the two real files,
so a future ``uv lock`` run changes the panel without anyone touching it. And
the range check judges only operators it understands (``>=`` and ``==``);
anything else returns ``None`` and the row says "not judged" rather than
guessing — the same honest-degradation posture the best-checklist's manual
rows take. If either file cannot be read, the panel degrades to
``available: false`` with the reason instead of failing the request.
"""

import re
import tomllib
from pathlib import Path
from typing import Any, Final, Literal

from guide.core.serialization import CamelModel

PROJECT_NAME: Final = "guide"
"""The lock entry whose direct dependencies ARE this project's manifest."""

SLICE_ROOT: Final = "fastapi"
"""The curated tree root: the one dependency every FastAPI app shares."""

_SERVER_ROOT: Final[Path] = Path(__file__).resolve().parents[3]
"""guide/domain/demos → guide/domain → guide → server/ (owns both files)."""

MANIFEST_PATH: Final[Path] = _SERVER_ROOT / "pyproject.toml"
LOCK_PATH: Final[Path] = _SERVER_ROOT / "uv.lock"

MANIFEST_DISPLAY: Final = "server/pyproject.toml"
LOCK_DISPLAY: Final = "server/uv.lock"
"""Repo-root-relative display paths — what the reader can open."""

_DEP_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)\s*(?:\[([^\]]*)\])?\s*(.*)$"
)
"""PEP 508-ish requirement string: name, optional [extras], specifier."""

LockDoc = dict[str, Any]
"""One parsed TOML document (tomllib returns plain dicts; typed at the seam)."""


class GroupRow(CamelModel):
    """One dependency group: who declared it and what installing it means."""

    group: Literal["main", "dev"]
    title: str
    declared_in: str
    direct_count: int
    note: str


class DirectDepRow(CamelModel):
    """One direct dependency: the manifest's range beside the lock's pin.

    ``satisfies`` is the honest range check — ``True``/``False`` for the
    operators this builder judges, ``None`` ("not judged") for anything
    more complex than a single ``>=`` or ``==`` clause.
    """

    name: str
    group: Literal["main", "dev"]
    constraint: str
    locked_version: str
    satisfies: bool | None
    extras: str
    """Extras the manifest requests ('asyncio' for sqlalchemy[asyncio])."""


class TransitiveRow(CamelModel):
    """One edge of the tree slice: a package the root pulls in."""

    name: str
    locked_version: str


class TransitiveSlice(CamelModel):
    """The direct-vs-transitive view: one root, one level, all locked pins."""

    root: str
    root_constraint: str
    root_locked_version: str
    children: list[TransitiveRow]
    note: str


class LockCounts(CamelModel):
    """The whole lock in three numbers."""

    total_locked: int
    direct: int
    transitive: int
    note: str


class AgreementRow(CamelModel):
    """The ``uv lock --check`` spirit, computed: manifest names vs lock names."""

    manifest_names: int
    lock_names: int
    missing_from_lock: list[str]
    extra_in_lock: list[str]
    agree: bool


class DepsManifestPanel(CamelModel):
    """Wire shape of ``GET /api/demo/deps`` — the manifest panel's contract."""

    manifest_file: str
    lock_file: str
    available: bool
    unavailable_reason: str | None = None
    requires_python: str | None = None
    groups: list[GroupRow] = []
    direct: list[DirectDepRow] = []
    slice: TransitiveSlice | None = None
    counts: LockCounts | None = None
    agreement: AgreementRow | None = None
    honesty_note: str


HONESTY_NOTE: Final = (
    "Every row is parsed at request time from the two real files named above "
    "— relock the project and this panel changes with it, no code involved. "
    "The range check judges only single >= or == clauses; anything else "
    "reads 'not judged' rather than guessing."
)

_MAIN_GROUP_NOTE: Final = (
    "Ships to prod: uv sync --locked installs exactly these, and the prod "
    "image's --no-dev build carries only them."
)

_DEV_GROUP_NOTE: Final = (
    "Tooling that never ships: uv sync installs the dev group by default, "
    "image builds pass --no-dev to skip it."
)

_SLICE_NOTE: Final = (
    "The uv tree view, one level deep: fastapi's locked pin and the packages "
    "it pulls in that nobody wrote down in the manifest — every one of them "
    "is a dependency you own anyway."
)


def _split_requirement(requirement: str) -> tuple[str, list[str], str]:
    """Split a PEP 508-ish requirement into (name, extras, specifier)."""
    match = _DEP_PATTERN.match(requirement)
    if match is None:
        return requirement.strip(), [], ""
    extras_raw = match.group(2) or ""
    extras = [extra.strip() for extra in extras_raw.split(",") if extra.strip()]
    return match.group(1), extras, match.group(3).strip()


def _version_tuple(version: str) -> tuple[int, ...] | None:
    """Numeric dotted version, or None when a suffix makes comparison unsafe."""
    try:
        return tuple(int(part) for part in version.strip().split("."))
    except ValueError:
        return None


def _satisfies(locked_version: str, constraint: str) -> bool | None:
    """Honest single-clause range check; None when the operator is not judged.

    Only ``>=`` and ``==``/``===`` are judged, and only over plain dotted
    numeric versions — a pre-release suffix or a compound clause returns
    ``None`` so the row can say "not judged" instead of guessing.
    """
    spec = constraint.strip()
    if "," in spec or not spec:
        return None
    for operator in (">=", "==", "==="):
        if spec.startswith(operator):
            locked = _version_tuple(locked_version)
            wanted = _version_tuple(spec[len(operator) :])
            if locked is None or wanted is None:
                return None
            return locked >= wanted if operator == ">=" else locked == wanted
    return None


def _package_index(lock: LockDoc) -> dict[str, LockDoc]:
    """The lock's [[package]] entries keyed by name."""
    index: dict[str, LockDoc] = {}
    for package in lock.get("package", []):
        name = package.get("name")
        if isinstance(name, str):
            index[name] = package
    return index


def _lock_version(index: dict[str, LockDoc], name: str) -> str:
    """One package's locked version, or an honest '?' when absent."""
    version = index.get(name, {}).get("version")
    return version if isinstance(version, str) else "?"


def _dep_names(package: LockDoc, key: str) -> list[str]:
    """Dependency names under ``dependencies`` or a dev-dependencies group."""
    if key == "dependencies":
        entries: Any = package.get("dependencies", [])
    else:
        entries = package.get("dev-dependencies", {}).get("dev", [])
    names: list[str] = []
    for entry in entries:
        name = entry.get("name")
        if isinstance(name, str):
            names.append(name)
    return names


def _degraded(reason: str) -> DepsManifestPanel:
    """The honest unavailable panel: why, and nothing composed."""
    return DepsManifestPanel(
        manifest_file=MANIFEST_DISPLAY,
        lock_file=LOCK_DISPLAY,
        available=False,
        unavailable_reason=reason,
        honesty_note=HONESTY_NOTE,
    )


def build_dep_manifest_payload(
    manifest_path: Path = MANIFEST_PATH,
    lock_path: Path = LOCK_PATH,
) -> DepsManifestPanel:
    """Build the panel over the REAL manifest + lock (or given paths).

    ``manifest_path`` / ``lock_path`` exist for the degradation tests; the
    default reads the two files the running server is built from, at request
    time, so the wire always shows the dependency world as it IS.
    """
    try:
        manifest_text = manifest_path.read_text(encoding="utf-8")
        lock_text = lock_path.read_text(encoding="utf-8")
    except OSError as exc:
        return _degraded(f"{type(exc).__name__}: {exc}")

    manifest: LockDoc = tomllib.loads(manifest_text)
    lock: LockDoc = tomllib.loads(lock_text)

    project: Any = manifest.get("project", {})
    main_requirements = [str(req) for req in project.get("dependencies", [])]
    dev_requirements = [
        str(req)
        for req in manifest.get("dependency-groups", {}).get("dev", [])
    ]
    requires_python = project.get("requires-python")
    if not isinstance(requires_python, str):
        requires_python = None

    index = _package_index(lock)
    guide_entry = index.get(PROJECT_NAME, {})
    lock_main = _dep_names(guide_entry, "dependencies")

    groups = [
        GroupRow(
            group="main",
            title="Runtime dependencies",
            declared_in="pyproject.toml [project] dependencies",
            direct_count=len(main_requirements),
            note=_MAIN_GROUP_NOTE,
        ),
        GroupRow(
            group="dev",
            title="Dev group",
            declared_in="pyproject.toml [dependency-groups] dev",
            direct_count=len(dev_requirements),
            note=_DEV_GROUP_NOTE,
        ),
    ]

    direct: list[DirectDepRow] = []
    for group, requirements in (("main", main_requirements), ("dev", dev_requirements)):
        for requirement in requirements:
            name, extras, specifier = _split_requirement(requirement)
            locked_version = _lock_version(index, name)
            direct.append(
                DirectDepRow(
                    name=name,
                    group=group,
                    constraint=specifier,
                    locked_version=locked_version,
                    satisfies=_satisfies(locked_version, specifier),
                    extras=", ".join(extras),
                )
            )

    manifest_names = {name for name, _, _ in map(_split_requirement, main_requirements)}
    lock_names = set(lock_main)
    agreement = AgreementRow(
        manifest_names=len(manifest_names),
        lock_names=len(lock_names),
        missing_from_lock=sorted(manifest_names - lock_names),
        extra_in_lock=sorted(lock_names - manifest_names),
        agree=manifest_names == lock_names,
    )

    root = index.get(SLICE_ROOT, {})
    children = [
        TransitiveRow(name=name, locked_version=_lock_version(index, name))
        for name in _dep_names(root, "dependencies")
    ]
    root_constraint = next(
        (row.constraint for row in direct if row.name == SLICE_ROOT),
        "",
    )
    tree_slice = TransitiveSlice(
        root=SLICE_ROOT,
        root_constraint=root_constraint,
        root_locked_version=_lock_version(index, SLICE_ROOT),
        children=children,
        note=_SLICE_NOTE,
    )

    direct_count = len(direct)
    transitive = len(index) - direct_count - 1  # minus the guide entry itself
    counts = LockCounts(
        total_locked=len(index),
        direct=direct_count,
        transitive=transitive,
        note=(
            f"{len(index)} locked entries include the guide project itself; the "
            f"direct {direct_count} are the names the manifest declares, and the "
            "rest arrived as edges of somebody else's graph."
        ),
    )

    return DepsManifestPanel(
        manifest_file=MANIFEST_DISPLAY,
        lock_file=LOCK_DISPLAY,
        available=True,
        requires_python=requires_python,
        groups=groups,
        direct=direct,
        slice=tree_slice,
        counts=counts,
        agreement=agreement,
        honesty_note=HONESTY_NOTE,
    )
