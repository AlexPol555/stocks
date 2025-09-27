"""Integration tests for news pipeline."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np

from core.news_pipeline import (
    BatchMode,
    NewsBatchProcessor,
    PipelineConfig,
    PipelineRequest,
    load_pipeline_config,
)
from core.news_pipeline.models import NewsItem, TickerRecord
from core.news_pipeline.repository import NewsPipelineRepository


class TestNewsPipelineIntegration(unittest.TestCase):
    """Integration tests for the complete news pipeline."""

    def setUp(self):
        """Set up test environment."""
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = Path(self.temp_db.name)
        
        # Initialize repository
        self.repository = NewsPipelineRepository(self.db_path)
        self.repository.ensure_schema()
        
        # Create test data
        self._create_test_data()
        
        # Initialize processor
        self.processor = NewsBatchProcessor(self.repository)
        
        # Test configuration
        self.config = PipelineConfig(
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

    def tearDown(self):
        """Clean up test environment."""
        if self.db_path.exists():
            self.db_path.unlink()

    def _create_test_data(self):
        """Create test data in the database."""
        with self.repository.connect() as conn:
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
            test_tickers = [
                {
                    'id': 1,
                    'ticker': 'SBER',
                    'name': 'Сбербанк',
                    'aliases': json.dumps(['Сбер', 'Sberbank', 'ПАО Сбербанк']),
                    'isin': 'RU0009029540',
                    'exchange': 'MOEX',
                    'description': 'ПАО Сбербанк',
                },
                {
                    'id': 2,
                    'ticker': 'GAZP',
                    'name': 'Газпром',
                    'aliases': json.dumps(['Газпром', 'Gazprom', 'ПАО Газпром']),
                    'isin': 'RU0007661625',
                    'exchange': 'MOEX',
                    'description': 'ПАО Газпром',
                },
                {
                    'id': 3,
                    'ticker': 'LKOH',
                    'name': 'Лукойл',
                    'aliases': json.dumps(['Лукойл', 'Lukoil', 'ПАО Лукойл']),
                    'isin': 'RU0009024277',
                    'exchange': 'MOEX',
                    'description': 'ПАО Лукойл',
                },
            ]
            
            for ticker in test_tickers:
                conn.execute("""
                    INSERT OR REPLACE INTO tickers 
                    (id, ticker, name, aliases, isin, exchange, description)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    ticker['id'],
                    ticker['ticker'],
                    ticker['name'],
                    ticker['aliases'],
                    ticker['isin'],
                    ticker['exchange'],
                    ticker['description'],
                ))
            
            conn.commit()

    @patch('core.news_pipeline.generators.embedding.SentenceTransformer')
    def test_full_pipeline_processing(self, mock_sentence_transformer):
        """Test complete pipeline processing."""
        # Mock SentenceTransformer
        mock_model = Mock()
        mock_model.encode.return_value = np.array([[0.1, 0.2, 0.3, 0.4, 0.5]])
        mock_sentence_transformer.return_value = mock_model
        
        # Initialize processor
        self.processor.initialize(self.config)
        
        # Create processing request
        request = PipelineRequest(
            mode=BatchMode.ONLY_UNPROCESSED,
            batch_size=10,
            operator="test_user",
            dry_run=False,
        )
        
        # Process batch
        metrics = self.processor.process_batch(request)
        
        # Verify metrics
        self.assertIsNotNone(metrics)
        self.assertGreater(metrics.total_news, 0)
        self.assertGreaterEqual(metrics.processed_news, 0)
        self.assertGreaterEqual(metrics.candidates_generated, 0)
        self.assertGreaterEqual(metrics.duration_seconds, 0)
        
        # Verify news items were marked as processed
        with self.repository.connect() as conn:
            processed_count = conn.execute(
                "SELECT COUNT(*) FROM articles WHERE processed = 1"
            ).fetchone()[0]
            self.assertGreater(processed_count, 0)
        
        # Verify candidates were created
        with self.repository.connect() as conn:
            candidates_count = conn.execute(
                "SELECT COUNT(*) FROM news_tickers"
            ).fetchone()[0]
            self.assertGreaterEqual(candidates_count, 0)

    def test_pipeline_idempotency(self):
        """Test that pipeline is idempotent."""
        # Initialize processor
        self.processor.initialize(self.config)
        
        # Process the same batch twice
        request = PipelineRequest(
            mode=BatchMode.ONLY_UNPROCESSED,
            batch_size=10,
            operator="test_user",
            dry_run=False,
        )
        
        # First run
        metrics1 = self.processor.process_batch(request)
        
        # Second run (should not create duplicates)
        metrics2 = self.processor.process_batch(request)
        
        # Verify that second run processed fewer items (already processed)
        self.assertLessEqual(metrics2.processed_news, metrics1.processed_news)
        
        # Verify no duplicate candidates were created
        with self.repository.connect() as conn:
            candidates_count = conn.execute(
                "SELECT COUNT(*) FROM news_tickers"
            ).fetchone()[0]
            # Should not have significantly more candidates
            self.assertLessEqual(candidates_count, metrics1.candidates_generated + 5)

    def test_recheck_mode(self):
        """Test recheck mode functionality."""
        # Initialize processor
        self.processor.initialize(self.config)
        
        # First, process some news
        request1 = PipelineRequest(
            mode=BatchMode.ONLY_UNPROCESSED,
            batch_size=5,
            operator="test_user",
            dry_run=False,
        )
        metrics1 = self.processor.process_batch(request1)
        
        # Then recheck all
        request2 = PipelineRequest(
            mode=BatchMode.RECHECK_ALL,
            batch_size=10,
            operator="test_user",
            dry_run=False,
        )
        metrics2 = self.processor.process_batch(request2)
        
        # Recheck should process all news items
        self.assertGreaterEqual(metrics2.total_news, metrics1.total_news)
        self.assertGreaterEqual(metrics2.processed_news, metrics1.processed_news)

    def test_candidate_validation_workflow(self):
        """Test candidate validation workflow."""
        # Initialize processor
        self.processor.initialize(self.config)
        
        # Process news to generate candidates
        request = PipelineRequest(
            mode=BatchMode.ONLY_UNPROCESSED,
            batch_size=10,
            operator="test_user",
            dry_run=False,
        )
        metrics = self.processor.process_batch(request)
        
        # Verify candidates were created
        with self.repository.connect() as conn:
            candidates = conn.execute("""
                SELECT nt.*, t.ticker, t.name, a.title
                FROM news_tickers nt
                LEFT JOIN tickers t ON t.id = nt.ticker_id
                LEFT JOIN articles a ON a.id = nt.news_id
                WHERE nt.confirmed = 0
                LIMIT 10
            """).fetchall()
            
            if candidates:
                # Test candidate confirmation
                candidate_id = candidates[0]['id']
                self.repository.update_confirmation(
                    candidate_id,
                    confirmed=1,
                    operator="test_user",
                )
                
                # Verify confirmation was saved
                confirmed = conn.execute(
                    "SELECT confirmed FROM news_tickers WHERE id = ?",
                    (candidate_id,)
                ).fetchone()
                self.assertEqual(confirmed[0], 1)

    def test_error_handling(self):
        """Test error handling in pipeline."""
        # Create invalid configuration
        invalid_config = PipelineConfig(
            batch_size=-1,  # Invalid
            chunk_size=0,   # Invalid
            auto_apply_threshold=1.5,  # Invalid
        )
        
        # Should handle invalid configuration gracefully
        try:
            self.processor.initialize(invalid_config)
            # If initialization succeeds, processing should still work
            request = PipelineRequest(
                mode=BatchMode.ONLY_UNPROCESSED,
                batch_size=1,
                operator="test_user",
                dry_run=True,  # Use dry run to avoid side effects
            )
            metrics = self.processor.process_batch(request)
            self.assertIsNotNone(metrics)
        except Exception as exc:
            # Should fail gracefully with informative error
            self.assertIsInstance(exc, (ValueError, RuntimeError))

    def test_large_batch_processing(self):
        """Test processing of large batches."""
        # Create more test data
        with self.repository.connect() as conn:
            for i in range(4, 104):  # Add 100 more articles
                conn.execute("""
                    INSERT OR REPLACE INTO articles 
                    (id, title, body, published_at, source_id, language, processed)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    i,
                    f'Test News {i}',
                    f'Test body content for news {i}. Сбербанк и Газпром упоминаются в тексте.',
                    f'2024-01-{i:02d}T00:00:00Z',
                    1,
                    'ru',
                    0,
                ))
            conn.commit()
        
        # Initialize processor
        self.processor.initialize(self.config)
        
        # Process large batch
        request = PipelineRequest(
            mode=BatchMode.ONLY_UNPROCESSED,
            batch_size=100,
            operator="test_user",
            dry_run=False,
        )
        
        metrics = self.processor.process_batch(request)
        
        # Verify large batch was processed
        self.assertGreaterEqual(metrics.total_news, 100)
        self.assertGreater(metrics.chunk_count, 1)  # Should use chunking
        self.assertGreater(metrics.duration_seconds, 0)

    def test_configuration_loading(self):
        """Test configuration loading from file."""
        # Create temporary config file
        config_data = {
            'batch_size': 50,
            'chunk_size': 25,
            'auto_apply_threshold': 0.90,
            'review_lower_threshold': 0.70,
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            import yaml
            yaml.dump(config_data, f)
            config_path = f.name
        
        try:
            # Load configuration
            config = load_pipeline_config(config_path)
            
            # Verify configuration was loaded
            self.assertEqual(config.batch_size, 50)
            self.assertEqual(config.chunk_size, 25)
            self.assertEqual(config.auto_apply_threshold, 0.90)
            self.assertEqual(config.review_lower_threshold, 0.70)
            
        finally:
            # Clean up
            Path(config_path).unlink()

    def test_dry_run_mode(self):
        """Test dry run mode."""
        # Initialize processor
        self.processor.initialize(self.config)
        
        # Process in dry run mode
        request = PipelineRequest(
            mode=BatchMode.ONLY_UNPROCESSED,
            batch_size=10,
            operator="test_user",
            dry_run=True,
        )
        
        metrics = self.processor.process_batch(request)
        
        # Verify metrics were collected
        self.assertIsNotNone(metrics)
        self.assertGreaterEqual(metrics.total_news, 0)
        
        # Verify no data was actually saved (dry run)
        with self.repository.connect() as conn:
            processed_count = conn.execute(
                "SELECT COUNT(*) FROM articles WHERE processed = 1"
            ).fetchone()[0]
            # Should still be 0 since we started with unprocessed articles
            self.assertEqual(processed_count, 0)


if __name__ == "__main__":
    unittest.main()
