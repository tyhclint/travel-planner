from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from hashlib import sha1
from pathlib import Path
import re
from typing import Any, Protocol

from app.core.config import get_settings
from app.domain.models.preferences import TravelPreferences
from app.domain.models.recommendations import DestinationRecommendation
from app.domain.models.trip import TripRequirements
from app.services.chroma import get_chroma_client
from app.services.search.base import SearchService
REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_RESOURCES_DIR = REPO_ROOT / "app" / "resources"
DEFAULT_RESULT_COUNT = 5
MAX_CHUNK_CHARS = 900
CHUNK_OVERLAP_CHARS = 150


class EmbeddingModel(Protocol):
    def embed_documents(
        self, texts: list[str], chunk_size: int | None = None, **kwargs: Any
    ) -> list[list[float]]: ...

    def embed_query(self, text: str, **kwargs: Any) -> list[float]: ...


@lru_cache(maxsize=1)
def get_embedding_model() -> EmbeddingModel:
    settings = get_settings()
    return LocalSentenceTransformerEmbedder(settings.embedding_model)


class LocalSentenceTransformerEmbedder:
    """Local sentence-transformers wrapper matching the RAG embedding protocol."""

    def __init__(self, model_name: str) -> None:
        from sentence_transformers import SentenceTransformer

        self.model_name = model_name
        self.model = SentenceTransformer(model_name)

    def embed_documents(
        self, texts: list[str], chunk_size: int | None = None, **kwargs: Any
    ) -> list[list[float]]:
        del chunk_size, kwargs
        if not texts:
            return []
        return self._encode(texts)

    def embed_query(self, text: str, **kwargs: Any) -> list[float]:
        del kwargs
        return self._encode([text])[0]

    def _encode(self, texts: list[str]) -> list[list[float]]:
        embeddings = self.model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
            convert_to_numpy=True,
        )
        return embeddings.tolist()


@dataclass(frozen=True)
class MarkdownChunk:
    chunk_id: str
    document: str
    metadata: dict[str, str | int]


@dataclass(frozen=True)
class IndexingStats:
    collection_name: str
    documents_indexed: int
    chunks_indexed: int


class MarkdownDestinationIndexer:
    def __init__(
        self,
        *,
        resources_dir: Path = DEFAULT_RESOURCES_DIR,
        collection_name: str | None = None,
        embedder: EmbeddingModel | None = None,
    ) -> None:
        settings = get_settings()
        self.resources_dir = resources_dir
        self.collection_name = collection_name or settings.chroma_destination_collection
        self.embedder = embedder or get_embedding_model()
        self.client = get_chroma_client()

    def index_documents(self, reset_collection: bool = False) -> IndexingStats:
        files = sorted(self.resources_dir.glob("**/*.md"))
        if reset_collection:
            try:
                self.client.delete_collection(name=self.collection_name)
            except Exception:
                pass

        collection = self.client.get_or_create_collection(name=self.collection_name)
        chunks = [
            chunk
            for path in files
            for chunk in _chunk_markdown_file(path, base_dir=self.resources_dir)
        ]
        if not chunks:
            return IndexingStats(
                collection_name=self.collection_name,
                documents_indexed=0,
                chunks_indexed=0,
            )

        embeddings = self.embedder.embed_documents([chunk.document for chunk in chunks])
        collection.upsert(
            ids=[chunk.chunk_id for chunk in chunks],
            documents=[chunk.document for chunk in chunks],
            embeddings=embeddings,
            metadatas=[chunk.metadata for chunk in chunks],
        )
        return IndexingStats(
            collection_name=self.collection_name,
            documents_indexed=len(files),
            chunks_indexed=len(chunks),
        )


class MarkdownRAGSearchService(SearchService):
    def __init__(
        self,
        *,
        collection_name: str | None = None,
        embedder: EmbeddingModel | None = None,
    ) -> None:
        settings = get_settings()
        self.collection_name = collection_name or settings.chroma_destination_collection
        self.embedder = embedder or get_embedding_model()
        self.client = get_chroma_client()

    def search_destination(
        self,
        requirements: TripRequirements,
        preferences: TravelPreferences,
    ) -> list[DestinationRecommendation]:
        collection = self.client.get_or_create_collection(name=self.collection_name)
        if collection.count() == 0:
            raise RuntimeError(
                "Destination knowledge base is empty. Run the MCP indexing tool first."
            )

        query_embedding = self.embedder.embed_query(
            _build_destination_query(requirements, preferences)
        )
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=DEFAULT_RESULT_COUNT,
            include=["documents", "metadatas"],
        )

        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        recommendations: list[DestinationRecommendation] = []
        seen_names: set[str] = set()

        for document, metadata in zip(documents, metadatas, strict=False):
            if not metadata:
                continue
            name = str(metadata.get("section_title") or metadata.get("document_title") or "Guide")
            if name in seen_names:
                continue
            seen_names.add(name)
            recommendations.append(
                DestinationRecommendation(
                    name=name,
                    category=str(metadata.get("category") or "destination"),
                    description=_build_recommendation_description(str(document)),
                    location=str(metadata.get("location")) if metadata.get("location") else None,
                    source_url=str(metadata.get("source_url")) if metadata.get("source_url") else None,
                )
            )

        return recommendations


