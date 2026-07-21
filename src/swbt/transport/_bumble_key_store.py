"""Bumble JSON key store metadata helpers."""

import copy
from pathlib import Path
from typing import Any, Protocol, cast

from swbt.diagnostics import DiagnosticsRecorder
from swbt.errors import InvalidKeyStoreError
from swbt.transport._pairing_profile import KeyStoreNamespaces, PairingProfile

PREVIOUS_NAMESPACE_PREFIX = "swbt.previous::"


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


class _CurrentPreviousProfileKeyStore:
    """Bumble-compatible JSON key store with one previous generation."""

    def __init__(
        self,
        *,
        filename: str | Path,
        namespace: str | None = None,
    ) -> None:
        if namespace is None:
            msg = "namespace is required"
            raise ValueError(msg)
        self._filename = Path(filename)
        self._namespace = namespace
        self.last_update_previous_saved = False

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

        return cast(
            "_BumbleJsonKeyStoreRuntime",
            JsonKeyStore(self._namespace, str(self._filename)),
        )

    def _previous_namespace(self, current_store: object) -> str:
        return f"{PREVIOUS_NAMESPACE_PREFIX}{cast('Any', current_store).namespace}"


class _PairingProfileNamespaceStore:
    """JsonKeyStore-compatible view over one profile namespace map."""

    def __init__(self, *, profile_path: Path, namespace: str) -> None:
        self._profile_path = profile_path
        self.namespace = namespace

    async def load(
        self,
    ) -> tuple[KeyStoreNamespaces, dict[str, dict[str, object]]]:
        profile = PairingProfile.load(self._profile_path)
        self._require_matching_identity(profile)
        namespaces = copy.deepcopy(profile.key_store_namespaces)
        current = namespaces.setdefault(self.namespace, {})
        return namespaces, current

    async def save(self, db: KeyStoreNamespaces) -> None:
        profile = PairingProfile.load(self._profile_path)
        self._require_matching_identity(profile)
        profile.with_key_store_namespaces(db).save(self._profile_path)

    async def get(self, name: str) -> object | None:
        for peer_address, peer_keys in await self.get_all():
            if peer_address == name:
                return peer_keys
        return None

    async def get_all(self) -> list[tuple[str, object]]:
        from bumble.keys import PairingKeys  # noqa: PLC0415

        _, key_map = await self.load()
        return [(name, PairingKeys.from_dict(cast("Any", keys))) for name, keys in key_map.items()]

    async def delete(self, name: str) -> None:
        db, key_map = await self.load()
        del key_map[name]
        await self.save(db)

    async def delete_all(self) -> None:
        db, key_map = await self.load()
        key_map.clear()
        await self.save(db)

    async def get_resolving_keys(self) -> object:
        from bumble.keys import KeyStore  # noqa: PLC0415

        return await KeyStore.get_resolving_keys(cast("Any", self))

    def _require_matching_identity(self, profile: PairingProfile) -> None:
        if str(profile.local_address) == self.namespace:
            return
        msg = "profile key-store namespace does not match local_address"
        raise InvalidKeyStoreError(msg)


class _PairingProfileKeyStore(_CurrentPreviousProfileKeyStore):
    """Current/previous Bumble key store persisted inside a profile envelope."""

    def __init__(self, *, profile_path: str | Path, namespace: str) -> None:
        super().__init__(filename=profile_path, namespace=namespace)

    def _current_store(self) -> _BumbleJsonKeyStoreRuntime:
        if self._namespace is None:
            msg = "profile key-store namespace is required"
            raise InvalidKeyStoreError(msg)
        return cast(
            "_BumbleJsonKeyStoreRuntime",
            _PairingProfileNamespaceStore(
                profile_path=self._filename,
                namespace=self._namespace,
            ),
        )


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
        if not isinstance(self._key_store, _CurrentPreviousProfileKeyStore):
            return {}
        return {
            "generation": "current",
            "previous_saved": self._key_store.last_update_previous_saved,
        }
