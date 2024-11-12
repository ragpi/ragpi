from src.document.schemas import Document


def reciprocal_rank_fusion(
    results: list[list[Document]], num_results: int, constant: int = 60
) -> list[Document]:
    scores: dict[str, float] = {}
    for docs in results:
        for rank, doc in enumerate(docs):
            scores[doc.id] = scores.get(doc.id, 0) + 1 / (rank + constant)

    sorted_doc_ids = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    top_doc_ids = [doc_id for doc_id, _ in sorted_doc_ids[:num_results]]

    id_to_doc = {doc.id: doc for result in results for doc in result}

    return [id_to_doc[doc_id] for doc_id in top_doc_ids]
