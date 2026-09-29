---
doc_id: keyword-index
title: Small corpus keyword indexing
---
# Small corpus keyword indexing

For a small local corpus, tokenize words consistently, normalize case, and rank documents by term relevance. A simple term-frequency and inverse-document-frequency score can reduce the influence of common words without a vector database.

Keep each document's stable ID alongside its text and score. The ranker should be deterministic so a debugging run can be repeated. A semantic index is not automatically better when the corpus is only a handful of short files.
