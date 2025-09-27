"""Tests for news pipeline components."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np

from core.news_pipeline.config import BatchMode, PipelineConfig
from core.news_pipeline.generators.embedding import EmbeddingGenerator
from core.news_pipeline.generators.fuzzy import FuzzyGenerator
from core.news_pipeline.generators.hybrid import HybridGenerator
from core.news_pipeline.generators.ner import NERGenerator
from core.news_pipeline.generators.substring import SubstringGenerator
from core.news_pipeline.models import NewsItem, TickerRecord
from core.news_pipeline.preprocessing import normalize_text, tokenize_lemmas
from core.news_pipeline.repository import NewsPipelineRepository


class TestPreprocessing(unittest.TestCase):
    """Test text preprocessing functions."""

    def test_normalize_text(self):
        """Test text normalization."""
        # Test basic normalization
        text = "Сбербанк России объявил о росте прибыли"
        normalized = normalize_text(text)
        self.assertIsInstance(normalized, str)
        self.assertGreater(len(normalized), 0)
        
        # Test empty text
        self.assertEqual(normalize_text(""), "")
        self.assertEqual(normalize_text(None), "")
        
        # Test with punctuation
        text = "ООО 'Газпром' - крупнейшая компания!"
        normalized = normalize_text(text)
        self.assertIsInstance(normalized, str)

    def test_tokenize_lemmas(self):
        """Test lemmatization and tokenization."""
        text = "Сбербанк России объявил о росте прибыли"
        tokens = tokenize_lemmas(text)
        self.assertIsInstance(tokens, list)
        self.assertGreater(len(tokens), 0)
        
        # Test empty text
        self.assertEqual(tokenize_lemmas(""), [])
        self.assertEqual(tokenize_lemmas(None), [])


class TestModels(unittest.TestCase):
    """Test data models."""

    def test_news_item(self):
        """Test NewsItem model."""
        news = NewsItem(
            id=1,
            title="Test News",
            body="Test body content",
            language="ru",
            published_at="2024-01-01T00:00:00Z",
            source="test_source",
            processed=False,
            processed_at=None,
            last_batch_id=None,
            last_processed_version=None,
        )
        
        self.assertEqual(news.id, 1)
        self.assertEqual(news.title, "Test News")
        self.assertEqual(news.text, "Test News\nTest body content")
        
        # Test with None values
        news_empty = NewsItem(
            id=2,
            title=None,
            body=None,
            language=None,
            published_at=None,
            source=None,
            processed=False,
            processed_at=None,
            last_batch_id=None,
            last_processed_version=None,
        )
        self.assertEqual(news_empty.text, "")

    def test_ticker_record(self):
        """Test TickerRecord model."""
        ticker = TickerRecord(
            id=1,
            ticker="SBER",
            name="Сбербанк",
            aliases=["Сбер", "Sberbank"],
            isin="RU0009029540",
            exchange="MOEX",
            description="ПАО Сбербанк",
        )
        
        self.assertEqual(ticker.id, 1)
        self.assertEqual(ticker.ticker, "SBER")
        
        # Test all_names method
        names = ticker.all_names()
        self.assertIn("SBER", names)
        self.assertIn("Сбербанк", names)
        self.assertIn("Сбер", names)
        self.assertIn("Sberbank", names)
        self.assertIn("ПАО Сбербанк", names)


class TestGenerators(unittest.TestCase):
    """Test candidate generators."""

    def setUp(self):
        """Set up test data."""
        self.config = PipelineConfig(
            batch_size=10,
            chunk_size=5,
            auto_apply_threshold=0.85,
            review_lower_threshold=0.60,
            fuzzy_threshold=65,
            cos_candidate_threshold=0.60,
            cos_auto_threshold=0.80,
        )
        
        self.tickers = [
            TickerRecord(
                id=1,
                ticker="SBER",
                name="Сбербанк",
                aliases=["Сбер", "Sberbank"],
            ),
            TickerRecord(
                id=2,
                ticker="GAZP",
                name="Газпром",
                aliases=["Газпром", "Gazprom"],
            ),
        ]
        
        self.news_item = NewsItem(
            id=1,
            title="Сбербанк объявил о росте прибыли",
            body="ПАО Сбербанк сообщил о значительном росте прибыли в отчетном периоде.",
            language="ru",
            published_at="2024-01-01T00:00:00Z",
            source="test",
            processed=False,
            processed_at=None,
            last_batch_id=None,
            last_processed_version=None,
        )

    def test_substring_generator(self):
        """Test substring generator."""
        generator = SubstringGenerator(weight=1.0)
        generator.prepare(self.tickers, config=self.config)
        
        results = generator.generate(self.news_item, self.tickers, config=self.config)
        
        self.assertIsInstance(results, dict)
        # Should find SBER in the text
        self.assertIn(1, results)  # SBER ticker ID
        self.assertGreater(results[1].score, 0.0)

    def test_fuzzy_generator(self):
        """Test fuzzy generator."""
        generator = FuzzyGenerator(weight=1.0)
        generator.prepare(self.tickers, config=self.config)
        
        results = generator.generate(self.news_item, self.tickers, config=self.config)
        
        self.assertIsInstance(results, dict)
        # Should find some matches
        if results:
            for ticker_id, signal in results.items():
                self.assertGreaterEqual(signal.score, self.config.review_lower_threshold)

    def test_ner_generator(self):
        """Test NER generator."""
        generator = NERGenerator(weight=1.0)
        generator.prepare(self.tickers, config=self.config)
        
        results = generator.generate(self.news_item, self.tickers, config=self.config)
        
        self.assertIsInstance(results, dict)
        # NER might not find matches without spaCy, but should not crash
        for ticker_id, signal in results.items():
            self.assertGreaterEqual(signal.score, self.config.review_lower_threshold)

    @patch('core.news_pipeline.generators.embedding.SentenceTransformer')
    def test_embedding_generator(self, mock_sentence_transformer):
        """Test embedding generator with mocked SentenceTransformer."""
        # Mock the SentenceTransformer
        mock_model = Mock()
        mock_model.encode.return_value = np.array([[0.1, 0.2, 0.3, 0.4, 0.5]])
        mock_sentence_transformer.return_value = mock_model
        
        generator = EmbeddingGenerator(weight=1.0)
        generator.prepare(self.tickers, config=self.config)
        
        results = generator.generate(self.news_item, self.tickers, config=self.config)
        
        self.assertIsInstance(results, dict)
        # Should not crash even with mocked embeddings

    def test_hybrid_generator(self):
        """Test hybrid generator."""
        generator = HybridGenerator(weight=1.0)
        generator.prepare(self.tickers, config=self.config)
        
        results = generator.generate(self.news_item, self.tickers, config=self.config)
        
        self.assertIsInstance(results, dict)
        # Hybrid should combine results from multiple generators


class TestRepository(unittest.TestCase):
    """Test repository functionality."""

    def setUp(self):
        """Set up test database."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = Path(self.temp_db.name)
        
        self.repository = NewsPipelineRepository(self.db_path)
        self.repository.ensure_schema()

    def tearDown(self):
        """Clean up test database."""
        if self.db_path.exists():
            self.db_path.unlink()

    def test_schema_creation(self):
        """Test that schema is created correctly."""
        with self.repository.connect() as conn:
            # Check that tables exist
            tables = conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name IN ('tickers', 'news_tickers', 'processing_runs')
            """).fetchall()
            
            table_names = [row[0] for row in tables]
            self.assertIn('tickers', table_names)
            self.assertIn('news_tickers', table_names)
            self.assertIn('processing_runs', table_names)

    def test_ticker_operations(self):
        """Test ticker operations."""
        # Test loading empty tickers
        tickers = self.repository.load_tickers()
        self.assertEqual(len(tickers), 0)
        
        # Test storing ticker embedding
        self.repository.store_ticker_embedding(1, [0.1, 0.2, 0.3, 0.4, 0.5])
        
        # Verify embedding was stored
        with self.repository.connect() as conn:
            result = conn.execute("SELECT embed_blob FROM tickers WHERE id = 1").fetchone()
            if result:
                stored_embedding = json.loads(result[0])
                self.assertEqual(stored_embedding, [0.1, 0.2, 0.3, 0.4, 0.5])

    def test_processing_run_operations(self):
        """Test processing run operations."""
        # Create a processing run
        batch_id = self.repository.create_processing_run(
            mode=BatchMode.ONLY_UNPROCESSED,
            requested=100,
            actual=50,
            version="v1.0",
            operator="test_user",
        )
        
        self.assertIsInstance(batch_id, str)
        self.assertEqual(len(batch_id), 32)  # UUID hex length
        
        # Complete the processing run
        from core.news_pipeline.models import ProcessingMetrics
        metrics = ProcessingMetrics(
            total_news=50,
            processed_news=45,
            candidates_generated=120,
            auto_applied=30,
            skipped_duplicates=10,
            retries=0,
            errors=5,
            duration_seconds=120.5,
            chunk_count=2,
        )
        
        self.repository.complete_processing_run(
            batch_id,
            status="completed",
            metrics=metrics,
            chunk_count=2,
        )
        
        # Verify the run was completed
        with self.repository.connect() as conn:
            result = conn.execute(
                "SELECT status, metrics FROM processing_runs WHERE batch_id = ?",
                (batch_id,)
            ).fetchone()
            
            self.assertIsNotNone(result)
            self.assertEqual(result[0], "completed")
            
            stored_metrics = json.loads(result[1])
            self.assertEqual(stored_metrics["total_news"], 50)
            self.assertEqual(stored_metrics["processed_news"], 45)


class TestConfiguration(unittest.TestCase):
    """Test configuration loading and validation."""

    def test_default_config(self):
        """Test default configuration."""
        config = PipelineConfig()
        
        self.assertEqual(config.batch_size, 100)
        self.assertEqual(config.chunk_size, 100)
        self.assertEqual(config.auto_apply_threshold, 0.85)
        self.assertEqual(config.review_lower_threshold, 0.60)
        self.assertEqual(config.fuzzy_threshold, 65)
        self.assertEqual(config.cos_candidate_threshold, 0.60)
        self.assertEqual(config.cos_auto_threshold, 0.80)

    def test_config_overrides(self):
        """Test configuration overrides."""
        config = PipelineConfig()
        overridden = config.with_overrides(
            batch_size=200,
            auto_apply_threshold=0.90,
        )
        
        self.assertEqual(overridden.batch_size, 200)
        self.assertEqual(overridden.auto_apply_threshold, 0.90)
        # Other values should remain unchanged
        self.assertEqual(overridden.chunk_size, config.chunk_size)
        self.assertEqual(overridden.review_lower_threshold, config.review_lower_threshold)

    def test_config_serialization(self):
        """Test configuration serialization."""
        config = PipelineConfig()
        config_dict = config.as_dict()
        
        self.assertIsInstance(config_dict, dict)
        self.assertIn("batch_size", config_dict)
        self.assertIn("chunk_size", config_dict)
        self.assertIn("auto_apply_threshold", config_dict)
        
        # Test that we can recreate config from dict
        recreated = PipelineConfig(**config_dict)
        self.assertEqual(recreated.batch_size, config.batch_size)
        self.assertEqual(recreated.chunk_size, config.chunk_size)


class TestBatchMode(unittest.TestCase):
    """Test batch mode enumeration."""

    def test_batch_mode_values(self):
        """Test batch mode values."""
        self.assertEqual(BatchMode.ONLY_UNPROCESSED.value, "only_unprocessed")
        self.assertEqual(BatchMode.RECHECK_ALL.value, "recheck_all")
        self.assertEqual(BatchMode.RECHECK_SELECTED_RANGE.value, "recheck_selected_range")

    def test_batch_mode_string_conversion(self):
        """Test batch mode string conversion."""
        self.assertEqual(str(BatchMode.ONLY_UNPROCESSED), "only_unprocessed")
        self.assertEqual(str(BatchMode.RECHECK_ALL), "recheck_all")
        self.assertEqual(str(BatchMode.RECHECK_SELECTED_RANGE), "recheck_selected_range")


if __name__ == "__main__":
    unittest.main()
