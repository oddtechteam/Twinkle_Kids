"""In-process object store for tests and credential-free local development."""

from threading import Lock
from urllib.parse import quote

from app.domain.entities.health import ComponentHealth, ComponentState
from app.domain.entities.media import StoredObject
from app.domain.errors import NotFoundError


class InMemoryObjectStorage:
    def __init__(self, base_url: str = "memory://storage") -> None:
        self._objects: dict[tuple[str, str], StoredObject] = {}
        self._lock = Lock()
        self._base_url = base_url.rstrip("/")

    def put(
        self, bucket: str, key: str, data: bytes, *, content_type: str, cache_control: str
    ) -> None:
        with self._lock:
            self._objects[(bucket, key)] = StoredObject(data=data, content_type=content_type)

    def get(self, bucket: str, key: str) -> StoredObject:
        with self._lock:
            try:
                return self._objects[(bucket, key)]
            except KeyError:
                raise NotFoundError("Object not found.") from None

    def exists(self, bucket: str, key: str) -> bool:
        with self._lock:
            return (bucket, key) in self._objects

    def delete(self, bucket: str, key: str) -> None:
        with self._lock:
            self._objects.pop((bucket, key), None)

    def public_url(self, bucket: str, key: str) -> str:
        return f"{self._base_url}/{quote(bucket)}/{quote(key)}"

    def presigned_url(self, bucket: str, key: str, *, expires_in: int) -> str:
        return f"{self.public_url(bucket, key)}?expires_in={expires_in}"

    def __len__(self) -> int:
        return len(self._objects)


class InMemoryStorageHealthProbe:
    def check(self) -> ComponentHealth:
        return ComponentHealth("storage", ComponentState.OK, latency_ms=0.0, detail="in-memory")
