"""ACIP embedding service client (M4).

Model-agnostic interface over a self-hosted embedding model (BGE-M3 /
Qwen3-Embedding) served by Text-Embeddings-Inference or any OpenAI-compatible
endpoint. Supports batching, Matryoshka (MRL) dimension truncation, and an
optional Redis-backed cache. Swapping the model is a config change, not code.
"""

from .client import EmbeddingClient, get_embedding_client

__all__ = ["EmbeddingClient", "get_embedding_client"]
