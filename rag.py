"""Bangla/English retrieval over curated docs. Character trigram overlap works for Bangla without a tokenizer.
Swap `score` for pgvector cosine similarity over multilingual embeddings (e.g. multilingual-e5) in production."""
import re
from .models import Doc

def grams(t, n=3):
    t = re.sub(r"\s+", " ", t.lower())
    return {t[i:i + n] for i in range(max(len(t) - n + 1, 1))}

def score(q, text):
    a, b = grams(q), grams(text)
    return len(a & b) / (len(a) or 1)

def ask(db, q, threshold=0.18):
    bn = bool(re.search(r"[\u0980-\u09FF]", q))
    best, sc = None, 0
    for d in db.query(Doc).all():
        s = max(score(q, d.en), score(q, d.bn))
        if s > sc: best, sc = d, s
    if not best or sc < threshold:
        return {"answer": None, "message": "No reliable source found; this could not be verified. Please check the official notice."}
    return {"answer": best.bn if bn else best.en, "source": best.source, "last_verified": best.last_verified, "score": round(sc, 2)}
