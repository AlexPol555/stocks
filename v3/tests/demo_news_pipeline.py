#!/usr/bin/env python3
"""
Демонстрационный скрипт для News Pipeline
Показывает основные возможности системы обработки новостей
"""

import json
import logging
import tempfile
from pathlib import Path
from typing import List

from core.news_pipeline import (
    BatchMode,
    NewsBatchProcessor,
    PipelineConfig,
    PipelineRequest,
    load_pipeline_config,
)
from core.news_pipeline.models import NewsItem, TickerRecord
from core.news_pipeline.repository import NewsPipelineRepository

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_test_data() -> List[NewsItem]:
    """Создать тестовые данные новостей."""
    return [
        NewsItem(
            id=1,
            title="Сбербанк объявил о новых продуктах для малого бизнеса",
            url="https://example.com/sber-news-1",
            published_at="2025-01-01T10:00:00Z",
            body="Сбербанк представил новые кредитные продукты для малого и среднего бизнеса...",
            source="РБК"
        ),
        NewsItem(
            id=2,
            title="Газпром увеличил добычу газа на 15%",
            url="https://example.com/gazp-news-1",
            published_at="2025-01-01T11:00:00Z",
            body="Газпром сообщил об увеличении добычи природного газа...",
            source="Интерфакс"
        ),
        NewsItem(
            id=3,
            title="Лукойл открыл новое месторождение в Сибири",
            url="https://example.com/lkoh-news-1",
            published_at="2025-01-01T12:00:00Z",
            body="Лукойл объявил об открытии нового нефтяного месторождения...",
            source="ТАСС"
        ),
        NewsItem(
            id=4,
            title="МТС запустил 5G сеть в Москве",
            url="https://example.com/mts-news-1",
            published_at="2025-01-01T13:00:00Z",
            body="МТС объявил о запуске сети 5G в столице...",
            source="Ведомости"
        ),
        NewsItem(
            id=5,
            title="Яндекс представил новый алгоритм поиска",
            url="https://example.com/yandex-news-1",
            published_at="2025-01-01T14:00:00Z",
            body="Яндекс анонсировал обновление алгоритма поиска...",
            source="Хабрахабр"
        )
    ]


def create_test_tickers() -> List[TickerRecord]:
    """Создать тестовые тикеры."""
    return [
        TickerRecord(
            id=1,
            ticker="SBER",
            name="Сбербанк",
            aliases=["Сбербанк", "Сбер", "SBER", "ПАО Сбербанк"],
            exchange="MOEX",
            description="Крупнейший банк России"
        ),
        TickerRecord(
            id=2,
            ticker="GAZP",
            name="Газпром",
            aliases=["Газпром", "GAZP", "ПАО Газпром"],
            exchange="MOEX",
            description="Крупнейшая газовая компания России"
        ),
        TickerRecord(
            id=3,
            ticker="LKOH",
            name="Лукойл",
            aliases=["Лукойл", "LKOH", "ПАО Лукойл"],
            exchange="MOEX",
            description="Крупнейшая нефтяная компания России"
        ),
        TickerRecord(
            id=4,
            ticker="MTSS",
            name="МТС",
            aliases=["МТС", "MTSS", "ПАО МТС"],
            exchange="MOEX",
            description="Крупнейший оператор связи России"
        ),
        TickerRecord(
            id=5,
            ticker="YNDX",
            name="Яндекс",
            aliases=["Яндекс", "YNDX", "Yandex"],
            exchange="NASDAQ",
            description="Крупнейшая IT компания России"
        )
    ]


def main():
    """Основная функция демонстрации."""
    print("🚀 Демонстрация News Pipeline")
    print("=" * 50)
    
    # Создаем временную базу данных
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
        db_path = tmp_db.name
    
    try:
        # Создаем репозиторий
        print("📁 Создание репозитория...")
        repository = NewsPipelineRepository(db_path)
        repository.ensure_schema()
        print("✅ Репозиторий создан")
        
        # Загружаем тестовые данные
        print("\n📰 Загрузка тестовых новостей...")
        news_items = create_test_data()
        for item in news_items:
            repository.insert_article(item)
        print(f"✅ Загружено {len(news_items)} новостей")
        
        # Загружаем тестовые тикеры
        print("\n🏷️  Загрузка тестовых тикеров...")
        tickers = create_test_tickers()
        for ticker in tickers:
            repository.insert_ticker(ticker)
        print(f"✅ Загружено {len(tickers)} тикеров")
        
        # Создаем конфигурацию
        print("\n⚙️  Создание конфигурации...")
        config = PipelineConfig(
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
            auto_apply_confirm=True
        )
        print("✅ Конфигурация создана")
        
        # Создаем процессор
        print("\n🔧 Создание процессора...")
        processor = NewsBatchProcessor(repository)
        processor.initialize(config)
        print("✅ Процессор создан и инициализирован")
        
        # Создаем запрос на обработку
        print("\n📋 Создание запроса на обработку...")
        request = PipelineRequest(
            mode=BatchMode.ONLY_UNPROCESSED,
            batch_size=10,
            chunk_size=5
        )
        print("✅ Запрос создан")
        
        # Запускаем обработку
        print("\n🚀 Запуск обработки...")
        result = processor.process_batch(request)
        print(f"✅ Обработка завершена")
        print(f"   - Обработано статей: {result.processed_count}")
        print(f"   - Создано кандидатов: {result.candidates_count}")
        print(f"   - Время обработки: {result.processing_time:.2f} сек")
        
        # Получаем кандидатов для валидации
        print("\n🔍 Получение кандидатов для валидации...")
        candidates = repository.fetch_pending_candidates(limit=10)
        print(f"✅ Найдено {len(candidates)} кандидатов")
        
        # Показываем примеры кандидатов
        if candidates:
            print("\n📊 Примеры кандидатов:")
            for i, candidate in enumerate(candidates[:3], 1):
                print(f"   {i}. {candidate.ticker} - {candidate.score:.3f} ({candidate.method})")
        
        # Получаем статистику
        print("\n📈 Статистика базы данных:")
        with repository.connect() as conn:
            articles_count = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
            tickers_count = conn.execute("SELECT COUNT(*) FROM tickers").fetchone()[0]
            candidates_count = conn.execute("SELECT COUNT(*) FROM news_tickers").fetchone()[0]
            confirmed_count = conn.execute("SELECT COUNT(*) FROM news_tickers WHERE confirmed = 1").fetchone()[0]
            
            print(f"   - Статей: {articles_count}")
            print(f"   - Тикеров: {tickers_count}")
            print(f"   - Кандидатов: {candidates_count}")
            print(f"   - Подтвержденных: {confirmed_count}")
        
        print("\n🎉 Демонстрация завершена успешно!")
        print(f"База данных сохранена в: {db_path}")
        
    except Exception as e:
        print(f"\n❌ Ошибка во время демонстрации: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Очищаем временный файл
        try:
            Path(db_path).unlink()
        except:
            pass


if __name__ == "__main__":
    main()
