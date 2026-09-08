from pathlib import Path

import pytest

from app.domain.models.preferences import TravelPreferences
from app.domain.models.trip import TripRequirements
from app.services.search import rag
from app.services.search.rag import MarkdownDestinationIndexer, MarkdownRAGSearchService


class FakeEmbedder:
    def embed_documents(self, texts: list[str], chunk_size: int | None = None, **kwargs):
        del chunk_size, kwargs
        return [[float(index), 0.5] for index, _ in enumerate(texts, start=1)]

    def embed_query(self, text: str, **kwargs):
        del text, kwargs
        return [0.25, 0.75]


class FakeCollection:
    def __init__(self, *, count_value: int = 0, query_result: dict | None = None):
        self.count_value = count_value
        self.query_result = query_result or {"documents": [[]], "metadatas": [[]]}
        self.upsert_payload: dict | None = None

    def upsert(self, **kwargs):
        self.upsert_payload = kwargs
        self.count_value = len(kwargs["ids"])

    def count(self):
        return self.count_value

    def query(self, **kwargs):
        del kwargs
        return self.query_result


class FakeClient:
    def __init__(self, collection: FakeCollection):
        self.collection = collection
        self.deleted_collections: list[str] = []

    def get_or_create_collection(self, name: str):
        del name
        return self.collection

    def delete_collection(self, name: str):
        self.deleted_collections.append(name)


def _build_test_resources(tmp_path: Path) -> Path:
    resources_dir = tmp_path / "resources"
    files = {
        resources_dir / "asia" / "japan" / "tokyo.md": """
# Tokyo, Japan

## Overview
Tokyo is a large city with strong food, shopping, and transit convenience.

## Food Notes
Try ramen, sushi, and neighborhood izakaya across different districts.
""",
        resources_dir / "asia" / "japan" / "kyoto.md": """
# Kyoto, Japan

## Overview
Kyoto is strong for temples, gardens, and slower-paced cultural travel.
""",
        resources_dir / "asia" / "china" / "beijing.md": """
# Beijing, China

## Overview
Beijing mixes imperial landmarks, food, and large city logistics.

## Practical Tips
Use the subway to avoid traffic during peak hours.
""",
    }
    for path, content in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content.strip(), encoding="utf-8")
    return resources_dir


def test_chunk_markdown_file_extracts_resource_metadata(tmp_path: Path):
    resources_dir = _build_test_resources(tmp_path)
    path = resources_dir / "asia" / "japan" / "tokyo.md"

    chunks = rag._chunk_markdown_file(path, base_dir=resources_dir)

    assert chunks
    assert chunks[0].metadata["city"] == "Tokyo"
    assert chunks[0].metadata["country"] == "Japan"
    assert chunks[0].metadata["source_path"].endswith("tokyo.md")


def test_indexer_vector_encodes_before_upsert(monkeypatch, tmp_path: Path):
    resources_dir = _build_test_resources(tmp_path)
    collection = FakeCollection()
    client = FakeClient(collection)
    monkeypatch.setattr(rag, "get_chroma_client", lambda: client)

    indexer = MarkdownDestinationIndexer(
        resources_dir=resources_dir,
        embedder=FakeEmbedder(),
    )
    stats = indexer.index_documents(reset_collection=True)

    assert stats.documents_indexed == 3
    assert stats.chunks_indexed > 3
    assert client.deleted_collections == [stats.collection_name]
    assert collection.upsert_payload is not None
    assert len(collection.upsert_payload["documents"]) == stats.chunks_indexed
    assert len(collection.upsert_payload["embeddings"]) == stats.chunks_indexed


def test_search_service_returns_destination_recommendations(monkeypatch):
    collection = FakeCollection(
        count_value=2,
        query_result={
            "documents": [[
                "Tokyo is excellent for first-time visitors interested in food and transit convenience.",
                "Asakusa works well for slower-paced cultural walks.",
            ]],
            "metadatas": [[
                {
                    "section_title": "Food notes",
                    "category": "food",
                    "location": "Tokyo, Japan",
                    "source_url": "file:///tmp/tokyo.md",
                },
                {
                    "section_title": "Where to stay",
                    "category": "stay",
                    "location": "Tokyo, Japan",
                    "source_url": "file:///tmp/tokyo.md",
                },
            ]],
        },
    )
    monkeypatch.setattr(rag, "get_chroma_client", lambda: FakeClient(collection))

    service = MarkdownRAGSearchService(embedder=FakeEmbedder())
    results = service.search_destination(
        TripRequirements(destination="Tokyo", trip_length_days=5),
        TravelPreferences(interests=["food", "culture"]),
    )

    assert [result.name for result in results] == ["Food notes", "Where to stay"]
    assert results[0].category == "food"
    assert results[0].location == "Tokyo, Japan"


def test_search_service_requires_indexed_collection(monkeypatch):
    monkeypatch.setattr(rag, "get_chroma_client", lambda: FakeClient(FakeCollection()))

    service = MarkdownRAGSearchService(embedder=FakeEmbedder())

    with pytest.raises(RuntimeError, match="Run the MCP indexing tool first"):
        service.search_destination(TripRequirements(destination="Tokyo"), TravelPreferences())
