"""Pytest configuration and fixtures for news pipeline tests."""

import json
import tempfile
from pathlib import Path
from typing import Generator

try:
    import pytest
except ImportError:
    pytest = None

from core.news_pipeline.config import PipelineConfig
from core.news_pipeline.models import NewsItem, TickerRecord
from core.news_pipeline.repository import NewsPipelineRepository


def temp_db_path() -> Generator[Path, None, None]:
    """Create a temporary database file for testing."""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp:
        tmp.close()
        db_path = Path(tmp.name)
        yield db_path
        if db_path.exists():
            db_path.unlink()


def repository(temp_db_path: Path) -> NewsPipelineRepository:
    """Create a repository with a temporary database."""
    repo = NewsPipelineRepository(temp_db_path)
    repo.ensure_schema()
    return repo


def test_config() -> PipelineConfig:
    """Create a test configuration."""
    return PipelineConfig(
        batch_size=10,
        chunk_size=5,
        auto_apply_threshold=0.85,
        review_lower_threshold=0.60,
        fuzzy_threshold=65,
        cos_candidate_threshold=0.60,
        cos_auto_threshold=0.80,
        embedding_model="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        use_faiss=False,
        cache_embeddings=True,
        dry_run=False,
        version="v1.0",
    )


def test_tickers() -> list[TickerRecord]:
    """Create test ticker records."""
    return [
        TickerRecord(
            id=1,
            ticker="SBER",
            name="Сбербанк",
            aliases=["Сбер", "Sberbank", "ПАО Сбербанк"],
            isin="RU0009029540",
            exchange="MOEX",
            description="ПАО Сбербанк",
        ),
        TickerRecord(
            id=2,
            ticker="GAZP",
            name="Газпром",
            aliases=["Газпром", "Gazprom", "ПАО Газпром"],
            isin="RU0007661625",
            exchange="MOEX",
            description="ПАО Газпром",
        ),
        TickerRecord(
            id=3,
            ticker="LKOH",
            name="Лукойл",
            aliases=["Лукойл", "Lukoil", "ПАО Лукойл"],
            isin="RU0009024277",
            exchange="MOEX",
            description="ПАО Лукойл",
        ),
    ]


def test_news_items() -> list[NewsItem]:
    """Create test news items."""
    return [
        NewsItem(
            id=1,
            title="Сбербанк объявил о росте прибыли",
            body="ПАО Сбербанк сообщил о значительном росте прибыли в отчетном периоде. Компания показала отличные результаты.",
            language="ru",
            published_at="2024-01-01T00:00:00Z",
            source="test_source",
            processed=False,
            processed_at=None,
            last_batch_id=None,
            last_processed_version=None,
        ),
        NewsItem(
            id=2,
            title="Газпром увеличил добычу газа",
            body="ПАО Газпром сообщило об увеличении добычи природного газа. Компания продолжает развиваться.",
            language="ru",
            published_at="2024-01-02T00:00:00Z",
            source="test_source",
            processed=False,
            processed_at=None,
            last_batch_id=None,
            last_processed_version=None,
        ),
        NewsItem(
            id=3,
            title="Лукойл инвестирует в новые проекты",
            body="ПАО Лукойл объявило о планах инвестирования в новые нефтегазовые проекты.",
            language="ru",
            published_at="2024-01-03T00:00:00Z",
            source="test_source",
            processed=False,
            processed_at=None,
            last_batch_id=None,
            last_processed_version=None,
        ),
    ]


def populated_repository(repository: NewsPipelineRepository, test_tickers: list[TickerRecord]) -> NewsPipelineRepository:
    """Create a repository populated with test data."""
    with repository.connect() as conn:
        # Create test sources
        conn.execute("""
            INSERT OR IGNORE INTO sources (id, name, rss_url, website)
            VALUES (1, 'Test Source', 'http://test.com/rss', 'http://test.com')
        """)
        
        # Create test articles
        test_articles = [
            {
                'id': 1,
                'title': 'Сбербанк объявил о росте прибыли',
                'body': 'ПАО Сбербанк сообщил о значительном росте прибыли в отчетном периоде. Компания показала отличные результаты.',
                'published_at': '2024-01-01T00:00:00Z',
                'source_id': 1,
                'language': 'ru',
                'processed': 0,
            },
            {
                'id': 2,
                'title': 'Газпром увеличил добычу газа',
                'body': 'ПАО Газпром сообщило об увеличении добычи природного газа. Компания продолжает развиваться.',
                'published_at': '2024-01-02T00:00:00Z',
                'source_id': 1,
                'language': 'ru',
                'processed': 0,
            },
            {
                'id': 3,
                'title': 'Лукойл инвестирует в новые проекты',
                'body': 'ПАО Лукойл объявило о планах инвестирования в новые нефтегазовые проекты.',
                'published_at': '2024-01-03T00:00:00Z',
                'source_id': 1,
                'language': 'ru',
                'processed': 0,
            },
        ]
        
        for article in test_articles:
            conn.execute("""
                INSERT OR REPLACE INTO articles 
                (id, title, body, published_at, source_id, language, processed)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                article['id'],
                article['title'],
                article['body'],
                article['published_at'],
                article['source_id'],
                article['language'],
                article['processed'],
            ))
        
        # Create test tickers
        for ticker in test_tickers:
            conn.execute("""
                INSERT OR REPLACE INTO tickers 
                (id, ticker, name, aliases, isin, exchange, description)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                ticker.id,
                ticker.ticker,
                ticker.name,
                json.dumps(list(ticker.aliases)),
                ticker.isin,
                ticker.exchange,
                ticker.description,
            ))
        
        conn.commit()
    
    return repository


def mock_sentence_transformer():
    """Mock SentenceTransformer for testing."""
    import numpy as np
    from unittest.mock import Mock
    
    mock_model = Mock()
    mock_model.encode.return_value = np.array([[0.1, 0.2, 0.3, 0.4, 0.5]])
    
    with pytest.MonkeyPatch().context() as m:
        m.setattr('core.news_pipeline.generators.embedding.SentenceTransformer', Mock(return_value=mock_model))
        yield mock_model


def mock_spacy_model():
    """Mock spaCy model for testing."""
    from unittest.mock import Mock
    
    mock_doc = Mock()
    mock_doc.ents = [
        Mock(text="Сбербанк", label_="ORG", lemma_="сбербанк"),
        Mock(text="Газпром", label_="ORG", lemma_="газпром"),
    ]
    
    mock_model = Mock()
    mock_model.return_value = mock_doc
    
    if pytest:
        with pytest.MonkeyPatch().context() as m:
            m.setattr('core.news_pipeline.generators.ner.spacy.load', Mock(return_value=mock_model))
            yield mock_model
    else:
        yield mock_model


# Pytest configuration (only if pytest is available)
if pytest:
    def pytest_configure(config):
        """Configure pytest."""
        config.addinivalue_line(
            "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
        )
        config.addinivalue_line(
            "markers", "integration: marks tests as integration tests"
        )
        config.addinivalue_line(
            "markers", "unit: marks tests as unit tests"
        )


    def pytest_collection_modifyitems(config, items):
        """Modify test collection."""
        for item in items:
            # Mark tests based on their location
            if "test_integration" in str(item.fspath):
                item.add_marker(pytest.mark.integration)
            else:
                item.add_marker(pytest.mark.unit)
            
            # Mark slow tests
            if "slow" in item.name or "large" in item.name:
                item.add_marker(pytest.mark.slow)
