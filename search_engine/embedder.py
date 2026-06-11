from sentence_transformers import SentenceTransformer

_model = None
MODEL_NAME = "all-MiniLM-L6-v2"


def init_embedder():
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def embed_texts(texts):
    model = init_embedder()
    return model.encode(texts, normalize_embeddings=True, show_progress_bar=False)


def embed_query(query):
    return embed_texts([query])[0]