def _build_destination_query(
    requirements: TripRequirements, preferences: TravelPreferences
) -> str:
    parts = [
        f"Destination: {requirements.destination or 'flexible'}",
        f"Budget: {requirements.budget or 'unspecified'} {requirements.currency}",
        f"Trip length: {requirements.trip_length_days or 'unspecified'} days",
        f"Travel style: {preferences.overall_style}",
        f"Activity pace: {preferences.activity_pace}",
    ]
    if preferences.interests:
        parts.append(f"Interests: {', '.join(preferences.interests)}")
    return " | ".join(parts)


def _chunk_markdown_file(
    path: Path, *, base_dir: Path = DEFAULT_RESOURCES_DIR
) -> list[MarkdownChunk]:
    raw_text = path.read_text(encoding="utf-8").strip()
    if not raw_text:
        return []

    relative_path = path.relative_to(base_dir)
    continent = _humanize(relative_path.parts[0]) if len(relative_path.parts) > 0 else "Unknown"
    country = _humanize(relative_path.parts[1]) if len(relative_path.parts) > 1 else "Unknown"
    city = _humanize(path.stem)
    location = f"{city}, {country}"

    document_title, sections = _parse_markdown_sections(raw_text, city)
    chunks: list[MarkdownChunk] = []

    for section_index, (section_title, section_body) in enumerate(sections):
        category = _infer_category(section_title)
        for chunk_index, chunk_text in enumerate(_chunk_section_text(section_body)):
            identity = f"{relative_path.as_posix()}::{section_index}::{chunk_index}"
            chunks.append(
                MarkdownChunk(
                    chunk_id=sha1(identity.encode("utf-8")).hexdigest(),
                    document=chunk_text,
                    metadata={
                        "continent": continent,
                        "country": country,
                        "city": city,
                        "location": location,
                        "document_title": document_title,
                        "section_title": section_title,
                        "category": category,
                        "source_path": str(path),
                        "source_url": path.resolve().as_uri(),
                        "section_index": section_index,
                        "chunk_index": chunk_index,
                    },
                )
            )

    return chunks


def _parse_markdown_sections(
    raw_text: str, fallback_title: str
) -> tuple[str, list[tuple[str, str]]]:
    document_title = fallback_title
    current_title = "Overview"
    current_lines: list[str] = []
    sections: list[tuple[str, str]] = []

    for line in raw_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            document_title = stripped[2:].strip() or fallback_title
            continue
        if stripped.startswith("## "):
            _append_section(sections, current_title, current_lines)
            current_title = stripped[3:].strip() or "Overview"
            current_lines = []
            continue
        if stripped == "---":
            continue
        current_lines.append(line)

    _append_section(sections, current_title, current_lines)
    return document_title, sections


def _append_section(
    sections: list[tuple[str, str]], title: str, lines: list[str]
) -> None:
    content = "\n".join(lines).strip()
    if content:
        sections.append((title, content))


def _chunk_section_text(section_text: str) -> list[str]:
    blocks = [
        _normalize_block(block)
        for block in re.split(r"\n\s*\n", section_text)
        if block.strip()
    ]
    if not blocks:
        return []

    chunks: list[str] = []
    current = ""
    for block in blocks:
        candidate = block if not current else f"{current}\n\n{block}"
        if len(candidate) <= MAX_CHUNK_CHARS:
            current = candidate
            continue

        if current:
            chunks.append(current)
        if len(block) <= MAX_CHUNK_CHARS:
            current = block
            continue

        overflow_chunks = _window_text(block)
        chunks.extend(overflow_chunks[:-1])
        current = overflow_chunks[-1]

    if current:
        chunks.append(current)
    return chunks


def _normalize_block(block: str) -> str:
    lines = [line.strip() for line in block.splitlines() if line.strip()]
    return "\n".join(lines)


def _window_text(text: str) -> list[str]:
    chunks: list[str] = []
    start = 0
    while start < len(text):
        tentative_end = min(start + MAX_CHUNK_CHARS, len(text))
        if tentative_end < len(text):
            split_at = max(
                text.rfind(". ", start, tentative_end),
                text.rfind("\n", start, tentative_end),
                text.rfind(" ", start, tentative_end),
            )
            end = tentative_end if split_at <= start else split_at + 1
        else:
            end = tentative_end

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break
        next_start = max(end - CHUNK_OVERLAP_CHARS, start + 1)
        start = next_start

    return chunks


def _infer_category(section_title: str) -> str:
    lowered = section_title.lower()
    if "food" in lowered or "eat" in lowered:
        return "food"
    if "stay" in lowered or "hotel" in lowered:
        return "stay"
    if "practical" in lowered or "connectivity" in lowered or "getting around" in lowered:
        return "practical"
    if "trip" in lowered:
        return "day_trip"
    if "itinerary" in lowered or "day " in lowered:
        return "itinerary"
    if "best time" in lowered:
        return "seasonality"
    return "destination"


def _build_recommendation_description(document: str) -> str:
    flattened = " ".join(document.split())
    if len(flattened) <= 280:
        return flattened
    return f"{flattened[:277].rstrip()}..."


def _humanize(value: str) -> str:
    return value.replace("-", " ").replace("_", " ").title()
