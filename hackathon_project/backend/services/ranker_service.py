import sys
import os
from typing import List, Dict, Any
from flashrank import Ranker, RerankRequest

# Load ranker once (singleton)
try:
    # Use the default model which is very fast and lightweight (3MB)
    _ranker = Ranker(model_name="ms-marco-TinyBERT-L-2-v2")
    print("FlashRank BGE Reranker initialized successfully.")
except Exception as e:
    print(f"Warning: Failed to initialize FlashRank: {e}. Attempting fallback...")
    _ranker = Ranker()

def rank_requirements(query: str, requirements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Reranks a list of requirements using BGE reranking model from FlashRank based on the user's query.
    requirements is a list of dictionary representations of ExtractedRequirement.
    """
    if not query.strip() or not requirements:
        # Default sort by req_number if query is empty
        for r in requirements:
            r["score"] = 1.0
        return sorted(requirements, key=lambda x: x.get("req_number", ""))

    passages = []
    for req in requirements:
        passages.append({
            "id": str(req["id"]),
            "text": req["description"],
            "meta": req  # preserve the original dictionary
        })

    # Execute reranking
    rerank_request = RerankRequest(query=query, passages=passages)
    results = _ranker.rerank(rerank_request)

    ranked_list = []
    for r in results:
        meta = r["meta"]
        meta["score"] = float(r["score"])
        ranked_list.append(meta)

    return ranked_list
