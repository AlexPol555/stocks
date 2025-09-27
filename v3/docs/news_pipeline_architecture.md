# News-Ticker Batch Pipeline Architecture

This document outlines the design for the scalable, idempotent news-ticker matching pipeline.

## Overview

The pipeline processes user-triggered batches of news, generates ticker candidates through several strategies, persists candidates with idempotent semantics, and exposes a human-in-the-loop Streamlit UI for validation. The design supports batch sizes from tens to thousands of items via chunked processing, optional restart, and progress logging.

Key capabilities:
- Configurable batch selection modes (only_unprocessed, recheck_all, recheck_selected_range).
- Multi-strategy candidate generation (substring, fuzzy, NER placeholder, embeddings, hybrid scoring).
- Chunked execution with resume support and metrics logging per run.
- Idempotent persistence with per-news dedupe and score updates.
- Auto-apply thresholds and manual validation workflow.

## Data Model (logical)

### `news`
Represents ingested news articles.
Fields: `id`, `source`, `url`, `published_at`, `title`, `body`, `language`, `ingested_at`, `processed`, `processed_at`, `last_batch_id`, `last_processed_version`.

### `tickers`
Reference catalogue of ticker symbols.
Fields: `id`, `ticker`, `name`, `aliases` (JSON array), `isin`, `exchange`, `description`, `embed_blob` (optional vector bytes), `updated_at`.

### `news_tickers`
Candidate ticker assignments for news.
Fields: `id`, `news_id`, `ticker_id`, `score`, `method`, `created_at`, `updated_at`, `confirmed` (1/0/-1), `confirmed_by`, `confirmed_at`, `batch_id`, `auto_suggest`, `history` (JSON audit trail).
Unique constraint on (`news_id`, `ticker_id`).

### `processing_runs`
Batch execution metadata.
Fields: `batch_id`, `mode`, `batch_size_requested`, `batch_size_actual`, `started_at`, `finished_at`, `status`, `metrics` (JSON), `operator`, `chunk_count`, `version`.

## Configuration

`core/news_pipeline/config.py` defines a `PipelineConfig` dataclass loaded from YAML or environment, covering thresholds (`review_lower`, `auto_apply_threshold`, etc.), chunk sizing, retry limits, and embedding model selection.

## Processing Flow

1. **Batch selection**: `NewsBatchSelector` queries news by mode and marks items with `last_batch_id` whilst leaving persisted state for restart.
2. **Chunker**: Splits selected IDs into `chunk_size` groups to avoid OOM. Progress persisted in `processing_runs`.
3. **Preprocessing**: `normalize_text` (with ru lemmatization via Pymorphy) prepares tokens shared across strategies. Embeddings computed in batch (`SentenceTransformer`) and cached.
4. **Candidate generation**:
   - Substring: exact and alias matches.
   - Fuzzy: RapidFuzz token sort ratio.
   - NER: placeholder hook (`SpacyRU`) with graceful degradation when unavailable.
   - Embedding: cosine similarity (matrix multiply or FAISS if many tickers).
   - Hybrid aggregator yields combined score and method trace.
5. **Persistence**: `CandidateRepository` applies idempotent UPSERT semantics: create missing pairs, update scores when improved, skip confirmed positives unless policy allows update, append history.
6. **Auto-apply**: Candidates above threshold optionally set `confirmed=1` and update news tags.
7. **Metrics/logging**: Each chunk updates counters (processed, candidates, auto-applied, retried). Final metrics captured in `processing_runs`.

## Restart Strategy

- Each `processing_runs` entry stores `last_processed_news_id` list for resume (serialized chunk index).
- On restart in same mode with same batch id, the processor loads existing run meta and continues remaining chunks.

## Streamlit UI

- Batch control form with mode, batch size, chunk size, threshold overrides.
- Progress panel streaming chunk-level metrics and ETA.
- Validation table filtered by status (new, pending review, auto-applied).
- Actions: confirm, reject, add manual ticker, bulk confirm >= threshold, undo (audit based).
- Separate tab for "no candidates" list.

## Extensibility

- Candidate generators are registered via plugin interface; additional strategies can be added without touching orchestrator.
- Repository isolated to allow migration from SQLite to PostgreSQL.
- Config loader supports environment overrides for dev/prod separation.

