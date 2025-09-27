# GPT4Free Integration Roadmap

## Stage 1. Requirements and Artifacts

### Current News Pipeline (baseline)
- `news_parser/news_parser/jobs.py:18` runs the RSS job, persists articles, and currently performs regex based ticker tagging via `TickerMatcher.match` in `news_parser/news_parser/ticker_match.py:47`.
- `news_parser/news_parser/storage.py` writes into SQLite tables `articles`, `article_ticker`, and `tickers`, which are loaded by the Streamlit UI through `core/news.py:118` (`fetch_recent_articles`) and exposed on the dashboard (`pages/8_🗞️_News.py`).
- `news_parser/news_parser/summary.py:47` builds daily cluster summaries for the UI.

### Trading Signal Pipeline (baseline)
- `core/indicators/service.py:176` computes indicators and signals per contract, calling `compute_signal_scores` at `core/analytics/scoring.py:56` to add probabilistic scoring and `apply_risk_management` for trade level outputs.
- Streamlit dashboard (`pages/1_📊_Dashboard.py`) reads the aggregated frame via `get_calculated_data` in `core/indicators/service.py:262`, rendering KPI cards through `compute_kpi_for_signals` in `core/analytics/workflows.py`.
- Data refresh is orchestrated by `core/jobs/auto_update.py:110` using `StockAnalyzer.get_stock_data` (`core/analyzer.py:133`) to backfill OHLCV history.

### GPT4Free Capabilities (supplied stack)
- Repository `gpt4free-main` bundles the FastAPI "Interference" server (OpenAI compatible), CLI, and provider adapters. `docker-compose.yml` maps ports `8080/1337/7900` and sets `--shm-size=2gb`; the Dockerfile is Selenium based which implies Chrome availability for browser bound providers.
- `example.env` lists supported API keys (HuggingFace, Gemini, Together, DeepInfra, OpenRouter, Groq, NVIDIA, etc.) and runtime tuning flags such as proxy host, timeout, and browser port.

### Access and Security Inputs
- No production keys or HAR files ship with the repo; Secrets must be collected from stakeholders and stored in a managed vault (HashiCorp Vault, Azure Key Vault, AWS Secrets Manager, etc.).
- Company policy (placeholder): enforce allowlisted domains, redact PII before LLM calls, store prompts/responses for 30 days max, and restrict usage to approved provider SKUs.

### Exit Criteria for Stage 1
- Approved technical specification describing the augmented news and signal flows.
- Signed off access policy including provider allowlist, data classification rules, and incident response contacts.

## Stage 2. Integration Architecture

### News Flow With GPT4Free
1. RSS/HTML ingestion runs as today (`run_once`).
2. After `storage.insert_articles`, push job to an async worker queue (e.g., Celery/RQ) that:
   - Calls GPT4Free JSON mode to label tickers, sentiment, and confidence.
   - (Optional) generates short article briefs for UI display.
3. Worker upserts enriched data into `article_ticker` and a new table `article_llm_enrichment` with fields `(article_id, provider, model, confidence, tags, summary, raw_response)`.
4. `fetch_recent_articles` joins enrichment tables; UI toggles between regex baseline and LLM output for A/B testing.
5. Failure fallback: if enrichment task fails or exceeds SLA, fall back to regex matcher and log retry metrics.

### Signal Flow With GPT4Free
1. Indicator frame is computed as before.
2. A new `SignalNarrationService` consumes signal snapshots (pandas row or JSON) and:
   - Requests GPT4Free for human readable rationales, risk notes, and scenario summaries.
   - Optionally issues tool calls back into analytics functions (e.g., indicator inspection) through GPT function calling support.
3. The service writes outputs into `signals_llm_context` (columns: `contract_code`, `signal_timestamp`, `direction`, `llm_provider`, `explanation`, `confidence`, `validation_status`, `raw_payload`).
4. Dashboard loads these annotations when rendering signal detail popovers or trade tickets.

### Provider Selection Matrix

