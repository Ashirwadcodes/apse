from abc import ABC, abstractmethod
from backend.models.technology import Technology, Source


class BaseSource(ABC):
    id: str
    name: str
    country: str
    institution: str
    status: str
    url: str
    ttl_seconds: int = 86400

    @abstractmethod
    async def search(self, query: str, filters: dict) -> tuple[list[Technology], int]:
        ...

    @abstractmethod
    def is_healthy(self) -> bool:
        ...

    def to_source_model(self) -> Source:
        return Source(
            id=self.id,
            name=self.name,
            country=self.country,
            institution=self.institution,
            status=self.status,
            url=self.url,
            ttl_seconds=self.ttl_seconds,
        )
