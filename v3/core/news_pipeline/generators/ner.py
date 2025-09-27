from __future__ import annotations

import logging
import re
from typing import Dict, List, Optional, Sequence

from ..config import PipelineConfig
from ..models import CandidateSignal, NewsItem, TickerRecord
from .base import CandidateGenerator

logger = logging.getLogger(__name__)


class NERGenerator(CandidateGenerator):
    name = "ner"

    def __init__(self, *, weight: float = 1.0):
        super().__init__(weight=weight)
        self._spacy_model: Optional[object] = None
        self._ticker_entities: Dict[int, List[str]] = {}
        self._company_patterns: Dict[int, List[re.Pattern]] = {}

    def prepare(self, tickers: Sequence[TickerRecord], *, config: PipelineConfig) -> None:
        """Initialize NER model and prepare entity patterns."""
        try:
            import spacy
            # Try to load Russian model, fallback to English
            try:
                self._spacy_model = spacy.load("ru_core_news_sm")
                logger.info("Loaded Russian spaCy model")
            except OSError:
                try:
                    self._spacy_model = spacy.load("en_core_web_sm")
                    logger.info("Loaded English spaCy model (fallback)")
                except OSError:
                    logger.warning("No spaCy models available, NER will use pattern matching only")
                    self._spacy_model = None
        except ImportError:
            logger.warning("spaCy not available, NER will use pattern matching only")
            self._spacy_model = None

        # Prepare entity patterns for each ticker
        ticker_entities: Dict[int, List[str]] = {}
        company_patterns: Dict[int, List[re.Pattern]] = {}
        
        for ticker in tickers:
            entities = []
            patterns = []
            
            # Collect all names and aliases
            names = ticker.all_names()
            
            for name in names:
                if not name:
                    continue
                    
                entities.append(name)
                
                # Create patterns for company names
                # Handle common company suffixes
                suffixes = [
                    r'\b(?:ООО|ОАО|ЗАО|ПАО|АО|ИП|LLC|Inc|Corp|Corporation|Company|Co|Ltd|Limited)\b',
                    r'\b(?:Группа|Group|Холдинг|Holding)\b',
                    r'\b(?:Банк|Bank|Банковская группа|Banking Group)\b',
                ]
                
                # Create pattern for the name with optional suffixes
                name_escaped = re.escape(name)
                for suffix in suffixes:
                    pattern = re.compile(
                        rf'\b{name_escaped}(?:\s+{suffix})?\b',
                        re.IGNORECASE | re.UNICODE
                    )
                    patterns.append(pattern)
                
                # Also create pattern for just the name
                pattern = re.compile(rf'\b{name_escaped}\b', re.IGNORECASE | re.UNICODE)
                patterns.append(pattern)
            
            if entities:
                ticker_entities[ticker.id] = entities
            if patterns:
                company_patterns[ticker.id] = patterns

        self._ticker_entities = ticker_entities
        self._company_patterns = company_patterns
        logger.info("Prepared NER patterns for %d tickers", len(ticker_entities))

    def generate(
        self,
        news_item: NewsItem,
        tickers: Sequence[TickerRecord],
        *,
        config: PipelineConfig,
        **context,
    ) -> Dict[int, CandidateSignal]:
        results: Dict[int, CandidateSignal] = {}
        
        # Extract entities using spaCy if available
        spacy_entities = set()
        if self._spacy_model:
            try:
                doc = self._spacy_model(news_item.text)
                for ent in doc.ents:
                    if ent.label_ in ["ORG", "PERSON", "MONEY"]:
                        spacy_entities.add(ent.text.strip())
                        # Also add lemmatized version
                        spacy_entities.add(ent.lemma_.strip())
            except Exception as exc:
                logger.warning("spaCy NER failed: %s", exc)

        # Match against ticker entities
        for ticker in tickers:
            if ticker.id not in self._ticker_entities:
                continue
                
            entities = self._ticker_entities[ticker.id]
            patterns = self._company_patterns.get(ticker.id, [])
            
            best_score = 0.0
            best_match = None
            match_type = None
            
            # Check spaCy entities first
            for entity in spacy_entities:
                for ticker_entity in entities:
                    if self._fuzzy_match(entity, ticker_entity):
                        score = self._calculate_ner_score(entity, ticker_entity, "spacy")
                        if score > best_score:
                            best_score = score
                            best_match = entity
                            match_type = "spacy"
            
            # Check pattern matching
            for pattern in patterns:
                matches = pattern.findall(news_item.text)
                for match in matches:
                    for ticker_entity in entities:
                        if self._fuzzy_match(match, ticker_entity):
                            score = self._calculate_ner_score(match, ticker_entity, "pattern")
                            if score > best_score:
                                best_score = score
                                best_match = match
                                match_type = "pattern"
            
            # Apply threshold
            if best_score >= config.review_lower_threshold:
                results[ticker.id] = CandidateSignal(
                    score=best_score * self.weight,
                    method=self.name,
                    metadata={
                        "matched_entity": best_match or "",
                        "match_type": match_type or "",
                        "ticker_entity": ticker.ticker,
                    },
                )
        
        return results

    def _fuzzy_match(self, text1: str, text2: str, threshold: float = 0.8) -> bool:
        """Check if two strings are similar enough to be considered a match."""
        if not text1 or not text2:
            return False
            
        # Exact match
        if text1.lower() == text2.lower():
            return True
            
        # Substring match
        if text1.lower() in text2.lower() or text2.lower() in text1.lower():
            return True
            
        # Fuzzy match using simple ratio
        try:
            from rapidfuzz import fuzz
            ratio = fuzz.ratio(text1.lower(), text2.lower()) / 100.0
            return ratio >= threshold
        except ImportError:
            # Fallback to simple character overlap
            common_chars = set(text1.lower()) & set(text2.lower())
            total_chars = set(text1.lower()) | set(text2.lower())
            if total_chars:
                ratio = len(common_chars) / len(total_chars)
                return ratio >= threshold
            return False

    def _calculate_ner_score(self, matched_text: str, ticker_entity: str, match_type: str) -> float:
        """Calculate confidence score for NER match."""
        base_score = 0.7  # Base score for NER matches
        
        # Boost for exact matches
        if matched_text.lower() == ticker_entity.lower():
            base_score = 0.95
        elif matched_text.lower() in ticker_entity.lower() or ticker_entity.lower() in matched_text.lower():
            base_score = 0.85
        
        # Boost for spaCy matches (more reliable)
        if match_type == "spacy":
            base_score += 0.1
        
        # Boost for longer matches (more specific)
        if len(matched_text) > 10:
            base_score += 0.05
        
        return min(1.0, base_score)


__all__ = ["NERGenerator"]