| Scenario | Primary Provider | Fall back | Notes |
| --- | --- | --- | --- |
| News tagging (JSON) | OpenRouter free tier (DeepSeek-R1, Claude) | Together AI (Llama 3.1 70B), local regex | Needs deterministic JSON, set `response_format={"type":"json_object"}` |
| News summary | OpenRouter (Claude) | Groq (LLaMA Guard for safety) | Cap length < 1200 tokens |
| Signal explanation | DeepSeek-R1 (reasoning mode) | Groq (Mixtral) | Use streaming to surface partial insights |
| Tool calling validation | GPT4Free function-call provider (DeepSeek or OpenAI-compatible) | Local Python fallback | Implement idempotent functions |

### Deployment Modes
- **Staging/Research:** docker compose (existing file) on shared VM with GPU optional. Mount `har_and_cookies` volume for providers needing browser automation.
- **Production:** choose between managed Kubernetes deployment (Helm chart wrapping Docker image) or systemd unit running `python -m g4f --port 8080`. For high availability, place behind reverse proxy (Traefik/NGINX) with mTLS.

### Exit Criteria for Stage 2
- Architecture diagram (sequence/data flow) shared in design doc or Miro.
- Provider roster with per-environment mappings and throttle settings.
- Infra requirements list (CPU, RAM, disk, Chrome dependencies) reviewed with DevOps.

## Stage 3. Infrastructure Preparation

### GPT4Free Runtime
- Containerise using existing `docker-compose.yml`; ensure `--shm-size` >= 2g for Selenium, and mount persistent `har_and_cookies` and `generated_media` volumes.
- Build hardened image variant: start from `docker/Dockerfile`, add OS packages for observability (telegraf, fluent-bit) and disable VNC port when unused.

### Secrets Management
- Store API keys, cookies, HAR paths, and OpenAI compatible tokens under a dedicated secret scope. Inject via environment at deploy time (`G4F_API_KEY`, `OPENROUTER_API_KEY`, etc.).
- Rotate credentials quarterly. Audit access via CI/CD pipeline integration.

### CI/CD Pipeline
- Build stage: lint (`ruff`), unit tests, Docker build and scan (Trivy/Grype).
- Deploy stage: push Docker image to registry, run Helm/Kustomize manifests, execute smoke tests (see below).
- Add job that validates GPT4Free availability with a synthetic `GET /v1/models` call and a sample completion using a mock prompt.

### Monitoring & Logging
- Metrics: request latency, success/error rate, token usage per provider, queue backlog, Selenium crash count. Export via Prometheus or OpenTelemetry.
- Logs: redact prompt payloads before centralizing. Configure log shipping from GPT4Free and enrichment workers.
- Alerts: trigger on latency > 2x baseline, error rate > 5%, or depletion of fallback providers.

### Exit Criteria for Stage 3
- Staging and production environments provisioned, secrets validated, monitoring dashboards live.
- Documented runbooks for provider outage, credential rotation, and queue backlog clearing.

## Stage 4. News Processing Enhancements

### Prompt Engineering
- Primary prompt: classify up to N tickers mentioned, return JSON `{ "tickers": [ { "symbol": "SBER", "confidence": 0.86, "evidence": "..." } ], "sentiment": "neutral" }`.
- Add fallback prompt for headlines with insufficient body text (focus on headline inference and ask for low confidence flags).
- Maintain prompt library under `news_parser/prompts/news_llm.json` with versioned templates.

### Pipeline Integration
- Extend `run_once` to enqueue article IDs after persistence (post `storage.insert_articles`). Use Celery task `enrich_article_with_llm(article_id)` to call GPT4Free via async HTTP client (httpx with timeout/retry policy).
- Validation step: ensure returned JSON parses and ticker symbols exist in `tickers` table; fallback to regex results otherwise.
- Store structured responses in new ORM/model; include provider latency metrics for monitoring.
- Update `fetch_recent_articles` (`core/news.py:118`) to perform left join on enrichment table and expose both `tickers_llm` and `tickers_regex` fields plus confidence.
- Update Streamlit page to show comparison toggle and highlight low-confidence outputs to human reviewer.

