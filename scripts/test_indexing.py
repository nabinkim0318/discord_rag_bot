from rag_agent.indexing.embeddings import embed_texts

print(len(embed_texts(["hello", "world"])[0]))  # 384 같은 차원 나와야 함
