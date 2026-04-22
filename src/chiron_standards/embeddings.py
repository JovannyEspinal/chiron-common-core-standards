from __future__ import annotations
import numpy as np
from openai import OpenAI

EMBED_MODEL = "text-embedding-3-small"
EMBED_DIM = 1536

def embed_texts(texts: list[str], client: OpenAI | None = None) -> np.ndarray:
    """Embed a list of texts. Returns a (len(texts), EMBED_DIM) float32 array."""
    client = client or OpenAI()
    response = client.embeddings.create(model=EMBED_MODEL, input=texts)
    vectors = [d.embedding for d in response.data]

    return np.array(vectors, dtype=np.float32)

