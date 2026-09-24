---
name: rag
description: Knowledge retrieval and semantic document search standards with user and thread isolation.
---

# RAG & Knowledge Retrieval Skill

1. **Isolation First**:
   - Always filter ChromaDB chunks by `thread_id` and `user_id`.
   - Never leak documents from one user or thread to another.

2. **Relevance & Grounding**:
   - Search with focused queries extracted from user intent.
   - Quote or synthesize facts directly from retrieved document snippets.
   - If information is not in the knowledge base, state clearly that the uploaded documents do not contain the answer.

3. **Citations**:
   - Attribute facts to source document filenames (e.g., `[From: QuarterlyReport.pdf]`).
