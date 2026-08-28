---
name: {{SLUG}}-router
description: Routes {{SLUG}} conceptual questions to the skill and factual questions to knowledge-rag.
metadata:
  type: router
  generated_by: docops
---

# {{SLUG}}-router

Load the `{{SLUG}}` skill for conceptual and behavioral questions.

For literal, version-sensitive, signature, default, endpoint, changelog or configuration questions, call the MCP tool `search_knowledge` before answering.

Every factual claim grounded in RAG must include an inline source citation such as `path/to/file.md#section` or `path/to/file.md:line`.

For ambiguous or high-risk decisions, combine the skill's rationale with RAG confirmation and explicitly report divergences.
