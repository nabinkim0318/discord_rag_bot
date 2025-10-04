from rag_agent.indexing.embeddings import embed_texts

print(len(embed_texts(["hello", "world"])[0]))  # Should output 384 dimensions
