"""Sentiment analysis for news and market sentiment prediction."""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
import logging
import re
from collections import Counter

logger = logging.getLogger(__name__)

try:
    from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
    from sentence_transformers import SentenceTransformer
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logger.warning("Transformers not available. Install transformers for sentiment analysis.")

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


@dataclass
class SentimentConfig:
    """Configuration for sentiment analysis."""
    model_name: str = "cardiffnlp/twitter-roberta-base-sentiment-latest"
    batch_size: int = 32
    max_length: int = 512
    confidence_threshold: float = 0.7
    use_gpu: bool = False
    fallback_to_lexicon: bool = True


@dataclass
class SentimentResult:
    """Result of sentiment analysis."""
    text: str
    sentiment: str  # 'positive', 'negative', 'neutral'
    confidence: float
    scores: Dict[str, float]
    method: str


class LexiconSentimentAnalyzer:
    """Rule-based sentiment analyzer using financial lexicons."""
    
    def __init__(self):
        # Financial sentiment words
        self.positive_words = {
            'bullish', 'surge', 'rally', 'gain', 'rise', 'up', 'positive', 'strong',
            'growth', 'profit', 'earnings', 'beat', 'exceed', 'outperform', 'optimistic',
            'confidence', 'momentum', 'breakthrough', 'milestone', 'record', 'high',
            'increase', 'boost', 'improve', 'better', 'excellent', 'outstanding',
            'success', 'win', 'victory', 'breakthrough', 'innovation', 'revolutionary'
        }
        
        self.negative_words = {
            'bearish', 'crash', 'fall', 'drop', 'down', 'negative', 'weak', 'decline',
            'loss', 'miss', 'disappoint', 'underperform', 'pessimistic', 'concern',
            'worry', 'risk', 'volatility', 'uncertainty', 'crisis', 'recession',
            'decrease', 'downturn', 'slump', 'plunge', 'tumble', 'collapse',
            'failure', 'problem', 'issue', 'challenge', 'threat', 'danger'
        }
        
        # Financial intensity modifiers
        self.intensifiers = {
            'very', 'extremely', 'highly', 'significantly', 'dramatically', 'sharply',
            'substantially', 'considerably', 'massively', 'tremendously', 'hugely'
        }
        
        self.negators = {
            'not', 'no', 'never', 'none', 'nothing', 'nobody', 'nowhere', 'neither',
            'nor', 'cannot', 'can\'t', 'won\'t', 'wouldn\'t', 'shouldn\'t', 'couldn\'t'
        }
    
    def analyze(self, text: str) -> SentimentResult:
        """Analyze sentiment using lexicon-based approach."""
        text_lower = text.lower()
        words = re.findall(r'\b\w+\b', text_lower)
        
        positive_score = 0
        negative_score = 0
        total_words = len(words)
        
        if total_words == 0:
            return SentimentResult(
                text=text,
                sentiment='neutral',
                confidence=0.0,
                scores={'positive': 0.0, 'negative': 0.0, 'neutral': 1.0},
                method='lexicon'
            )
        
        i = 0
        while i < len(words):
            word = words[i]
            intensity = 1.0
            is_negated = False
            
            # Check for negators
            if i > 0 and words[i-1] in self.negators:
                is_negated = True
            
            # Check for intensifiers
            if i > 0 and words[i-1] in self.intensifiers:
                intensity = 2.0
            
            # Check sentiment
            if word in self.positive_words:
                score = intensity if not is_negated else -intensity
                positive_score += score
            elif word in self.negative_words:
                score = intensity if not is_negated else -intensity
                negative_score += score
            
            i += 1
        
        # Normalize scores
        positive_score = max(0, positive_score) / total_words
        negative_score = max(0, negative_score) / total_words
        neutral_score = 1.0 - positive_score - negative_score
        
        # Determine sentiment
        if positive_score > negative_score and positive_score > 0.1:
            sentiment = 'positive'
            confidence = positive_score
        elif negative_score > positive_score and negative_score > 0.1:
            sentiment = 'negative'
            confidence = negative_score
        else:
            sentiment = 'neutral'
            confidence = neutral_score
        
        return SentimentResult(
            text=text,
            sentiment=sentiment,
            confidence=confidence,
            scores={
                'positive': positive_score,
                'negative': negative_score,
                'neutral': neutral_score
            },
            method='lexicon'
        )


