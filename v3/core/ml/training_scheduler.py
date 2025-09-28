"""
Планировщик обучения ML моделей.
Поддерживает автоматическое обучение по расписанию и инкрементальное обучение.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import time

from .model_manager import ml_model_manager
from .storage import ml_storage
from core.database import get_connection

logger = logging.getLogger(__name__)


class MLTrainingScheduler:
    """Планировщик обучения ML моделей."""
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.is_running = False
        self.training_tasks = {}
        
        # Настройки расписания для разных таймфреймов
        self.schedule_configs = {
            '1d': {
                'retrain_interval_hours': 6,      # Переобучение каждые 6 часов
                'batch_size': 5,                  # Обучаем по 5 символов за раз
                'priority': 1,                    # Высокий приоритет
                'enabled': True
            },
            '1h': {
                'retrain_interval_hours': 2,      # Переобучение каждые 2 часа
                'batch_size': 3,                  # Обучаем по 3 символа за раз
                'priority': 2,                    # Средний приоритет
                'enabled': False                  # Пока отключено
            },
            '1m': {
                'retrain_interval_hours': 1,      # Переобучение каждый час
                'batch_size': 2,                  # Обучаем по 2 символа за раз
                'priority': 3,                    # Низкий приоритет
                'enabled': False                  # Пока отключено
            },
            '1s': {
                'retrain_interval_hours': 0.5,    # Переобучение каждые 30 минут
                'batch_size': 1,                  # Обучаем по 1 символу за раз
                'priority': 4,                    # Самый низкий приоритет
                'enabled': False                  # Пока отключено
            }
        }
        
        # Статистика обучения
        self.training_stats = {
            'total_trainings': 0,
            'successful_trainings': 0,
            'failed_trainings': 0,
            'last_training': None,
            'average_training_time': 0.0
        }
    
    def start_scheduler(self) -> None:
        """Запустить планировщик."""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return
        
        self.is_running = True
        logger.info("ML Training Scheduler started")
        
        # Запускаем асинхронные задачи для каждого таймфрейма
        for timeframe, config in self.schedule_configs.items():
            if config['enabled']:
                asyncio.create_task(self._schedule_timeframe_training(timeframe, config))
    
    def stop_scheduler(self) -> None:
        """Остановить планировщик."""
        self.is_running = False
        self.executor.shutdown(wait=True)
        logger.info("ML Training Scheduler stopped")
    
    async def _schedule_timeframe_training(self, timeframe: str, config: Dict[str, Any]) -> None:
        """Планировать обучение для конкретного таймфрейма."""
        while self.is_running:
            try:
                # Получаем символы для обучения
                symbols_to_train = await self._get_symbols_for_training(timeframe)
                
                if symbols_to_train:
                    logger.info(f"Training {len(symbols_to_train)} models for timeframe {timeframe}")
                    
                    # Обучаем модели батчами
                    await self._train_models_batch(symbols_to_train, timeframe, config['batch_size'])
                
                # Ждем до следующего цикла
                await asyncio.sleep(config['retrain_interval_hours'] * 3600)
                
            except Exception as e:
                logger.error(f"Error in timeframe {timeframe} training scheduler: {e}")
                await asyncio.sleep(300)  # Ждем 5 минут при ошибке
    
    async def _get_symbols_for_training(self, timeframe: str) -> List[str]:
        """Получить символы, которые нужно обучить."""
        try:
            # Получаем все символы из БД
            conn = get_connection()
            try:
                cursor = conn.execute("SELECT DISTINCT contract_code FROM companies LIMIT 50")
                all_symbols = [row[0] for row in cursor.fetchall()]
            finally:
                conn.close()
            
            if not all_symbols:
                return []
            
            # Проверяем, какие модели нужно обучить
            symbols_to_train = []
            
            for symbol in all_symbols:
                # Проверяем, есть ли актуальная модель
                model, metadata = ml_storage.get_model(symbol, 'lstm', timeframe)
                
                if model is None:
                    # Модель не существует
                    symbols_to_train.append(symbol)
                elif self._should_retrain_model(metadata, timeframe):
                    # Модель устарела
                    symbols_to_train.append(symbol)
            
            # Ограничиваем количество символов для обучения
            max_symbols = 20 if timeframe == '1d' else 10
            return symbols_to_train[:max_symbols]
            
        except Exception as e:
            logger.error(f"Error getting symbols for training: {e}")
            return []
    
    def _should_retrain_model(self, metadata: Dict[str, Any], timeframe: str) -> bool:
        """Проверить, нужно ли переобучать модель."""
        if not metadata or 'training_date' not in metadata:
            return True
        
        config = self.schedule_configs.get(timeframe, self.schedule_configs['1d'])
        retrain_interval_hours = config['retrain_interval_hours']
        
        try:
            training_time = datetime.fromisoformat(metadata['training_date'])
            age_hours = (datetime.now() - training_time).total_seconds() / 3600
            return age_hours >= retrain_interval_hours
        except (ValueError, TypeError):
            return True
    
    async def _train_models_batch(self, symbols: List[str], timeframe: str, batch_size: int) -> None:
        """Обучить модели батчами."""
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i + batch_size]
            
            # Обучаем модели параллельно
            futures = []
            for symbol in batch:
                future = self.executor.submit(
                    self._train_single_model, symbol, 'lstm', timeframe
                )
                futures.append((symbol, future))
            
            # Ждем завершения батча
            for symbol, future in futures:
                try:
                    start_time = time.time()
                    result = future.result(timeout=300)  # 5 минут таймаут
                    training_time = time.time() - start_time
                    
                    if result['success']:
                        self.training_stats['successful_trainings'] += 1
                        logger.info(f"Successfully trained {symbol} ({timeframe}) in {training_time:.1f}s")
                    else:
                        self.training_stats['failed_trainings'] += 1
                        logger.error(f"Failed to train {symbol} ({timeframe}): {result.get('error', 'Unknown error')}")
                    
                    self.training_stats['total_trainings'] += 1
                    self.training_stats['last_training'] = datetime.now().isoformat()
                    
                    # Обновляем среднее время обучения
                    total_time = self.training_stats['average_training_time'] * (self.training_stats['total_trainings'] - 1)
                    self.training_stats['average_training_time'] = (total_time + training_time) / self.training_stats['total_trainings']
                    
                except Exception as e:
                    self.training_stats['failed_trainings'] += 1
                    logger.error(f"Error training {symbol} ({timeframe}): {e}")
            
            # Небольшая пауза между батчами
            await asyncio.sleep(10)
    
    def _train_single_model(self, symbol: str, model_type: str, timeframe: str) -> Dict[str, Any]:
        """Обучить одну модель."""
        try:
            model, metadata = ml_model_manager.get_or_train_model(
                symbol, model_type, timeframe, force_retrain=True
            )
            
            if model is not None:
                return {
                    'success': True,
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'metadata': metadata
                }
            else:
                return {
                    'success': False,
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'error': 'Model training returned None'
                }
                
        except Exception as e:
            return {
                'success': False,
                'symbol': symbol,
                'timeframe': timeframe,
                'error': str(e)
            }
    
    def train_model_now(self, symbol: str, model_type: str = 'lstm', 
                       timeframe: str = '1d') -> Dict[str, Any]:
        """Обучить модель немедленно."""
        try:
            logger.info(f"Starting immediate training for {symbol} ({model_type}, {timeframe})")
            
            model, metadata = ml_model_manager.get_or_train_model(
                symbol, model_type, timeframe, force_retrain=True
            )
            
            if model is not None:
                return {
                    'success': True,
                    'symbol': symbol,
                    'model_type': model_type,
                    'timeframe': timeframe,
                    'metadata': metadata
                }
            else:
                return {
                    'success': False,
                    'symbol': symbol,
                    'error': 'Model training returned None'
                }
                
        except Exception as e:
            logger.error(f"Error in immediate training for {symbol}: {e}")
            return {
                'success': False,
                'symbol': symbol,
                'error': str(e)
            }
    
    def train_all_models_now(self, timeframe: str = '1d', 
                           model_type: str = 'lstm') -> Dict[str, Any]:
        """Обучить все модели немедленно."""
        try:
            # Получаем все символы
            conn = get_connection()
            try:
                cursor = conn.execute("SELECT DISTINCT contract_code FROM companies LIMIT 100")
                all_symbols = [row[0] for row in cursor.fetchall()]
            finally:
                conn.close()
            
            if not all_symbols:
                return {
                    'success': False,
                    'error': 'No symbols found in database'
                }
            
            logger.info(f"Starting batch training for {len(all_symbols)} symbols ({timeframe})")
            
            # Обучаем все модели параллельно
            futures = []
            for symbol in all_symbols:
                future = self.executor.submit(
                    self._train_single_model, symbol, model_type, timeframe
                )
                futures.append((symbol, future))
            
            # Собираем результаты
            results = {
                'successful': [],
                'failed': [],
                'total': len(all_symbols)
            }
            
            for symbol, future in futures:
                try:
                    result = future.result(timeout=600)  # 10 минут таймаут
                    if result['success']:
                        results['successful'].append(symbol)
                    else:
                        results['failed'].append({
                            'symbol': symbol,
                            'error': result.get('error', 'Unknown error')
                        })
                except Exception as e:
                    results['failed'].append({
                        'symbol': symbol,
                        'error': str(e)
                    })
            
            logger.info(f"Batch training completed: {len(results['successful'])} successful, {len(results['failed'])} failed")
            
            return {
                'success': True,
                'results': results
            }
            
        except Exception as e:
            logger.error(f"Error in batch training: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_training_status(self) -> Dict[str, Any]:
        """Получить статус обучения."""
        return {
            'is_running': self.is_running,
            'stats': self.training_stats,
            'schedule_configs': self.schedule_configs,
            'active_tasks': len(self.training_tasks)
        }
    
    def get_training_history(self, symbol: Optional[str] = None, 
                           timeframe: Optional[str] = None, 
                           limit: int = 50) -> pd.DataFrame:
        """Получить историю обучения."""
        return ml_storage.get_training_history(symbol, timeframe, limit)
    
    def cleanup_expired_models(self) -> int:
        """Очистить устаревшие модели."""
        return ml_storage.cleanup_expired_models()
    
    def update_schedule_config(self, timeframe: str, config: Dict[str, Any]) -> None:
        """Обновить конфигурацию расписания."""
        if timeframe in self.schedule_configs:
            self.schedule_configs[timeframe].update(config)
            logger.info(f"Updated schedule config for {timeframe}: {config}")
        else:
            logger.warning(f"Unknown timeframe: {timeframe}")
    
    def enable_timeframe(self, timeframe: str) -> None:
        """Включить обучение для таймфрейма."""
        if timeframe in self.schedule_configs:
            self.schedule_configs[timeframe]['enabled'] = True
            logger.info(f"Enabled training for timeframe {timeframe}")
        else:
            logger.warning(f"Unknown timeframe: {timeframe}")
    
    def disable_timeframe(self, timeframe: str) -> None:
        """Отключить обучение для таймфрейма."""
        if timeframe in self.schedule_configs:
            self.schedule_configs[timeframe]['enabled'] = False
            logger.info(f"Disabled training for timeframe {timeframe}")
        else:
            logger.warning(f"Unknown timeframe: {timeframe}")


# Глобальный экземпляр планировщика
ml_training_scheduler = MLTrainingScheduler()
