---
doc_id: retrieval-grounding
title: Grounding answers in retrieved documents
---
# Grounding answers in retrieved documents

Retrieval should return a small set of relevant source documents with stable document IDs. The synthesis step should receive those sources and answer from their contents. Cite the source IDs so a reviewer can inspect the evidence.

When retrieval finds no useful evidence, the agent should say that the corpus does not answer the question. A plausible answer is not a grounded answer. Do not let planning notes or a tool result turn into an unsupported factual claim.
