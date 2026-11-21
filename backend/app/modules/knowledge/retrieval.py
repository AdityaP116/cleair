from typing import Dict, Any, List
from pathlib import Path
import json
import re

KB_STARTER_PATH = Path(__file__).resolve().parents[4] / "data" / "kb" / "kb_starter.json"

class KnowledgeRetrieval:
    def __init__(self, kb_path: Path = KB_STARTER_PATH):
        if not kb_path.exists():
            kb_path = Path("data/kb/kb_starter.json")
        self.documents = []
        if kb_path.exists():
            with open(kb_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.documents = data.get("documents", [])

    def search(self, query: str, audience: str = "general", topic: str = None, top_k: int = 3) -> List[Dict[str, Any]]:
        tokens = set(re.findall(r"\w+", query.lower()))
        scored = []
        for doc in self.documents:
            score = 0
            text = (doc.get("title", "") + " " + doc.get("content", "")).lower()
            doc_tokens = set(re.findall(r"\w+", text))
            common = tokens.intersection(doc_tokens)
            score += len(common) * 2

            if audience and audience in doc.get("audience", []):
                score += 3
            if topic and topic in doc.get("topic", []):
                score += 4

            if score > 0:
                scored.append((score, doc))

        scored.sort(key=lambda x: x[0], reverse=True)
        top = [d for s, d in scored[:top_k]]
        
        # If no query matches, return top default official references
        if not top and self.documents:
            top = self.documents[:top_k]

        citations = []
        for d in top:
            citations.append({
                "id": d["id"],
                "title": d["title"],
                "publisher": d["publisher"],
                "url": d["url"],
                "published": d.get("published", "2023-01-01"),
                "content_snippet": d.get("content", "")[:300] + "..."
            })
        return citations

knowledge_retrieval = KnowledgeRetrieval()
