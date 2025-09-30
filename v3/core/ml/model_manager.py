"""
Менеджер ML моделей с поддержкой разных таймфреймов.
Управляет обучением, кэшированием и предсказаниями.
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple, Union
import pandas as pd
import numpy as np

from .storage import ml_storage
from .predictive_models import LSTMPredictor, GRUPredictor, ModelConfig
from .sentiment_analysis import NewsSentimentAnalyzer, SentimentConfig
from .clustering import StockClusterer, ClusteringConfig
from .ensemble_methods import EnsemblePredictor, EnsembleConfig

logger = logging.getLogger(__name__)


class MLModelManager:
    """Менеджер ML моделей с поддержкой разных таймфреймов."""
    
    def __init__(self, db_path: str = "stock_data.db"):
        self.db_path = db_path
        self.storage = ml_storage
        
        # Кэш обученных моделей
        self.trained_models = {}
        
        # Конфигурации по умолчанию для разных таймфреймов
        self.timeframe_configs = {
            '1d': {
                'sequence_length': 60,
                'hidden_size': 50,
                'epochs': 100,
                'batch_size': 32,
                'learning_rate': 0.001,
                'validation_split': 0.2
            },
            '1h': {
                'sequence_length': 168,  # 1 неделя часовых данных
                'hidden_size': 64,
                'epochs': 150,
                'batch_size': 64,
                'learning_rate': 0.0008,
                'validation_split': 0.2
            },
            '1m': {
                'sequence_length': 1440,  # 1 день минутных данных
                'hidden_size': 128,
                'epochs': 200,
                'batch_size': 128,
                'learning_rate': 0.0005,
                'validation_split': 0.15
            },
            '1s': {
                'sequence_length': 3600,  # 1 час секундных данных
                'hidden_size': 256,
                'epochs': 300,
                'batch_size': 256,
                'learning_rate': 0.0003,
                'validation_split': 0.1
            }
        }
    
    def get_or_train_model(self, symbol: str, model_type: str = 'lstm', 
                          timeframe: str = '1d', force_retrain: bool = False) -> Tuple[Any, Dict[str, Any]]:
        """
        Получить модель или обучить новую.
        
        Args:
            symbol: Символ акции
            model_type: Тип модели ('lstm', 'gru', 'ensemble', 'sentiment')
            timeframe: Таймфрейм ('1d', '1h', '1m', '1s')
            force_retrain: Принудительное переобучение
            
        Returns:
            Tuple[модель, метаданные]
        """
        # Проверяем кэш
        if not force_retrain:
            model, metadata = self.storage.get_model(symbol, model_type, timeframe)
            if model is not None:
                logger.debug(f"Using cached model for {symbol}_{model_type}_{timeframe}")
                return model, metadata
        
        # Обучаем новую модель
        logger.info(f"Training new {model_type} model for {symbol} ({timeframe})")
        return self._train_model(symbol, model_type, timeframe)
    
    def predict_price_movement(self, symbol: str, timeframe: str = '1d', 
                             days_ahead: int = 1, use_cache: bool = True) -> Dict[str, Any]:
        """
        Предсказать движение цены.
        
        Args:
            symbol: Символ акции
            timeframe: Таймфрейм данных
            days_ahead: На сколько дней вперед предсказывать
            use_cache: Использовать кэш предсказаний
            
        Returns:
            Словарь с результатами предсказания
        """
        # Проверяем кэш предсказаний
        if use_cache:
            cached_prediction = self.storage.get_prediction(symbol, 'price', timeframe)
            if cached_prediction:
                logger.debug(f"Using cached price prediction for {symbol}")
                return {
                    'prediction': cached_prediction['prediction'],
                    'confidence': cached_prediction['confidence'],
                    'cached': True,
                    'cache_date': cached_prediction['date']
                }
        
        try:
            # Получаем данные
            historical_data = self._get_stock_data_from_db(symbol, timeframe)
            if historical_data.empty:
                return {'error': f'No historical data available for {symbol}'}
            
            # Получаем или обучаем модель
            model, metadata = self.get_or_train_model(symbol, 'lstm', timeframe)
            
            if model is None:
                return {'error': f'Failed to train model for {symbol}'}
            
            # Делаем предсказание
            prediction_result = model.predict(historical_data.tail(100))
            
            prediction = prediction_result.predictions[-1] if len(prediction_result.predictions) > 0 else 0
            confidence = prediction_result.confidence
            
            # Сохраняем в кэш
            self.storage.save_prediction(symbol, 'price', prediction, confidence, timeframe)
            
            return {
                'prediction': prediction,
                'confidence': confidence,
                'model_metrics': {
                    'mse': prediction_result.mse,
                    'mae': prediction_result.mae,
                    'rmse': prediction_result.rmse
                },
                'training_metrics': metadata,
                'cached': False
            }
            
        except Exception as e:
            logger.error(f"Error predicting price movement for {symbol}: {e}")
            return {'error': str(e)}
    
    def analyze_sentiment(self, symbol: str, timeframe: str = '1d', 
                         use_cache: bool = True) -> Dict[str, Any]:
        """Анализ настроений для символа."""
        # Проверяем кэш
        if use_cache:
            cached_sentiment = self.storage.get_prediction(symbol, 'sentiment', timeframe)
            if cached_sentiment:
                logger.debug(f"Using cached sentiment for {symbol}")
                return {
                    'sentiment': cached_sentiment['prediction'],
                    'confidence': cached_sentiment['confidence'],
                    'cached': True,
                    'cache_date': cached_sentiment['date']
                }
        
        try:
            # Получаем новости
            news_data = self._get_news_data_from_db(symbol, timeframe)
            
            if news_data.empty:
                return {'error': f'No news data available for {symbol}'}
            
            # Анализируем настроения
            sentiment_config = SentimentConfig()
            sentiment_analyzer = NewsSentimentAnalyzer(sentiment_config)
            
            # Объединяем заголовки и контент
            texts = []
            for _, row in news_data.iterrows():
                text_parts = []
                if pd.notna(row.get('title')):
                    text_parts.append(str(row['title']))
                if pd.notna(row.get('content')):
                    text_parts.append(str(row['content']))
                if text_parts:
                    texts.append(' '.join(text_parts))
            
            if not texts:
                return {'error': 'No valid news texts found'}
            
            # Анализируем настроения
            sentiment_results = sentiment_analyzer.analyze_batch(texts[:10])  # Ограничиваем количество
            
            # Агрегируем результаты
            sentiments = [r.sentiment for r in sentiment_results]
            confidences = [r.confidence for r in sentiment_results]
            
            # Определяем общее настроение
            sentiment_counts = {'positive': 0, 'negative': 0, 'neutral': 0}
            for sentiment in sentiments:
                sentiment_counts[sentiment] += 1
            
            overall_sentiment = max(sentiment_counts, key=sentiment_counts.get)
            avg_confidence = np.mean(confidences) if confidences else 0.5
            
            # Сохраняем в кэш
            self.storage.save_prediction(symbol, 'sentiment', 
                                       float(sentiment_counts[overall_sentiment] / len(sentiments)), 
                                       avg_confidence, timeframe)
            
            return {
                'sentiment': overall_sentiment,
                'confidence': avg_confidence,
                'sentiment_distribution': sentiment_counts,
                'news_count': len(texts),
                'cached': False
            }
            
        except Exception as e:
            logger.error(f"Error analyzing sentiment for {symbol}: {e}")
            return {'error': str(e)}
    
    def cluster_stocks(self, symbols: List[str], timeframe: str = '1d', 
                      n_clusters: int = 5) -> Dict[str, Any]:
        """Кластеризация акций."""
        try:
            # Получаем данные для всех символов
            all_data = []
            valid_symbols = []
            
            for symbol in symbols:
                data = self._get_stock_data_from_db(symbol, timeframe)
                if not data.empty:
                    all_data.append(data)
                    valid_symbols.append(symbol)
            
            if not all_data:
                return {'error': 'No valid data for clustering'}
            
            # Объединяем данные
            combined_data = pd.concat(all_data, ignore_index=True)
            
            # Кластеризация
            clustering_config = ClusteringConfig(n_clusters=n_clusters)
            clusterer = StockClusterer(clustering_config)
            
            clustering_result = clusterer.cluster_stocks(combined_data)
            
            # Создаем маппинг символов к кластерам
            symbol_clusters = {}
            for i, symbol in enumerate(valid_symbols):
                if i < len(clustering_result.cluster_labels):
                    symbol_clusters[symbol] = int(clustering_result.cluster_labels[i])
            
            return {
                'clusters': symbol_clusters,
                'n_clusters': clustering_result.n_clusters,
                'silhouette_score': clustering_result.silhouette_score,
                'symbols_processed': len(valid_symbols)
            }
            
        except Exception as e:
            logger.error(f"Error clustering stocks: {e}")
            return {'error': str(e)}
    
    def get_ensemble_prediction(self, symbol: str, timeframe: str = '1d') -> Dict[str, Any]:
        """Получить ансамблевое предсказание."""
        try:
            # Получаем данные
            historical_data = self._get_stock_data_from_db(symbol, timeframe)
            if historical_data.empty:
                return {'error': f'No historical data available for {symbol}'}
            
            # Создаем ансамбль
            ensemble_config = EnsembleConfig()
            ensemble = EnsemblePredictor(ensemble_config)
            
            # Обучаем ансамбль
            ensemble_result = ensemble.predict(historical_data)
            
            return {
                'prediction': ensemble_result.predictions[-1] if len(ensemble_result.predictions) > 0 else 0,
                'confidence': ensemble_result.confidence,
                'model_type': 'ensemble',
                'individual_predictions': getattr(ensemble_result, 'individual_predictions', {}),
                'weights': getattr(ensemble_result, 'weights', {})
            }
            
        except Exception as e:
            logger.error(f"Error getting ensemble prediction for {symbol}: {e}")
            return {'error': str(e)}
    
    def get_model_status(self, timeframe: Optional[str] = None) -> Dict[str, Any]:
        """Получить статус моделей."""
        try:
            # Получаем активные модели
            models_df = self.storage.get_active_models(timeframe)
            
            # Статистика по таймфреймам
            timeframe_stats = {}
            for tf in ['1d', '1h', '1m', '1s']:
                tf_models = models_df[models_df['timeframe'] == tf] if not models_df.empty else pd.DataFrame()
                timeframe_stats[tf] = {
                    'total_models': len(tf_models),
                    'symbols': tf_models['symbol'].nunique() if not tf_models.empty else 0,
                    'avg_accuracy': tf_models['accuracy'].mean() if not tf_models.empty and 'accuracy' in tf_models.columns else 0.0,
                    'latest_training': tf_models['training_date'].max() if not tf_models.empty and 'training_date' in tf_models.columns else None
                }
            
            # Общая статистика
            total_models = len(models_df)
            total_symbols = models_df['symbol'].nunique() if not models_df.empty else 0
            avg_accuracy = models_df['accuracy'].mean() if not models_df.empty and 'accuracy' in models_df.columns else 0.0
            
            return {
                'total_models': total_models,
                'total_symbols': total_symbols,
                'average_accuracy': avg_accuracy,
                'timeframe_stats': timeframe_stats,
                'models': models_df.to_dict('records') if not models_df.empty else []
            }
            
        except Exception as e:
            logger.error(f"Error getting model status: {e}")
            return {'error': str(e)}
    
    def cleanup_expired_models(self) -> int:
        """Очистить устаревшие модели."""
        return self.storage.cleanup_expired_models()
    
    def _train_model(self, symbol: str, model_type: str, timeframe: str) -> Tuple[Any, Dict[str, Any]]:
        """Обучить модель."""
        try:
            # Получаем данные
            historical_data = self._get_stock_data_from_db(symbol, timeframe)
            if historical_data.empty:
                raise ValueError(f'No historical data available for {symbol}')
            
            # Получаем конфигурацию для таймфрейма
            config_params = self.timeframe_configs.get(timeframe, self.timeframe_configs['1d'])
            
            # Создаем модель
            if model_type == 'lstm':
                model_config = ModelConfig(
                    sequence_length=config_params['sequence_length'],
                    hidden_size=config_params['hidden_size'],
                    epochs=config_params['epochs'],
                    batch_size=config_params['batch_size'],
                    learning_rate=config_params['learning_rate'],
                    validation_split=config_params['validation_split']
                )
                model = LSTMPredictor(model_config)
            elif model_type == 'gru':
                model_config = ModelConfig(
                    sequence_length=config_params['sequence_length'],
                    hidden_size=config_params['hidden_size'],
                    epochs=config_params['epochs'],
                    batch_size=config_params['batch_size'],
                    learning_rate=config_params['learning_rate'],
                    validation_split=config_params['validation_split']
                )
                model = GRUPredictor(model_config)
            else:
                raise ValueError(f'Unsupported model type: {model_type}')
            
            # Обучаем модель
            start_time = datetime.now()
            training_result = model.train(historical_data)
            training_duration = (datetime.now() - start_time).total_seconds()
            
            # Подготавливаем метрики
            training_metrics = {
                'accuracy': training_result.get('final_val_loss', 0.0),  # Используем как proxy для accuracy
                'mse': training_result.get('final_train_loss', 0.0),
                'mae': training_result.get('final_train_loss', 0.0),
                'rmse': np.sqrt(training_result.get('final_train_loss', 0.0)),
                'data_points': len(historical_data),
                'epochs_trained': training_result.get('epochs_trained', 0),
                'training_duration': training_duration,
                'sequence_length': config_params['sequence_length'],
                'hidden_size': config_params['hidden_size'],
                'features_used': ['open', 'high', 'low', 'close', 'volume']  # Базовые признаки
            }
            
            # Сохраняем модель
            metadata = self.storage.save_model(symbol, model, model_type, timeframe, training_metrics)
            
            # Записываем в историю обучения
            self._record_training_history(symbol, model_type, timeframe, training_metrics, 'completed')
            
            logger.info(f"Model {symbol}_{model_type}_{timeframe} trained successfully")
            return model, metadata
            
        except Exception as e:
            logger.error(f"Error training model {symbol}_{model_type}_{timeframe}: {e}")
            # Записываем ошибку в историю
            self._record_training_history(symbol, model_type, timeframe, {}, 'failed', str(e))
            raise
    
    def _get_stock_data_from_db(self, symbol: str, timeframe: str = '1d') -> pd.DataFrame:
        """Получить данные акций из БД."""
        import sqlite3
        from pathlib import Path
        
        print(f"    📊 [ML_DATA] Получаем данные для {symbol}...")
        
        db_path = "stock_data.db"
        if not Path(db_path).exists():
            print(f"    ❌ [ML_DATA] {symbol}: База данных не найдена")
            return pd.DataFrame()
        
        conn = sqlite3.connect(db_path)
        try:
            # Базовый запрос для дневных данных
            query = """
                SELECT datetime as date, open, high, low, close, volume
                FROM data_1d 
                WHERE symbol = ?
                ORDER BY datetime DESC
                LIMIT 1000
            """
            
            df = pd.read_sql_query(query, conn, params=(symbol,))
            
            if df.empty:
                print(f"    ❌ [ML_DATA] {symbol}: Нет данных в таблице data_1d")
                return df
            else:
                print(f"    ✅ [ML_DATA] {symbol}: Найдено {len(df)} записей")
            
            # Конвертируем дату
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
            
            # Добавляем технические индикаторы
            df = self._add_technical_indicators(df)
            
            print(f"    ✅ [ML_DATA] {symbol}: Данные обработаны, итого {len(df)} записей")
            return df
            
        except Exception as e:
            print(f"    ❌ [ML_DATA] {symbol}: Ошибка получения данных - {e}")
            logger.error(f"Error getting stock data for {symbol}: {e}")
            return pd.DataFrame()
        finally:
            conn.close()
    
    def _get_news_data_from_db(self, symbol: str, timeframe: str = '1d') -> pd.DataFrame:
        """Получить новости из БД."""
        import sqlite3
        from pathlib import Path
        
        db_path = "stock_data.db"
        if not Path(db_path).exists():
            return pd.DataFrame()
        
        conn = sqlite3.connect(db_path)
        try:
            # Определяем период для новостей
            days_back = 7 if timeframe == '1d' else 1
            
            # Ищем таблицу с новостями
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND (name LIKE '%news%' OR name LIKE '%article%')")
            news_tables = cursor.fetchall()
            
            if not news_tables:
                return pd.DataFrame()
            
            # Используем первую найденную таблицу
            news_table = news_tables[0][0]
            
            # Простой запрос для новостей
            query = f"""
                SELECT title, content, date
                FROM {news_table}
                WHERE date >= date('now', '-{days_back} days')
                ORDER BY date DESC
                LIMIT 100
            """
            
            df = pd.read_sql_query(query, conn)
            return df
            
        except Exception as e:
            logger.error(f"Error getting news data: {e}")
            return pd.DataFrame()
        finally:
            conn.close()
    
    def _add_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Добавить технические индикаторы."""
        try:
            # Простые скользящие средние
            df['sma_20'] = df['close'].rolling(window=20).mean()
            df['sma_50'] = df['close'].rolling(window=50).mean()
            
            # EMA
            df['ema_12'] = df['close'].ewm(span=12).mean()
            df['ema_26'] = df['close'].ewm(span=26).mean()
            
            # RSI
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['rsi'] = 100 - (100 / (1 + rs))
            
            # MACD
            df['macd'] = df['ema_12'] - df['ema_26']
            
            # Bollinger Bands
            bb_period = 20
            bb_std = 2
            df['bb_middle'] = df['close'].rolling(window=bb_period).mean()
            bb_std_val = df['close'].rolling(window=bb_period).std()
            df['bb_upper'] = df['bb_middle'] + (bb_std_val * bb_std)
            df['bb_lower'] = df['bb_middle'] - (bb_std_val * bb_std)
            
            # Заполняем NaN значения
            df = df.ffill().fillna(0)
            
            return df
            
        except Exception as e:
            logger.error(f"Error adding technical indicators: {e}")
            return df
    
    def _record_training_history(self, symbol: str, model_type: str, timeframe: str, 
                               training_metrics: Dict[str, Any], status: str, 
                               error_message: Optional[str] = None) -> None:
        """Записать историю обучения в БД."""
        import sqlite3
        
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                INSERT INTO ml_training_history
                (symbol, model_type, timeframe, training_start, training_end,
                 duration_seconds, data_points, epochs_trained, final_accuracy,
                 final_loss, hyperparameters, training_status, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                symbol, model_type, timeframe,
                training_metrics.get('training_start', datetime.now().isoformat()),
                training_metrics.get('training_end', datetime.now().isoformat()),
                training_metrics.get('training_duration', 0.0),
                training_metrics.get('data_points', 0),
                training_metrics.get('epochs_trained', 0),
                training_metrics.get('accuracy', 0.0),
                training_metrics.get('mse', 0.0),
                '{}',  # hyperparameters
                status,
                error_message
            ))
            conn.commit()
        finally:
            conn.close()


# Глобальный экземпляр для использования в приложении
ml_model_manager = MLModelManager()
