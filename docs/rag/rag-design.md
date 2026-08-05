# HealthCore RAG design

## Purpose and scope

This knowledge base helps HealthCore commercial and operational staff answer questions about the company without searching its internal documents manually. It is grounded in the two repository context files, `CONTEXT.md` and `CONTEXT_HEALTHCORE.md`, and uses HealthCore vocabulary such as Patient Experience and Access, Revenue Cycle and Billing, Compliance and Data Governance, HIPAA, UK GDPR, claims, appointments, clinicians, and locations.

The API exposes `POST /knowledge/query` with `{ "question": "..." }` and returns only `{ "answer": "..." }`. Search payloads, source chunks, and similarity scores remain server-side.

## End-to-end flow

1. `data/process/rag.py` reads Markdown from `docs/company-knowledge-base/` and splits it at semantic headings and paragraph boundaries.
2. `data/pipelines/rag.py:setup()` embeds every chunk with the dedicated embedding model, recreates the `healthcore_knowledge_base` Qdrant collection, and upserts deterministic points.
3. `data/pipelines/rag.py:retrieve()` embeds a salesperson's question, searches Qdrant with cosine similarity, removes hits below `RAG_MIN_SCORE`, and returns allowlisted payload dictionaries.
4. `data/pipelines/rag.py:query()` assembles only the surviving chunk text into a prompt for the generation model.
5. The generation model answers from the supplied HealthCore context. When no chunk passes the threshold, it returns an honest no-information response rather than inventing a fact.
6. `services/api/routes/knowledge.py` validates the request and delegates to `query()`; it does not contain retrieval or generation logic.

```text
HealthCore Markdown corpus
        | setup: heading-aware chunks
        v
dedicated embeddings model -> Qdrant healthcore_knowledge_base
        | query: vector search + RAG_MIN_SCORE
        v
allowlisted context -> dedicated generation model -> salesperson answer
```

## Corpus and chunking

The committed corpus consists of `healthcore-operating-brief.md` and `healthcore-compliance-and-access.md`. They are derived from both HealthCore context files and preserve the company-specific departments, entities, operational baselines, and compliance constraints.

Chunks are created at Markdown heading boundaries so a department's responsibility or a compliance rule stays with its scope. Paragraphs are the fallback boundary for long sections, with an approximate 220-word target. The chunker never cuts through a paragraph, and each chunk carries its source document and section. This avoids the common failure where a rule and its exception are indexed as unrelated fragments.

## Embeddings and generation

The IDs are deliberately separate:

- `RAG_EMBEDDING_MODEL` defaults to `4geeks-healthcore-embedding`.
- `RAG_GENERATION_MODEL` defaults to `4geeks-healthcore-generation`.

Both are configured through environment variables and are sent to the OpenAI-compatible provider selected by `RAG_BASE_URL` and `RAG_API_KEY`. In a 4Geeks environment, those variables point to the provided endpoint and model IDs. The embedding function is used both while indexing chunks and while querying, so vectors are produced consistently. The generation model is never used to create vectors.

Qdrant uses cosine distance. The default local fallback vector dimension is 384 (`RAG_EMBEDDING_DIMENSION`), while `setup()` creates the collection from the actual vector length so a configured provider can use its own dimension. The production minimum score is `RAG_MIN_SCORE=0.10`; it is intentionally a threshold rather than a requirement to return exactly five results. The value should be tuned against a labelled set of HealthCore questions and reviewed for false positives because an incorrect compliance answer is more harmful than an honest no-answer.

When no API key or Qdrant server is configured, local tests use a deterministic hash embedding, lexical thresholding, and a clearly marked offline answer fallback. This keeps CI and the previous LangGraph trace tests deterministic; deployed environments should configure the real 4Geeks-compatible providers and Qdrant service.

## Qdrant payload and idempotency

Every point stores exactly these application payload keys:

| Key | Purpose |
| --- | --- |
| `source_document` | Audit trail back to the committed source file |
| `section` | Human-readable semantic section |
| `company` | `HealthCore` domain identifier |
| `language` | `en` corpus language |
| `chunk_index` | Stable chunk ordering |
| `text` | Context body used for prompt assembly |

Point IDs are UUIDv5 values derived from the source filename and chunk index. `setup()` recreates the collection and upserts the same deterministic IDs, so repeated development indexing cannot leave duplicate points. Qdrant is mounted as a Docker service at `http://qdrant:6333`; `QDRANT_URL` can point to Qdrant Cloud instead.

## Safety and failure behavior

The generation prompt instructs the assistant to answer as a HealthCore salesperson using only retrieved context and to decline when the context does not support an answer. The endpoint returns a safe generic error if the pipeline fails. It never returns raw Qdrant objects, chunk lists, or scores to the browser. The backoffice page displays loading, answer, validation, and error states and uses the existing authenticated API client.

## Verification

Run the RAG tests from the repository root:

```powershell
$env:PYTHONPATH = (Get-Location).Path
uv run --project services/api pytest -q tests/pipelines/test_rag.py
```

With Docker running, start Qdrant and the API with `docker compose up qdrant api`, then call:

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8000/knowledge/query `
  -ContentType "application/json" `
  -Body '{"question":"What rules protect HealthCore patient data in the UK?"}'
```
