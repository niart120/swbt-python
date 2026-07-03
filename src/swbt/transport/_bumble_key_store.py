"""Bumble JSON key store metadata helpers."""

import copy
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, cast

from swbt.diagnostics import DiagnosticsRecorder
from swbt.errors import InvalidKeyStoreError

PREVIOUS_NAMESPACE_PREFIX = "swbt.previous::"


@dataclass(frozen=True)
class KeyStoreMetadata:
    """Observed metadata for a Bumble JSON key store file."""

    exists: bool
    previous_exists: bool


def read_key_store_metadata(key_store_path: str | Path) -> KeyStoreMetadata:
    """Read non-sensitive metadata from a Bumble JSON key store file."""
    path = Path(key_store_path)
    if not path.exists():
        return KeyStoreMetadata(exists=False, previous_exists=False)
    return KeyStoreMetadata(
        exists=True,
        previous_exists=_previous_generation_exists(path),
    )


def _previous_generation_exists(key_store_path: Path) -> bool:
    try:
        key_store_data = json.loads(key_store_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    if not isinstance(key_store_data, dict):
        return False
    return any(str(namespace).startswith(PREVIOUS_NAMESPACE_PREFIX) for namespace in key_store_data)


class _BumbleJsonKeyStoreRuntime(Protocol):
    namespace: str

    async def load(
        self,
    ) -> tuple[dict[str, dict[str, dict[str, object]]], dict[str, dict[str, object]]]:
        """Load the full JSON DB and this store's current key map."""

    async def save(self, db: dict[str, dict[str, dict[str, object]]]) -> None:
        """Save the full JSON DB."""

    async def get(self, name: str) -> object | None:
        """Return one key entry."""

    async def get_all(self) -> list[tuple[str, object]]:
        """Return all current key entries."""

    async def delete(self, name: str) -> None:
        """Delete one current key entry."""

    async def delete_all(self) -> None:
        """Delete all current key entries."""

    async def get_resolving_keys(self) -> object:
        """Return LE resolving keys for Bumble internals."""


class _CurrentPreviousJsonKeyStore:
    """Bumble-compatible JSON key store with one previous generation."""

    def __init__(
        self,
        *,
        filename: str | Path,
        namespace: str | None = None,
        device: object | None = None,
    ) -> None:
        if namespace is None and device is None:
            msg = "namespace or device is required"
            raise ValueError(msg)
        self._filename = Path(filename)
        self._namespace = namespace
        self._device = device
        self.last_update_previous_saved = False

    @classmethod
    def from_device(
        cls,
        device: object,
        *,
        filename: str | Path,
    ) -> "_CurrentPreviousJsonKeyStore":
        """Create a store whose namespace follows the Bumble device address."""
        return cls(filename=filename, device=device)

    async def update(self, name: str, keys: object) -> None:
        """Write current keys and keep the overwritten current value as previous."""
        current_store = self._current_store()
        db, current_key_map = await current_store.load()
        previous_namespace = self._previous_namespace(current_store)
        previous_key_map = copy.deepcopy(current_key_map)
        self.last_update_previous_saved = bool(previous_key_map)
        if previous_key_map:
            db[previous_namespace] = previous_key_map
        else:
            db.pop(previous_namespace, None)
        current_key_map.clear()
        current_key_map[name] = cast("Any", keys).to_dict()
        await current_store.save(db)

    async def get(self, name: str) -> object | None:
        """Return one current key entry."""
        for peer_address, peer_keys in await self.get_all():
            if peer_address == name:
                return peer_keys
        return None

    async def get_all(self) -> list[tuple[str, object]]:
        """Return current key entries only."""
        entries = await self._current_store().get_all()
        if len(entries) > 1:
            msg = "key store contains multiple current peers"
            raise InvalidKeyStoreError(msg)
        return entries

    async def delete(self, name: str) -> None:
        """Delete one current key entry."""
        await self._current_store().delete(name)

    async def delete_all(self) -> None:
        """Delete all current key entries."""
        await self._current_store().delete_all()

    async def get_resolving_keys(self) -> object:
        """Return current LE resolving keys for Bumble internals."""
        return await self._current_store().get_resolving_keys()

    def _current_store(self) -> _BumbleJsonKeyStoreRuntime:
        from bumble.keys import JsonKeyStore  # noqa: PLC0415

        if self._device is not None:
            return cast(
                "_BumbleJsonKeyStoreRuntime",
                JsonKeyStore.from_device(
                    cast("Any", self._device),
                    filename=str(self._filename),
                ),
            )
        return cast(
            "_BumbleJsonKeyStoreRuntime",
            JsonKeyStore(self._namespace, str(self._filename)),
        )

    def _previous_namespace(self, current_store: object) -> str:
        return f"{PREVIOUS_NAMESPACE_PREFIX}{cast('Any', current_store).namespace}"


class _DiagnosticKeyStore:
    """Key store wrapper that records write outcome without logging key material."""

    def __init__(self, key_store: object, diagnostics: DiagnosticsRecorder) -> None:
        self._key_store = key_store
        self._diagnostics = diagnostics

    async def update(self, name: str, keys: object) -> None:
        """Record key-store write success or failure."""
        try:
            await cast("Any", self._key_store).update(name, keys)
        except Exception as error:
            fields = self._generation_fields()
            self._diagnostics.record_event(
                "key_store_update",
                **fields,
                error_type=type(error).__name__,
                message=str(error),
                peer_address=name,
                status="failed",
            )
            raise
        fields = self._generation_fields()
        self._diagnostics.record_event(
            "key_store_update",
            **fields,
            peer_address=name,
            status="succeeded",
        )

    async def get(self, name: str) -> object | None:
        """Delegate key lookup."""
        return await cast("Any", self._key_store).get(name)

    async def get_all(self) -> list[tuple[str, object]]:
        """Delegate full key listing."""
        return await cast("Any", self._key_store).get_all()

    async def delete(self, name: str) -> None:
        """Delegate key deletion."""
        await cast("Any", self._key_store).delete(name)

    async def delete_all(self) -> None:
        """Delegate all-key deletion."""
        await cast("Any", self._key_store).delete_all()

    async def get_resolving_keys(self) -> object:
        """Delegate LE resolving-key lookup for Bumble internals."""
        return await cast("Any", self._key_store).get_resolving_keys()

    def __getattr__(self, name: str) -> object:
        return getattr(self._key_store, name)

    def _generation_fields(self) -> dict[str, object]:
        if not isinstance(self._key_store, _CurrentPreviousJsonKeyStore):
            return {}
        return {
            "generation": "current",
            "previous_saved": self._key_store.last_update_previous_saved,
        }
