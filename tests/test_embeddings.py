import pytest

from app.services.rag.embeddings import EmbeddingError, HashEmbeddingProvider, get_embedding_provider
from app.core import config as config_module


def test_hash_embeddings_are_deterministic_and_normalized():
    provider = HashEmbeddingProvider(dimensions=32)
    first = provider.embed_query("hidden gems in Paris")
    second = provider.embed_query("hidden gems in Paris")
    other = provider.embed_query("tokyo metro tips")

    assert first == second
    assert first != other
    assert pytest.approx(sum(value * value for value in first), rel=1e-6) == 1.0


def test_hash_provider_embeds_documents_in_order():
    provider = HashEmbeddingProvider(dimensions=16)
    vectors = provider.embed_documents(["alpha", "beta"])
    assert len(vectors) == 2
    assert vectors[0] == provider.embed_query("alpha")


def test_embedding_factory_uses_hash_in_test_config():
    provider = get_embedding_provider()
    assert isinstance(provider, HashEmbeddingProvider)


def test_embedding_factory_rejects_unknown_provider(monkeypatch):
    monkeypatch.setattr(config_module.settings, "EMBEDDING_PROVIDER", "not-real")
    with pytest.raises(EmbeddingError):
        get_embedding_provider()