class NewsSentimentAnalyzer:
    """Advanced sentiment analyzer for financial news."""
    
    def __init__(self, config: SentimentConfig):
        self.config = config
        self.transformer_pipeline = None
        self.lexicon_analyzer = LexiconSentimentAnalyzer()
        
        if TRANSFORMERS_AVAILABLE and TORCH_AVAILABLE:
            self._initialize_transformer_model()
    
    def _initialize_transformer_model(self):
        """Initialize transformer-based sentiment analysis model."""
        try:
            device = 0 if self.config.use_gpu and torch.cuda.is_available() else -1
            
            self.transformer_pipeline = pipeline(
                "sentiment-analysis",
                model=self.config.model_name,
                tokenizer=self.config.model_name,
                device=device,
                return_all_scores=True
            )
            logger.info(f"Initialized transformer model: {self.config.model_name}")
        except Exception as e:
            logger.warning(f"Failed to initialize transformer model: {e}")
            self.transformer_pipeline = None
    
    def analyze_text(self, text: str) -> SentimentResult:
        """Analyze sentiment of a single text."""
        if not text or not text.strip():
            return SentimentResult(
                text=text,
                sentiment='neutral',
                confidence=0.0,
                scores={'positive': 0.0, 'negative': 0.0, 'neutral': 1.0},
                method='empty'
            )
        
        # Try transformer model first
        if self.transformer_pipeline:
            try:
                return self._analyze_with_transformer(text)
            except Exception as e:
                logger.warning(f"Transformer analysis failed: {e}")
        
        # Fallback to lexicon
        if self.config.fallback_to_lexicon:
            return self.lexicon_analyzer.analyze(text)
        
        # Return neutral if no method available
        return SentimentResult(
            text=text,
            sentiment='neutral',
            confidence=0.0,
            scores={'positive': 0.0, 'negative': 0.0, 'neutral': 1.0},
            method='fallback'
        )
    
    def _clean_text(self, text: str) -> str:
        """Clean and preprocess text for analysis."""
        if not text:
            return ""
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Remove special characters but keep basic punctuation
        text = re.sub(r'[^\w\s.,!?;:-]', '', text)
        
        # Limit length
        if len(text) > 500:
            text = text[:500]
        
        return text
    
    def _analyze_with_transformer(self, text: str) -> SentimentResult:
        """Analyze sentiment using transformer model."""
        try:
            # More aggressive text truncation
            max_chars = min(self.config.max_length, 256)  # Limit to 256 chars to avoid tensor issues
            if len(text) > max_chars:
                text = text[:max_chars]
                logger.debug(f"Truncated text to {max_chars} characters")
            
            # Clean text
            text = self._clean_text(text)
            if not text.strip():
                return SentimentResult(
                    text=text,
                    sentiment='neutral',
                    confidence=0.5,
                    scores={'positive': 0.33, 'negative': 0.33, 'neutral': 0.34},
                    method='transformer_empty'
                )
            
            # Try with error handling
            try:
                results = self.transformer_pipeline(text, truncation=True, max_length=128)
            except Exception as e:
                logger.warning(f"Pipeline failed with full text, trying shorter: {e}")
                # Try with even shorter text
                short_text = text[:128]
                results = self.transformer_pipeline(short_text, truncation=True, max_length=64)
            
            # Convert results to our format
            scores = {}
            for result in results[0]:
                label = result['label'].lower()
                score = result['score']
                
                if 'positive' in label or 'pos' in label:
                    scores['positive'] = score
                elif 'negative' in label or 'neg' in label:
                    scores['negative'] = score
                else:
                    scores['neutral'] = score
            
            # Determine sentiment
            sentiment = max(scores, key=scores.get)
            confidence = scores[sentiment]
            
            return SentimentResult(
                text=text,
                sentiment=sentiment,
                confidence=confidence,
                scores=scores,
                method='transformer'
            )
            
        except Exception as e:
            logger.error(f"Transformer analysis failed: {e}")
            # Fallback to neutral sentiment
            return SentimentResult(
                text=text,
                sentiment='neutral',
                confidence=0.5,
                scores={'positive': 0.33, 'negative': 0.33, 'neutral': 0.34},
                method='transformer_error'
            )
    
    def analyze_batch(self, texts: List[str]) -> List[SentimentResult]:
        """Analyze sentiment for a batch of texts."""
        results = []
        
        # Limit batch size to avoid memory issues
        max_batch_size = 10
        if len(texts) > max_batch_size:
            logger.warning(f"Batch size {len(texts)} too large, limiting to {max_batch_size}")
            texts = texts[:max_batch_size]
        
        for i, text in enumerate(texts):
            try:
                result = self.analyze_text(text)
                results.append(result)
            except Exception as e:
                logger.error(f"Error analyzing text {i}: {e}")
                # Add neutral result for failed analysis
                results.append(SentimentResult(
                    text=text,
                    sentiment='neutral',
                    confidence=0.5,
                    scores={'positive': 0.33, 'negative': 0.33, 'neutral': 0.34},
                    method='error_fallback'
                ))
        
        return results
    
    def analyze_news_dataframe(self, df: pd.DataFrame, 
                              text_column: str = 'content',
                              title_column: Optional[str] = None) -> pd.DataFrame:
        """Analyze sentiment for a DataFrame of news."""
        results = []
        
        for idx, row in df.iterrows():
            # Combine title and content if both available
            text_parts = []
            if title_column and pd.notna(row.get(title_column)):
                text_parts.append(str(row[title_column]))
            if pd.notna(row.get(text_column)):
                text_parts.append(str(row[text_column]))
            
            combined_text = ' '.join(text_parts)
            result = self.analyze_text(combined_text)
            
            results.append({
                'index': idx,
                'sentiment': result.sentiment,
                'confidence': result.confidence,
                'positive_score': result.scores.get('positive', 0.0),
                'negative_score': result.scores.get('negative', 0.0),
                'neutral_score': result.scores.get('neutral', 0.0),
                'method': result.method
            })
        
        return pd.DataFrame(results)
    
    def get_market_sentiment(self, news_df: pd.DataFrame, 
                           text_column: str = 'content',
                           title_column: Optional[str] = None,
                           time_column: Optional[str] = None,
                           window_hours: int = 24) -> Dict[str, float]:
        """Calculate overall market sentiment from news."""
        # Analyze sentiment
        sentiment_df = self.analyze_news_dataframe(news_df, text_column, title_column)
        
        # Filter by time window if time column provided
        if time_column and time_column in news_df.columns:
            if pd.api.types.is_datetime64_any_dtype(news_df[time_column]):
                cutoff_time = pd.Timestamp.now() - pd.Timedelta(hours=window_hours)
                recent_mask = news_df[time_column] >= cutoff_time
                sentiment_df = sentiment_df[recent_mask]
        
        if len(sentiment_df) == 0:
            return {
                'overall_sentiment': 'neutral',
                'confidence': 0.0,
                'positive_ratio': 0.0,
                'negative_ratio': 0.0,
                'neutral_ratio': 1.0,
                'total_articles': 0
            }
        
        # Calculate ratios
        total_articles = len(sentiment_df)
        positive_count = len(sentiment_df[sentiment_df['sentiment'] == 'positive'])
        negative_count = len(sentiment_df[sentiment_df['sentiment'] == 'negative'])
        neutral_count = len(sentiment_df[sentiment_df['sentiment'] == 'neutral'])
        
        positive_ratio = positive_count / total_articles
        negative_ratio = negative_count / total_articles
        neutral_ratio = neutral_count / total_articles
        
        # Determine overall sentiment
        if positive_ratio > negative_ratio and positive_ratio > 0.4:
            overall_sentiment = 'positive'
            confidence = positive_ratio
        elif negative_ratio > positive_ratio and negative_ratio > 0.4:
            overall_sentiment = 'negative'
            confidence = negative_ratio
        else:
            overall_sentiment = 'neutral'
            confidence = neutral_ratio
        
        return {
            'overall_sentiment': overall_sentiment,
            'confidence': confidence,
            'positive_ratio': positive_ratio,
            'negative_ratio': negative_ratio,
            'neutral_ratio': neutral_ratio,
            'total_articles': total_articles
        }


def create_sentiment_analyzer(config: Optional[SentimentConfig] = None) -> NewsSentimentAnalyzer:
    """Factory function to create sentiment analyzer."""
    if config is None:
        config = SentimentConfig()
    return NewsSentimentAnalyzer(config)
