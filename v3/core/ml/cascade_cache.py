#!/usr/bin/env python3
"""
Cascade ML Cache Manager.

Специализированный менеджер кэша для ML результатов каскадного анализа.
Использует базу данных для персистентного хранения кэша с проверкой актуальности.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import sqlite3
from pathlib import Path

from core.database import get_connection
from core.settings import get_settings

logger = logging.getLogger(__name__)


class CascadeMLCacheManager:
    """Менеджер кэша для ML результатов каскадного анализа."""
    
    def __init__(self, db_path: Optional[str] = None):
        """Инициализация менеджера кэша.
        
        Args:
            db_path: Путь к базе данных (если None, используется настройка по умолчанию)
        """
        self.settings = get_settings()
        self.db_path = db_path or str(self.settings.database_path)
        self.cache_duration = timedelta(hours=6)  # Кэш на 6 часов
        self.cache_key_prefix = "cascade_ml_results"
        
    def _get_connection(self) -> sqlite3.Connection:
        """Получить соединение с базой данных."""
        return get_connection(self.db_path)
    
    def _generate_cache_key(self, symbols: List[str], min_volume: float, min_avg_volume: float) -> str:
        """Генерировать ключ кэша на основе параметров.
        
        Args:
            symbols: Список символов
            min_volume: Минимальный объем
            min_avg_volume: Минимальный средний объем
            
        Returns:
            Уникальный ключ кэша
        """
        # Сортируем символы для консистентности
        sorted_symbols = sorted(symbols)
        symbols_hash = hash(tuple(sorted_symbols))
        
        return f"{self.cache_key_prefix}_{symbols_hash}_{min_volume}_{min_avg_volume}"
    
    def save_ml_results(self, symbols: List[str], ml_results: Dict[str, Any], 
                       min_volume: float, min_avg_volume: float,
                       expires_in_hours: int = 6) -> bool:
        """Сохранить ML результаты в кэш.
        
        Args:
            symbols: Список проанализированных символов
            ml_results: Результаты ML анализа
            min_volume: Минимальный объем фильтрации
            min_avg_volume: Минимальный средний объем фильтрации
            expires_in_hours: Время жизни кэша в часах
            
        Returns:
            True если успешно сохранено
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Генерируем ключ кэша
            cache_key = self._generate_cache_key(symbols, min_volume, min_avg_volume)
            
            # Подготавливаем данные для сохранения
            cache_data = {
                'symbols': symbols,
                'ml_results': ml_results,
                'min_volume': min_volume,
                'min_avg_volume': min_avg_volume,
                'created_at': datetime.now().isoformat(),
                'symbols_count': len(symbols),
                'results_count': len(ml_results)
            }
            
            # Рассчитываем время истечения
            expires_at = (datetime.now() + timedelta(hours=expires_in_hours)).isoformat()
            
            # Сериализуем данные
            cache_data_json = json.dumps(cache_data, default=str)
            
            # Сохраняем в БД
            cursor.execute("""
                INSERT OR REPLACE INTO ml_cache (cache_key, cache_data, expires_at, created_at)
                VALUES (?, ?, ?, ?)
            """, (cache_key, cache_data_json, expires_at, datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            
            logger.info(f"💾 [CACHE] Сохранены ML результаты в БД: {len(symbols)} символов, ключ: {cache_key}")
            return True
            
        except Exception as e:
            logger.error(f"❌ [CACHE] Ошибка сохранения ML результатов: {e}")
            return False
    
    def get_ml_results(self, symbols: List[str], min_volume: float, min_avg_volume: float) -> Optional[Dict[str, Any]]:
        """Получить ML результаты из кэша.
        
        Args:
            symbols: Список символов
            min_volume: Минимальный объем фильтрации
            min_avg_volume: Минимальный средний объем фильтрации
            
        Returns:
            Кэшированные данные или None если не найдены/устарели
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Генерируем ключ кэша
            cache_key = self._generate_cache_key(symbols, min_volume, min_avg_volume)
            
            # Ищем в БД
            cursor.execute("""
                SELECT cache_data, expires_at, created_at FROM ml_cache 
                WHERE cache_key = ? AND expires_at > ?
            """, (cache_key, datetime.now().isoformat()))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                cache_data_json, expires_at, created_at = row
                cache_data = json.loads(cache_data_json)
                
                logger.info(f"✅ [CACHE] Найдены кэшированные ML результаты: {cache_data['symbols_count']} символов")
                logger.info(f"📅 [CACHE] Создано: {created_at}, истекает: {expires_at}")
                
                return cache_data
            else:
                logger.debug(f"🔍 [CACHE] Кэш не найден или устарел для ключа: {cache_key}")
                return None
                
        except Exception as e:
            logger.error(f"❌ [CACHE] Ошибка получения ML результатов: {e}")
            return None
    
    def is_cache_valid(self, symbols: List[str], min_volume: float, min_avg_volume: float) -> bool:
        """Проверить, валиден ли кэш.
        
        Args:
            symbols: Список символов
            min_volume: Минимальный объем фильтрации
            min_avg_volume: Минимальный средний объем фильтрации
            
        Returns:
            True если кэш валиден и не устарел
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cache_key = self._generate_cache_key(symbols, min_volume, min_avg_volume)
            
            cursor.execute("""
                SELECT COUNT(*) FROM ml_cache 
                WHERE cache_key = ? AND expires_at > ?
            """, (cache_key, datetime.now().isoformat()))
            
            count = cursor.fetchone()[0]
            conn.close()
            
            is_valid = count > 0
            logger.debug(f"🔍 [CACHE] Валидность кэша для {len(symbols)} символов: {is_valid}")
            return is_valid
            
        except Exception as e:
            logger.error(f"❌ [CACHE] Ошибка проверки валидности кэша: {e}")
            return False
    
    def clear_cache(self, symbols: Optional[List[str]] = None, 
                   min_volume: Optional[float] = None, 
                   min_avg_volume: Optional[float] = None) -> int:
        """Очистить кэш.
        
        Args:
            symbols: Список символов (если None, очищает весь кэш)
            min_volume: Минимальный объем (если None, очищает весь кэш)
            min_avg_volume: Минимальный средний объем (если None, очищает весь кэш)
            
        Returns:
            Количество удаленных записей
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            if symbols is not None and min_volume is not None and min_avg_volume is not None:
                # Очищаем конкретный кэш
                cache_key = self._generate_cache_key(symbols, min_volume, min_avg_volume)
                cursor.execute("DELETE FROM ml_cache WHERE cache_key = ?", (cache_key,))
                logger.info(f"🗑️ [CACHE] Очищен кэш для ключа: {cache_key}")
            else:
                # Очищаем весь кэш каскадного анализа
                cursor.execute("DELETE FROM ml_cache WHERE cache_key LIKE ?", (f"{self.cache_key_prefix}%",))
                logger.info("🗑️ [CACHE] Очищен весь кэш каскадного анализа")
            
            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()
            
            logger.info(f"✅ [CACHE] Удалено {deleted_count} записей кэша")
            return deleted_count
            
        except Exception as e:
            logger.error(f"❌ [CACHE] Ошибка очистки кэша: {e}")
            return 0
    
    def clear_expired_cache(self) -> int:
        """Очистить устаревший кэш.
        
        Returns:
            Количество удаленных записей
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM ml_cache WHERE expires_at < ?", (datetime.now().isoformat(),))
            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()
            
            logger.info(f"🧹 [CACHE] Очищено {deleted_count} устаревших записей кэша")
            return deleted_count
            
        except Exception as e:
            logger.error(f"❌ [CACHE] Ошибка очистки устаревшего кэша: {e}")
            return 0
    
    def get_cache_status(self) -> Dict[str, Any]:
        """Получить статус кэша.
        
        Returns:
            Словарь со статусом кэша
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Общая статистика
            cursor.execute("SELECT COUNT(*) FROM ml_cache WHERE cache_key LIKE ?", (f"{self.cache_key_prefix}%",))
            total_entries = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM ml_cache WHERE cache_key LIKE ? AND expires_at > ?", 
                         (f"{self.cache_key_prefix}%", datetime.now().isoformat()))
            valid_entries = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM ml_cache WHERE cache_key LIKE ? AND expires_at <= ?", 
                         (f"{self.cache_key_prefix}%", datetime.now().isoformat()))
            expired_entries = cursor.fetchone()[0]
            
            # Последняя запись
            cursor.execute("""
                SELECT cache_key, created_at, expires_at FROM ml_cache 
                WHERE cache_key LIKE ? 
                ORDER BY created_at DESC LIMIT 1
            """, (f"{self.cache_key_prefix}%",))
            
            last_entry = cursor.fetchone()
            conn.close()
            
            status = {
                'total_entries': total_entries,
                'valid_entries': valid_entries,
                'expired_entries': expired_entries,
                'cache_duration_hours': self.cache_duration.total_seconds() / 3600,
                'last_entry': {
                    'key': last_entry[0] if last_entry else None,
                    'created_at': last_entry[1] if last_entry else None,
                    'expires_at': last_entry[2] if last_entry else None
                } if last_entry else None
            }
            
            logger.info(f"📊 [CACHE] Статус кэша: {valid_entries}/{total_entries} валидных записей")
            return status
            
        except Exception as e:
            logger.error(f"❌ [CACHE] Ошибка получения статуса кэша: {e}")
            return {}
    
    def inspect_cache(self) -> Dict[str, Any]:
        """Инспектировать содержимое кэша.
        
        Returns:
            Детальная информация о кэше
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Получаем все записи кэша
            cursor.execute("""
                SELECT cache_key, created_at, expires_at, cache_data FROM ml_cache 
                WHERE cache_key LIKE ? 
                ORDER BY created_at DESC
            """, (f"{self.cache_key_prefix}%",))
            
            entries = cursor.fetchall()
            conn.close()
            
            cache_info = {
                'total_entries': len(entries),
                'entries': []
            }
            
            for entry in entries:
                cache_key, created_at, expires_at, cache_data_json = entry
                
                try:
                    cache_data = json.loads(cache_data_json)
                    entry_info = {
                        'key': cache_key,
                        'created_at': created_at,
                        'expires_at': expires_at,
                        'is_expired': datetime.fromisoformat(expires_at) < datetime.now(),
                        'symbols_count': cache_data.get('symbols_count', 0),
                        'results_count': cache_data.get('results_count', 0),
                        'symbols': cache_data.get('symbols', [])[:5],  # Первые 5 символов
                        'min_volume': cache_data.get('min_volume', 0),
                        'min_avg_volume': cache_data.get('min_avg_volume', 0)
                    }
                    cache_info['entries'].append(entry_info)
                except json.JSONDecodeError:
                    logger.warning(f"⚠️ [CACHE] Не удалось декодировать данные для ключа: {cache_key}")
            
            logger.info(f"🔍 [CACHE] Инспекция завершена: {len(entries)} записей")
            return cache_info
            
        except Exception as e:
            logger.error(f"❌ [CACHE] Ошибка инспекции кэша: {e}")
            return {}


# Глобальный экземпляр менеджера кэша
cascade_ml_cache = CascadeMLCacheManager()
