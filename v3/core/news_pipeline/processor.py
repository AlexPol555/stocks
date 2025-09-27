from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Sequence

from .config import BatchMode, PipelineConfig
from .generators.hybrid import HybridGenerator
from .models import (
    CandidateRecord,
    CandidateComparison,
    NewsItem,
    ProcessingMetrics,
    TickerCandidate,
    TickerRecord,
)
from .progress import ProgressEvent, ProgressReporter
from .repository import NewsPipelineRepository

logger = logging.getLogger(__name__)


@dataclass
class PipelineRequest:
    mode: BatchMode
    batch_size: int
    range_start: Optional[str] = None
    range_end: Optional[str] = None
    selected_ids: Optional[Sequence[int]] = None
    operator: Optional[str] = None
    dry_run: bool = False


class NewsBatchProcessor:
    def __init__(self, repository: Optional[NewsPipelineRepository] = None):
        self.repository = repository or NewsPipelineRepository()
        self.repository.ensure_schema()
        self._generator: Optional[HybridGenerator] = None
        self._tickers: List[TickerRecord] = []
        self._config: Optional[PipelineConfig] = None

    def initialize(self, config: PipelineConfig) -> None:
        """Initialize the processor with configuration and load tickers."""
        self._config = config
        
        # Load tickers
        self._tickers = self.repository.load_tickers()
        if not self._tickers:
            logger.warning("No tickers loaded from database")
            return
        
        # Initialize generator
        self._generator = HybridGenerator(weight=1.0)
        self._generator.prepare(self._tickers, config=config)
        
        logger.info("Processor initialized with %d tickers", len(self._tickers))

    def process_batch(
        self,
        request: PipelineRequest,
        *,
        progress_reporter: Optional[ProgressReporter] = None,
    ) -> ProcessingMetrics:
        """Process a batch of news items and generate ticker candidates."""
        if not self._config or not self._generator:
            raise RuntimeError("Processor not initialized. Call initialize() first.")

        start_time = time.time()
        metrics = ProcessingMetrics()
        
        # Create processing run record
        batch_id = self.repository.create_processing_run(
            mode=request.mode,
            requested=request.batch_size,
            actual=0,  # Will be updated
            version=self._config.version,
            operator=request.operator,
        )
        
        try:
            # Fetch news batch
            news_items = self.repository.fetch_news_batch(
                mode=request.mode,
                batch_size=request.batch_size,
                range_start=request.range_start,
                range_end=request.range_end,
                selected_ids=request.selected_ids,
            )
            
            metrics.total_news = len(news_items)
            if not news_items:
                logger.info("No news items found for processing")
                return metrics
            
            # Update actual batch size
            self.repository.complete_processing_run(
                batch_id,
                status="running",
                metrics=metrics,
                chunk_count=0,
            )
            
            # Process in chunks
            chunk_size = self._config.chunk_size
            processed_news_ids = []
            
            for chunk_start in range(0, len(news_items), chunk_size):
                chunk_end = min(chunk_start + chunk_size, len(news_items))
                chunk_items = news_items[chunk_start:chunk_end]
                
                logger.info("Processing chunk %d-%d of %d", chunk_start + 1, chunk_end, len(news_items))
                
                # Process chunk
                chunk_metrics = self._process_chunk(
                    chunk_items,
                    batch_id,
                    progress_reporter=progress_reporter,
                )
                
                # Update metrics
                metrics.processed_news += chunk_metrics.processed_news
                metrics.candidates_generated += chunk_metrics.candidates_generated
                metrics.auto_applied += chunk_metrics.auto_applied
                metrics.skipped_duplicates += chunk_metrics.skipped_duplicates
                metrics.errors += chunk_metrics.errors
                metrics.chunk_count += 1
                
                # Collect processed news IDs
                processed_news_ids.extend([item.id for item in chunk_items])
                
                # Report progress
                if progress_reporter:
                    progress_reporter.report(ProgressEvent(
                        stage="processing",
                        current=chunk_end,
                        total=len(news_items),
                        message=f"Processed {chunk_end}/{len(news_items)} news items",
                        metadata={"chunk": metrics.chunk_count, "batch_id": batch_id},
                    ))
            
            # Mark news as processed
            if not request.dry_run:
                self.repository.mark_news_processed(
                    processed_news_ids,
                    batch_id=batch_id,
                    version=self._config.version,
                )
            
            # Calculate final metrics
            metrics.duration_seconds = time.time() - start_time
            
            # Complete processing run
            status = "completed" if metrics.errors == 0 else "completed_with_errors"
            self.repository.complete_processing_run(
                batch_id,
                status=status,
                metrics=metrics,
                chunk_count=metrics.chunk_count,
            )
            
            logger.info(
                "Batch processing completed: %d news items, %d candidates, %d auto-applied, %d errors, %.2fs",
                metrics.processed_news,
                metrics.candidates_generated,
                metrics.auto_applied,
                metrics.errors,
                metrics.duration_seconds,
            )
            
            return metrics
            
        except Exception as exc:
            logger.error("Batch processing failed: %s", exc)
            metrics.errors += 1
            metrics.duration_seconds = time.time() - start_time
            
            # Mark run as failed
            self.repository.complete_processing_run(
                batch_id,
                status="failed",
                metrics=metrics,
                chunk_count=metrics.chunk_count,
            )
            
            raise

    def _process_chunk(
        self,
        news_items: List[NewsItem],
        batch_id: str,
        *,
        progress_reporter: Optional[ProgressReporter] = None,
    ) -> ProcessingMetrics:
        """Process a chunk of news items."""
        metrics = ProcessingMetrics()
        
        for news_item in news_items:
            try:
                # Check existing candidates
                existing_candidates = self.repository.load_existing_candidates(news_item.id)
                
                # Generate new candidates
                candidates = self._generate_candidates(news_item)
                
                # Process each candidate
                for candidate in candidates:
                    comparison = self._process_candidate(
                        candidate,
                        news_item.id,
                        batch_id,
                        existing_candidates,
                    )
                    
                    if comparison.should_update:
                        metrics.candidates_generated += 1
                        if candidate.auto_apply:
                            metrics.auto_applied += 1
                    else:
                        metrics.skipped_duplicates += 1
                
                metrics.processed_news += 1
                
                # Report progress
                if progress_reporter:
                    progress_reporter.report(ProgressEvent(
                        stage="candidate_generation",
                        current=metrics.processed_news,
                        total=len(news_items),
                        message=f"Generated candidates for news {news_item.id}",
                        metadata={"news_id": news_item.id},
                    ))
                
            except Exception as exc:
                logger.error("Failed to process news item %d: %s", news_item.id, exc)
                metrics.errors += 1
                continue
        
        return metrics

    def _generate_candidates(self, news_item: NewsItem) -> List[TickerCandidate]:
        """Generate ticker candidates for a news item."""
        if not self._generator:
            return []
        
        try:
            # Generate candidates using hybrid generator
            results = self._generator.generate(
                news_item,
                self._tickers,
                config=self._config,
            )
            
            candidates = []
            for ticker_id, signal in results.items():
                # Find ticker record
                ticker = next((t for t in self._tickers if t.id == ticker_id), None)
                if not ticker:
                    continue
                
                # Check if score meets thresholds
                if signal.score < self._config.review_lower_threshold:
                    continue
                
                # Determine if should auto-apply
                auto_apply = (
                    signal.score >= self._config.auto_apply_threshold and
                    self._config.auto_apply_confirm
                )
                
                candidate = TickerCandidate(
                    ticker=ticker,
                    aggregate_score=signal.score,
                    signals=[signal],
                    auto_apply=auto_apply,
                )
                candidates.append(candidate)
            
            return candidates
            
        except Exception as exc:
            logger.error("Failed to generate candidates for news %d: %s", news_item.id, exc)
            return []

    def _process_candidate(
        self,
        candidate: TickerCandidate,
        news_id: int,
        batch_id: str,
        existing_candidates: Dict[int, object],
    ) -> CandidateComparison:
        """Process a single candidate and determine if it should be updated."""
        if not self._config:
            raise RuntimeError("Processor not initialized")
        
        # Convert to record
        record = candidate.to_record(news_id, batch_id)
        
        # Check if already confirmed
        existing = existing_candidates.get(candidate.ticker.id)
        if existing and existing.confirmed == 1 and not self._config.allow_confirmed_overwrite:
            return CandidateComparison(
                news_id=news_id,
                ticker_id=candidate.ticker.id,
                existing_score=existing.score,
                new_score=candidate.aggregate_score,
                should_update=False,
                reason="confirmed_locked",
            )
        
        # Upsert candidate
        comparison = self.repository.upsert_candidate(record, config=self._config)
        return comparison

    def get_processing_status(self, batch_id: str) -> Optional[Dict]:
        """Get the status of a processing run."""
        # This would need to be implemented in the repository
        # For now, return None
        return None

    def cancel_processing(self, batch_id: str) -> bool:
        """Cancel a processing run."""
        # This would need to be implemented in the repository
        # For now, return False
        return False


__all__ = ["NewsBatchProcessor", "PipelineRequest"]
