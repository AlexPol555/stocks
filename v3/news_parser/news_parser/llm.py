"""LLM integration helpers for GPT4Free enrichment."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence

import httpx

from .config import LLMConfig

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class ArticleEnvelope:
    """Minimal data needed to build enrichment prompts."""

    id: int
    title: str
    body: str
    url: str


@dataclass
class EnrichmentResult:
    success: bool
    tags: List[dict]
    summary: str
    sentiment: str
    confidence: Optional[float]
    raw_response: str
    latency_ms: int
    error: Optional[str] = None
    status: str = "success"


class GPT4FreeClient:
    """Thin OpenAI-compatible client for GPT4Free deployment."""

    def __init__(self, config: LLMConfig):
        self.config = config
        base = config.base_url.rstrip("/")
        if base.endswith("/chat/completions"):
            self.endpoint = base
        else:
            self.endpoint = f"{base}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if config.api_key:
            headers["Authorization"] = f"Bearer {config.api_key}"
        self.headers = headers

    def _build_prompt(self, article: ArticleEnvelope, tickers: Sequence[str]) -> List[dict]:
        tickers_list = ", ".join(sorted(set(tickers))) if tickers else ""
        body = article.body or ""
        if len(body) > 4000:
            body = body[:4000]
        user_content = (
            "Тебе дана новостная заметка по финансовым рынкам. "
            "Нужно найти тикеры Московской биржи, которые явно упоминаются или подразумеваются, "
            "и оценить настрой новости. Ответь строго JSON по схеме:\n"
            "{\n"
            "  \"tickers\": [\n"
            "    {\"symbol\": \"SBER\", \"confidence\": 0.92, \"evidence\": \"Краткая цитата\"}\n"
            "  ],\n"
            "  \"sentiment\": \"positive|negative|neutral|uncertain\",\n"
            "  \"summary\": \"краткий пересказ на русском до 240 символов\"\n"
            "}\n"
            "Если нет уверенности, оставь массив tickers пустым и поставь sentiment=\"uncertain\"."
        )
        user_content = "".join(user_content)
        if tickers_list:
            user_content += f"\nСписок допустимых тикеров: {tickers_list}."
        user_content += (
            "\nУчитывай только фактические упоминания компаний или активов."
            "\nЗаголовок: {title}\nURL: {url}\nТекст: {body}\n"
        ).format(title=article.title or "", url=article.url or "", body=body)
        return [
            {
                "role": "system",
                "content": "Ты помощник по разметке финансовых новостей. Всегда возвращай корректный JSON.",
            },
            {"role": "user", "content": user_content},
        ]
    def enrich(
        self,
        article: ArticleEnvelope,
        *,
        tickers: Iterable[str],
    ) -> EnrichmentResult:
        payload = {
            "model": self.config.model,
            "messages": self._build_prompt(article, tickers),
            "temperature": self.config.temperature,
            "max_tokens": 400,
            "response_format": {"type": "json_object"},
        }
        start = time.perf_counter()
        try:
            response = httpx.post(
                self.endpoint,
                json=payload,
                headers=self.headers,
                timeout=self.config.timeout,
            )
            latency_ms = int((time.perf_counter() - start) * 1000)
        except Exception as exc:  # pragma: no cover - network failure
            LOGGER.exception("GPT4Free request failed")
            return EnrichmentResult(
                success=False,
                tags=[],
                summary="",
                sentiment="uncertain",
                confidence=None,
                raw_response="",
                latency_ms=int((time.perf_counter() - start) * 1000),
                error=str(exc),
                status="unavailable",
            )

        raw = response.text
        if response.status_code >= 400:
            status_label = "unavailable" if response.status_code >= 500 else "failed"
            LOGGER.error("GPT4Free error %s: %s", response.status_code, raw)
            return EnrichmentResult(
                success=False,
                tags=[],
                summary="",
                sentiment="uncertain",
                confidence=None,
                raw_response=raw,
                latency_ms=latency_ms,
                error=f"HTTP {response.status_code}",
                status=status_label,
            )

        try:
            payload_json = response.json()
            content = payload_json["choices"][0]["message"]["content"]
        except Exception as exc:  # pragma: no cover - defensive
            LOGGER.error("Unexpected GPT4Free payload: %s", exc)
            return EnrichmentResult(
                success=False,
                tags=[],
                summary="",
                sentiment="uncertain",
                confidence=None,
                raw_response=raw,
                latency_ms=latency_ms,
                error="invalid_payload",
                status="failed",
            )

        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            LOGGER.warning("Failed to decode LLM JSON: %s", exc)
            return EnrichmentResult(
                success=False,
                tags=[],
                summary="",
                sentiment="uncertain",
                confidence=None,
                raw_response=content,
                latency_ms=latency_ms,
                error="json_decode_error",
                status="failed",
            )

        tickers_data = data.get("tickers") or []
        if not isinstance(tickers_data, list):
            tickers_data = []
        tags: List[dict] = []
        for item in tickers_data:
            if not isinstance(item, dict):
                continue
            symbol = str(item.get("symbol", "")).strip().upper()
            if not symbol:
                continue
            tags.append(
                {
                    "symbol": symbol,
                    "confidence": float(item.get("confidence", 0) or 0),
                    "evidence": str(item.get("evidence", "")),
                }
            )

        sentiment = str(data.get("sentiment") or "uncertain").strip().lower()
        summary = str(data.get("summary") or "").strip()

        avg_conf: Optional[float] = None
        if tags:
            avg_conf = sum(tag.get("confidence") or 0 for tag in tags) / len(tags)

        return EnrichmentResult(
            success=True,
            tags=tags,
            summary=summary,
            sentiment=sentiment,
            confidence=avg_conf,
            raw_response=content,
            latency_ms=latency_ms,
            status="success",
        )


__all__ = ["ArticleEnvelope", "EnrichmentResult", "GPT4FreeClient"]
