from src.document_store.schemas import Document


def reciprocal_rank_fusion(
    ranked_lists: list[list[Document]], top_k: int, constant: int = 60
) -> list[Document]:
    scores: dict[str, float] = {}
    for docs in ranked_lists:
        for rank, doc in enumerate(docs):
            scores[doc.id] = scores.get(doc.id, 0) + 1 / (rank + constant)

    sorted_doc_ids = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    top_doc_ids = [doc_id for doc_id, _ in sorted_doc_ids[:top_k]]

    id_to_doc = {doc.id: doc for docs in ranked_lists for doc in docs}

    return [id_to_doc[doc_id] for doc_id in top_doc_ids]