### Testing Strategy
- Unit tests using recorded fixtures: feed curated articles and assert deterministic JSON schema.
- Integration tests hitting GPT4Free staging with mock provider (use `g4f.cli mock` or patched provider) to avoid consuming quotas.
- Regression set: maintain 50 labelled news articles (tickers + sentiment) as golden dataset; target >= desired precision/recall threshold before rollout.

### Exit Criteria for Stage 4
- Documented prompts and fallbacks.
- Automated tests passing with target quality metric (e.g., ticker precision >= 85%).
- UI changes reviewed with newsroom stakeholders.

## Stage 5. Signal Processing Enhancements

### Use Cases
- Generate natural language rationales summarizing indicator alignment and risk context.
- Validate signals against configurable guardrails (e.g., reject long signals during macro downdrafts) using tool calling.
- Produce shareable briefs (PDF/email) and optional chart annotations.

### Tool Calling Integration
- Expose deterministic functions via API: `get_indicator_snapshot(contract_code, timestamp)`, `check_drawdown_limits(contract_code)`, `project_position_sizing(params)`.
- Register tool schemas with GPT4Free request payloads; ensure function calls query the same dataset used in `calculate_technical_indicators` to keep decisions consistent.
- Cache LLM rationales keyed by `(contract_code, signal_time, signal_version)` to avoid duplicate calls when dashboards refresh.

### Implementation Steps
- Add `SignalNarrationService` module under `core/analytics/llm/` encapsulating GPT4Free client, prompt templates, and retries.
- Hook into indicator pipeline after `compute_signal_scores` to emit events for qualifying signals (confidence above threshold, new crossovers, etc.).
- Persist outputs in `signals_llm_context` and surface via Streamlit (expanders or modal) with review controls for analysts.
- For near real-time alerts, integrate with existing scheduler or add lightweight FastAPI service subscribed to message bus (Redis, NATS).

### Testing & Validation
- Backtest set: replay last 90 days of signals, generate explanations, and manually score accuracy with trading desk.
- Load tests: simulate 100 concurrent signal requests, ensure GPT4Free throughput meets SLA (target < 5 s per explanation).
- A/B test: compare user engagement or decision latency with and without LLM context before full rollout.

### Exit Criteria for Stage 5
- Published explanation catalog and validation metrics (accuracy, average generation time).
- Tool calling coverage documented and mocked in unit tests.
- Ops handbook covering rollback to non-LLM explanations.

## Stage 6. Resilience and Quality Controls

### Fallback Strategy
- Maintain provider priority list; implement circuit breaker that demotes failing provider after N consecutive errors.
- Allow feature flags to disable LLM enrichment per pipeline if budget or policy requires.
- Keep regex ticker matcher and existing KPI logic as baseline modes.

### Retry and Rate Limits
- Configure exponential backoff (e.g., 1s, 4s, 10s) with jitter and max 3 attempts per article/signal.
- Enforce per-user/service quotas (requests per minute/hour) via Redis or API gateway.
- Capture timeout metrics to adjust prompts and provider selection.

### Audit and Compliance
- Log structured prompt/response metadata (hashes, lengths, provider, timestamp) without raw content unless incident investigation required.
- Apply data retention policy (auto purge after 30 days, archive metrics only).
- Align with legal review for each provider's TOS; maintain DR plan documenting restore steps for GPT4Free instance and queue workers.

### Exit Criteria for Stage 6
- Signed fallback and DR runbook, with tabletop exercise completed.
- Compliance checklist approved (data residency, access logging, retention).

## Implementation Backlog (Suggested Sequence)
1. Finalise Stage 1 spec with stakeholders (product, security).
2. Provision staging GPT4Free stack, wire monitoring, validate providers.
3. Implement async enrichment service and news LLM pipeline, launch controlled beta.
4. Build signal narration service with tool calling, run backtests and A/B.
5. Harden production deployment, enable resilience features, hand over to operations.

## Next Steps for Decision Makers
- Review this roadmap with architecture board.
- Decide on queue/messaging technology and hosting environment (Kubernetes vs VM).
- Approve provider budget and data handling policy updates.
- Schedule implementation sprints and assign owners for each stage.
