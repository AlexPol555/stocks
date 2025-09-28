"""
Гибридная система хранения ML моделей и предсказаний.
Поддерживает файловое хранение + БД метаданные + кэширование.
Готова для масштабирования на разные таймфреймы.
"""

import os
import json
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple, Union
from pathlib import Path
import pandas as pd

try:
    import joblib
    JOBLIB_AVAILABLE = True
except ImportError:
    JOBLIB_AVAILABLE = False
    logging.warning("joblib not available, using pickle fallback")

try:
    import pickle
    PICKLE_AVAILABLE = True
except ImportError:
    PICKLE_AVAILABLE = False
    logging.warning("pickle not available")

from core.database import get_connection

logger = logging.getLogger(__name__)


class MLModelStorage:
    """Гибридная система хранения ML моделей."""
    
    def __init__(self, db_path: str = "stock_data.db", cache_dir: str = "models/"):
        self.db_path = db_path
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
        # Кэш в памяти для быстрого доступа
        self.memory_cache = {}
        self.cache_max_size = 50  # Максимум моделей в памяти
        
        # Настройки по умолчанию для разных таймфреймов
        self.timeframe_configs = {
            '1d': {
                'model_expiry_hours': 24,      # Модель актуальна 24 часа
                'prediction_cache_minutes': 60, # Предсказания кэшируются 60 минут
                'sequence_length': 60,         # 60 дней истории
                'retrain_frequency_hours': 6   # Переобучение каждые 6 часов
            },
            '1h': {
                'model_expiry_hours': 6,       # Модель актуальна 6 часов
                'prediction_cache_minutes': 30, # Предсказания кэшируются 30 минут
                'sequence_length': 168,        # 168 часов (1 неделя) истории
                'retrain_frequency_hours': 2   # Переобучение каждые 2 часа
            },
            '1m': {
                'model_expiry_hours': 2,       # Модель актуальна 2 часа
                'prediction_cache_minutes': 10, # Предсказания кэшируются 10 минут
                'sequence_length': 1440,       # 1440 минут (1 день) истории
                'retrain_frequency_hours': 1   # Переобучение каждый час
            },
            '1s': {
                'model_expiry_hours': 1,       # Модель актуальна 1 час
                'prediction_cache_minutes': 5,  # Предсказания кэшируются 5 минут
                'sequence_length': 3600,       # 3600 секунд (1 час) истории
                'retrain_frequency_hours': 0.5 # Переобучение каждые 30 минут
            }
        }
    
    def get_model(self, symbol: str, model_type: str = 'lstm', timeframe: str = '1d') -> Tuple[Optional[Any], Optional[Dict[str, Any]]]:
        """
        Получить модель и метаданные.
        
        Args:
            symbol: Символ акции
            model_type: Тип модели ('lstm', 'gru', 'ensemble', 'sentiment')
            timeframe: Таймфрейм ('1d', '1h', '1m', '1s')
            
        Returns:
            Tuple[модель, метаданные] или (None, None) если не найдено
        """
        cache_key = f"{symbol}_{model_type}_{timeframe}"
        
        # 1. Проверяем кэш в памяти
        if cache_key in self.memory_cache:
            model, metadata = self.memory_cache[cache_key]
            if not self._is_model_expired(metadata, timeframe):
                logger.debug(f"Model {cache_key} loaded from memory cache")
                return model, metadata
            else:
                # Удаляем устаревшую модель из кэша
                del self.memory_cache[cache_key]
        
        # 2. Загружаем из файла
        model_path = self.cache_dir / f"{symbol}_{model_type}_{timeframe}.pkl"
        if model_path.exists():
            try:
                model = self._load_model_from_file(model_path)
                metadata = self._get_model_metadata(symbol, model_type, timeframe)
                
                if metadata and not self._is_model_expired(metadata, timeframe):
                    # Сохраняем в кэш памяти
                    self._add_to_memory_cache(cache_key, model, metadata)
                    logger.debug(f"Model {cache_key} loaded from file")
                    return model, metadata
                else:
                    # Модель устарела, удаляем файл
                    model_path.unlink()
                    logger.info(f"Expired model {cache_key} removed from file system")
            except Exception as e:
                logger.error(f"Error loading model {cache_key} from file: {e}")
        
        # 3. Модель не найдена или устарела
        logger.debug(f"Model {cache_key} not found or expired")
        return None, None
    
    def save_model(self, symbol: str, model: Any, model_type: str = 'lstm', 
                   timeframe: str = '1d', training_metrics: Optional[Dict[str, Any]] = None,
                   hyperparameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Сохранить модель.
        
        Args:
            symbol: Символ акции
            model: Обученная модель
            model_type: Тип модели
            timeframe: Таймфрейм
            training_metrics: Метрики обучения
            hyperparameters: Гиперпараметры
            
        Returns:
            Метаданные сохраненной модели
        """
        model_path = self.cache_dir / f"{symbol}_{model_type}_{timeframe}.pkl"
        
        # 1. Сохраняем модель в файл
        try:
            self._save_model_to_file(model, model_path)
            logger.info(f"Model {symbol}_{model_type}_{timeframe} saved to file")
        except Exception as e:
            logger.error(f"Error saving model to file: {e}")
            raise
        
        # 2. Подготавливаем метаданные
        metadata = {
            'symbol': symbol,
            'model_type': model_type,
            'timeframe': timeframe,
            'model_path': str(model_path),
            'training_date': datetime.now().isoformat(),
            'accuracy': training_metrics.get('accuracy', 0.0) if training_metrics else 0.0,
            'mse': training_metrics.get('mse', 0.0) if training_metrics else 0.0,
            'mae': training_metrics.get('mae', 0.0) if training_metrics else 0.0,
            'rmse': training_metrics.get('rmse', 0.0) if training_metrics else 0.0,
            'data_points': training_metrics.get('data_points', 0) if training_metrics else 0,
            'epochs_trained': training_metrics.get('epochs_trained', 0) if training_metrics else 0,
            'training_duration': training_metrics.get('training_duration', 0.0) if training_metrics else 0.0,
            'sequence_length': training_metrics.get('sequence_length', 60) if training_metrics else 60,
            'hidden_size': training_metrics.get('hidden_size', 50) if training_metrics else 50,
            'features_used': json.dumps(training_metrics.get('features_used', [])) if training_metrics else '[]',
            'hyperparameters': json.dumps(hyperparameters) if hyperparameters else '{}',
            'model_version': '1.0',
            'is_active': True
        }
        
        # 3. Сохраняем метаданные в БД
        try:
            self._save_model_metadata(metadata)
            logger.info(f"Model metadata for {symbol}_{model_type}_{timeframe} saved to DB")
        except Exception as e:
            logger.error(f"Error saving model metadata to DB: {e}")
            # Не прерываем выполнение, файл уже сохранен
        
        # 4. Сохраняем в кэш памяти
        cache_key = f"{symbol}_{model_type}_{timeframe}"
        self._add_to_memory_cache(cache_key, model, metadata)
        
        return metadata
    
    def get_prediction(self, symbol: str, prediction_type: str, timeframe: str = '1d') -> Optional[Dict[str, Any]]:
        """Получить предсказание из кэша."""
        conn = get_connection(self.db_path)
        try:
            cursor = conn.execute("""
                SELECT prediction_value, confidence, input_data, prediction_date
                FROM ml_predictions_cache
                WHERE symbol = ? AND prediction_type = ? AND timeframe = ?
                AND expires_at > ?
                ORDER BY prediction_date DESC LIMIT 1
            """, (symbol, prediction_type, timeframe, datetime.now().isoformat()))
            
            result = cursor.fetchone()
            if result:
                return {
                    'prediction': result[0],
                    'confidence': result[1],
                    'input_data': json.loads(result[2]) if result[2] else {},
                    'date': result[3]
                }
            return None
        finally:
            conn.close()
    
    def save_prediction(self, symbol: str, prediction_type: str, prediction: float, 
                       confidence: float, timeframe: str = '1d', 
                       input_data: Optional[Dict[str, Any]] = None) -> None:
        """Сохранить предсказание в кэш."""
        config = self.timeframe_configs.get(timeframe, self.timeframe_configs['1d'])
        expires_at = datetime.now() + timedelta(minutes=config['prediction_cache_minutes'])
        
        conn = get_connection(self.db_path)
        try:
            conn.execute("""
                INSERT OR REPLACE INTO ml_predictions_cache
                (symbol, prediction_type, timeframe, prediction_value, confidence, 
                 input_data, prediction_date, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (symbol, prediction_type, timeframe, prediction, confidence,
                  json.dumps(input_data) if input_data else '{}',
                  datetime.now().isoformat(), expires_at.isoformat()))
            conn.commit()
        finally:
            conn.close()
    
    def get_active_models(self, timeframe: Optional[str] = None) -> pd.DataFrame:
        """Получить список активных моделей."""
        conn = get_connection(self.db_path)
        try:
            if timeframe:
                query = """
                    SELECT symbol, model_type, timeframe, accuracy, training_date, 
                           data_points, epochs_trained, is_active
                    FROM ml_models 
                    WHERE timeframe = ? AND is_active = 1
                    ORDER BY training_date DESC
                """
                df = pd.read_sql_query(query, conn, params=(timeframe,))
            else:
                query = """
                    SELECT symbol, model_type, timeframe, accuracy, training_date, 
                           data_points, epochs_trained, is_active
                    FROM ml_models 
                    WHERE is_active = 1
                    ORDER BY timeframe, training_date DESC
                """
                df = pd.read_sql_query(query, conn)
            
            return df
        finally:
            conn.close()
    
    def get_training_history(self, symbol: Optional[str] = None, 
                           timeframe: Optional[str] = None, 
                           limit: int = 100) -> pd.DataFrame:
        """Получить историю обучения."""
        conn = get_connection(self.db_path)
        try:
            conditions = []
            params = []
            
            if symbol:
                conditions.append("symbol = ?")
                params.append(symbol)
            
            if timeframe:
                conditions.append("timeframe = ?")
                params.append(timeframe)
            
            where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
            params.append(limit)
            
            query = f"""
                SELECT symbol, model_type, timeframe, training_start, training_end,
                       duration_seconds, data_points, epochs_trained, final_accuracy,
                       final_loss, training_status, error_message
                FROM ml_training_history 
                {where_clause}
                ORDER BY training_start DESC
                LIMIT ?
            """
            
            df = pd.read_sql_query(query, conn, params=params)
            return df
        finally:
            conn.close()
    
    def cleanup_expired_models(self) -> int:
        """Очистить устаревшие модели."""
        cleaned_count = 0
        
        # Очистка файлов
        for model_file in self.cache_dir.glob("*.pkl"):
            try:
                # Извлекаем информацию из имени файла
                parts = model_file.stem.split('_')
                if len(parts) >= 3:
                    symbol, model_type, timeframe = parts[0], parts[1], '_'.join(parts[2:])
                    
                    # Проверяем метаданные в БД
                    metadata = self._get_model_metadata(symbol, model_type, timeframe)
                    if metadata and self._is_model_expired(metadata, timeframe):
                        model_file.unlink()
                        cleaned_count += 1
                        logger.info(f"Expired model file removed: {model_file}")
            except Exception as e:
                logger.error(f"Error cleaning up model file {model_file}: {e}")
        
        # Очистка кэша в памяти
        expired_keys = []
        for key, (model, metadata) in self.memory_cache.items():
            parts = key.split('_')
            if len(parts) >= 3:
                timeframe = '_'.join(parts[2:])
                if self._is_model_expired(metadata, timeframe):
                    expired_keys.append(key)
        
        for key in expired_keys:
            del self.memory_cache[key]
            cleaned_count += 1
        
        # Очистка кэша предсказаний
        conn = get_connection(self.db_path)
        try:
            cursor = conn.execute("DELETE FROM ml_predictions_cache WHERE expires_at <= ?", 
                                (datetime.now().isoformat(),))
            cleaned_count += cursor.rowcount
            conn.commit()
        finally:
            conn.close()
        
        logger.info(f"Cleaned up {cleaned_count} expired items")
        return cleaned_count
    
    def _load_model_from_file(self, model_path: Path) -> Any:
        """Загрузить модель из файла."""
        if JOBLIB_AVAILABLE:
            return joblib.load(model_path)
        elif PICKLE_AVAILABLE:
            with open(model_path, 'rb') as f:
                return pickle.load(f)
        else:
            raise ImportError("Neither joblib nor pickle available for model loading")
    
    def _save_model_to_file(self, model: Any, model_path: Path) -> None:
        """Сохранить модель в файл."""
        if JOBLIB_AVAILABLE:
            joblib.dump(model, model_path)
        elif PICKLE_AVAILABLE:
            with open(model_path, 'wb') as f:
                pickle.dump(model, f)
        else:
            raise ImportError("Neither joblib nor pickle available for model saving")
    
    def _get_model_metadata(self, symbol: str, model_type: str, timeframe: str) -> Optional[Dict[str, Any]]:
        """Получить метаданные модели из БД."""
        conn = get_connection(self.db_path)
        try:
            cursor = conn.execute("""
                SELECT * FROM ml_models 
                WHERE symbol = ? AND model_type = ? AND timeframe = ?
                ORDER BY training_date DESC LIMIT 1
            """, (symbol, model_type, timeframe))
            
            result = cursor.fetchone()
            if result:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, result))
            return None
        finally:
            conn.close()
    
    def _save_model_metadata(self, metadata: Dict[str, Any]) -> None:
        """Сохранить метаданные модели в БД."""
        conn = get_connection(self.db_path)
        try:
            conn.execute("""
                INSERT OR REPLACE INTO ml_models 
                (symbol, model_type, timeframe, model_path, accuracy, mse, mae, rmse,
                 training_date, data_points, sequence_length, hidden_size, epochs_trained,
                 training_duration, features_used, hyperparameters, model_version, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                metadata['symbol'], metadata['model_type'], metadata['timeframe'],
                metadata['model_path'], metadata['accuracy'], metadata['mse'], 
                metadata['mae'], metadata['rmse'], metadata['training_date'],
                metadata['data_points'], metadata['sequence_length'], 
                metadata['hidden_size'], metadata['epochs_trained'],
                metadata['training_duration'], metadata['features_used'],
                metadata['hyperparameters'], metadata['model_version'], 
                metadata['is_active']
            ))
            conn.commit()
        finally:
            conn.close()
    
    def _is_model_expired(self, metadata: Dict[str, Any], timeframe: str) -> bool:
        """Проверить, устарела ли модель."""
        if not metadata or 'training_date' not in metadata:
            return True
        
        config = self.timeframe_configs.get(timeframe, self.timeframe_configs['1d'])
        max_age_hours = config['model_expiry_hours']
        
        try:
            training_time = datetime.fromisoformat(metadata['training_date'])
            age = datetime.now() - training_time
            return age.total_seconds() > (max_age_hours * 3600)
        except (ValueError, TypeError):
            return True
    
    def _add_to_memory_cache(self, key: str, model: Any, metadata: Dict[str, Any]) -> None:
        """Добавить модель в кэш памяти."""
        # Если кэш переполнен, удаляем самую старую модель
        if len(self.memory_cache) >= self.cache_max_size:
            oldest_key = min(self.memory_cache.keys(), 
                           key=lambda k: self.memory_cache[k][1].get('training_date', ''))
            del self.memory_cache[oldest_key]
        
        self.memory_cache[key] = (model, metadata)


# Глобальный экземпляр для использования в приложении
ml_storage = MLModelStorage()
