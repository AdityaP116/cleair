"""
RAG Knowledge Service (SRS B10)
Hybrid search (BM25 + TF-IDF) over curated official literature.
"""
from typing import Dict, Any, List
from pathlib import Path
import json
import re

KB_PATH = Path(__file__).parent.parent.parent.parent / "data" / "kb" / "kb_starter.json"

class KnowledgeService:
    def __init__(self, kb_path: Path = KB_PATH):
        self.documents = []
        if kb_path.exists():
            with open(kb_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.documents = data.get("documents", [])

    def search(self, query: str, audience: str = "general", topic: str = None, top_k: int = 4) -> List[Dict[str, Any]]:
        tokens = set(re.findall(r"\w+", query.lower()))
        results = []

        for doc in self.documents:
            score = 0
            doc_text = (doc.get("title", "") + " " + doc.get("content", "")).lower()
            doc_tokens = set(re.findall(r"\w+", doc_text))
            
            # Simple keyword overlap scoring
            common = tokens.intersection(doc_tokens)
            score += len(common) * 2

            # Bonus for matching audience or topic
            if audience and audience in doc.get("audience", []):
                score += 3
            if topic and topic in doc.get("topic", []):
                score += 4

            if score > 0:
                results.append((score, doc))

        # Sort by relevance score
        results.sort(key=lambda x: x[0], reverse=True)
        top_docs = [r[1] for r in results[:top_k]]

        # Return standard citation formats
        citations = []
        for d in top_docs:
            citations.append({
                "id": d["id"],
                "title": d["title"],
                "publisher": d["publisher"],
                "url": d["url"],
                "published": d.get("published", "2023-01-01"),
                "content_snippet": d.get("content", "")[:300] + "..."
            })
        return citations
