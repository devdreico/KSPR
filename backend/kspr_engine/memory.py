"""KSPR Autonomous Cognitive OS: Vectorial Memory and Semantic Search Engine."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any


class VectorMemory:
    def __init__(self, memory_dir: Path | None = None):
        self.memory_dir = memory_dir or (Path.cwd() / "memory")
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.memory_dir / "vector_index.json"
        self._load_index()

    def _load_index(self) -> None:
        if self.index_file.is_file():
            try:
                self.documents = json.loads(self.index_file.read_text(encoding="utf-8"))
            except Exception:
                self.documents = []
        else:
            self.documents = []

    def _save_index(self) -> None:
        self.index_file.write_text(json.dumps(self.documents, ensure_ascii=False, indent=2), encoding="utf-8")

    def _simple_embedding(self, text: str) -> list[float]:
        """Genera un vector de características léxicas/semánticas ligero para indexación offline."""
        import hashlib
        words = text.lower().split()
        vector = [0.0] * 64
        for w in words:
            h = int(hashlib.md5(w.encode()).hexdigest(), 16)
            idx = h % 64
            vector[idx] += 1.0
        # Normalizar vector
        magnitude = math.sqrt(sum(v * v for v in vector))
        if magnitude > 0:
            vector = [v / magnitude for v in vector]
        return vector

    def add_document(self, doc_id: str, content: str, metadata: dict[str, Any] | None = None) -> None:
        embedding = self._simple_embedding(content)
        # Reemplazar si ya existe
        self.documents = [d for d in self.documents if d["id"] != doc_id]
        self.documents.append({
            "id": doc_id,
            "content": content,
            "metadata": metadata or {},
            "vector": embedding
        })
        self._save_index()

    def search(self, query: str, top_k: int = 3) -> list[dict[str, Any]]:
        if not self.documents:
            return []
        q_vec = self._simple_embedding(query)
        scored = []
        for doc in self.documents:
            doc_vec = doc["vector"]
            similarity = sum(q * d for q, d in zip(q_vec, doc_vec))
            scored.append((similarity, doc))
        
        scored.sort(key=lambda x: x[0], reverse=True)
        return [{
            "id": doc["id"],
            "content": doc["content"],
            "metadata": doc["metadata"],
            "score": round(score, 4)
        } for score, doc in scored[:top_k]]
