#!/usr/bin/env python3
"""
Cascade Signal Notifications.
Система уведомлений для каскадных торговых сигналов.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import asyncio

from .cascade_analyzer import CascadeSignalResult
from .notifications import NotificationManager

logger = logging.getLogger(__name__)


class CascadeNotificationManager:
    """Менеджер уведомлений для каскадных сигналов."""
    
    def __init__(self, notification_manager: NotificationManager = None):
        self.notification_manager = notification_manager or NotificationManager()
        
        # Настройки уведомлений
        self.notification_config = {
            'enabled': True,
            'min_confidence_for_notification': 0.7,
            'min_risk_reward_for_notification': 2.0,
            'auto_trade_notifications': True,
            'stage_rejection_notifications': False,  # Уведомления об отклонении на этапах
            'daily_summary': True,
            'telegram_enabled': True,
            'email_enabled': False,
            'webhook_enabled': False
        }
        
        # Кэш для предотвращения дублирования уведомлений
        self.notification_cache = {}
        self.cache_duration = timedelta(minutes=30)
    
    async def notify_cascade_signal(self, result: CascadeSignalResult) -> bool:
        """
        Отправить уведомление о каскадном сигнале.
        
        Args:
            result: Результат каскадного анализа
            
        Returns:
            bool: True если уведомление отправлено успешно
        """
        try:
            if not self.notification_config['enabled']:
                return False
            
            if not result.final_signal:
                return False
            
            # Проверяем кэш для предотвращения дублирования
            cache_key = f"{result.symbol}_{result.final_signal}_{result.entry_price:.2f}"
            if self._is_cached(cache_key):
                logger.info(f"Notification already sent for {cache_key}")
                return False
            
            # Проверяем критерии для уведомления
            if not self._should_notify(result):
                return False
            
            # Формируем уведомление
            notification_data = self._format_cascade_notification(result)
            
            # Отправляем уведомления
            success = False
            
            if self.notification_config['telegram_enabled']:
                success |= await self._send_telegram_notification(notification_data)
            
            if self.notification_config['email_enabled']:
                success |= await self._send_email_notification(notification_data)
            
            if self.notification_config['webhook_enabled']:
                success |= await self._send_webhook_notification(notification_data)
            
            # Сохраняем в кэш
            if success:
                self._cache_notification(cache_key)
                logger.info(f"Cascade notification sent for {result.symbol}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending cascade notification for {result.symbol}: {e}")
            return False
    
    async def notify_auto_trade_execution(self, trade_result: Dict[str, Any]) -> bool:
        """
        Отправить уведомление об автоматической сделке.
        
        Args:
            trade_result: Результат автоматической сделки
            
        Returns:
            bool: True если уведомление отправлено успешно
        """
        try:
            if not self.notification_config['auto_trade_notifications']:
                return False
            
            notification_data = {
                'type': 'auto_trade_execution',
                'title': '🤖 Автоматическая сделка выполнена',
                'symbol': trade_result.get('symbol', 'Unknown'),
                'side': trade_result.get('side', 'Unknown'),
                'quantity': trade_result.get('quantity', 0),
                'price': trade_result.get('price', 0.0),
                'balance': trade_result.get('balance', 0.0),
                'timestamp': datetime.now().isoformat(),
                'success': trade_result.get('success', False)
            }
            
            success = False
            
            if self.notification_config['telegram_enabled']:
                success |= await self._send_telegram_notification(notification_data)
            
            if self.notification_config['email_enabled']:
                success |= await self._send_email_notification(notification_data)
            
            if self.notification_config['webhook_enabled']:
                success |= await self._send_webhook_notification(notification_data)
            
            if success:
                logger.info(f"Auto trade notification sent for {trade_result.get('symbol')}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending auto trade notification: {e}")
            return False
    
    async def notify_stage_rejection(self, symbol: str, stage: str, reason: str) -> bool:
        """
        Отправить уведомление об отклонении на этапе.
        
        Args:
            symbol: Торговый символ
            stage: Этап, на котором произошло отклонение
            reason: Причина отклонения
            
        Returns:
            bool: True если уведомление отправлено успешно
        """
        try:
            if not self.notification_config['stage_rejection_notifications']:
                return False
            
            notification_data = {
                'type': 'stage_rejection',
                'title': f'⚠️ Сигнал отклонен на этапе {stage}',
                'symbol': symbol,
                'stage': stage,
                'reason': reason,
                'timestamp': datetime.now().isoformat()
            }
            
            success = False
            
            if self.notification_config['telegram_enabled']:
                success |= await self._send_telegram_notification(notification_data)
            
            if self.notification_config['webhook_enabled']:
                success |= await self._send_webhook_notification(notification_data)
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending stage rejection notification: {e}")
            return False
    
    async def send_daily_summary(self, results: List[CascadeSignalResult]) -> bool:
        """
        Отправить дневную сводку по каскадным сигналам.
        
        Args:
            results: Список результатов каскадного анализа
            
        Returns:
            bool: True если сводка отправлена успешно
        """
        try:
            if not self.notification_config['daily_summary']:
                return False
            
            # Анализируем результаты
            successful_signals = [r for r in results if r.final_signal]
            rejected_signals = [r for r in results if not r.final_signal]
            
            buy_signals = [r for r in successful_signals if r.final_signal == 'BUY']
            sell_signals = [r for r in successful_signals if r.final_signal == 'SELL']
            
            # Статистика по этапам отклонения
            rejection_stats = {}
            for result in rejected_signals:
                stage = result.rejected_at_stage or 'unknown'
                rejection_stats[stage] = rejection_stats.get(stage, 0) + 1
            
            notification_data = {
                'type': 'daily_summary',
                'title': '📊 Дневная сводка каскадных сигналов',
                'date': datetime.now().strftime('%Y-%m-%d'),
                'total_analyzed': len(results),
                'successful_signals': len(successful_signals),
                'rejected_signals': len(rejected_signals),
                'buy_signals': len(buy_signals),
                'sell_signals': len(sell_signals),
                'rejection_stats': rejection_stats,
                'avg_confidence': sum(r.confidence for r in successful_signals) / len(successful_signals) if successful_signals else 0,
                'timestamp': datetime.now().isoformat()
            }
            
            success = False
            
            if self.notification_config['telegram_enabled']:
                success |= await self._send_telegram_notification(notification_data)
            
            if self.notification_config['email_enabled']:
                success |= await self._send_email_notification(notification_data)
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending daily summary: {e}")
            return False
    
    def _should_notify(self, result: CascadeSignalResult) -> bool:
        """Проверить, следует ли отправлять уведомление."""
        try:
            # Проверяем минимальную уверенность
            if result.confidence < self.notification_config['min_confidence_for_notification']:
                return False
            
            # Проверяем минимальное соотношение риск/доходность
            if result.risk_reward < self.notification_config['min_risk_reward_for_notification']:
                return False
            
            return True
            
        except Exception:
            return False
    
    def _format_cascade_notification(self, result: CascadeSignalResult) -> Dict[str, Any]:
        """Форматировать данные для уведомления о каскадном сигнале."""
        try:
            # Определяем эмодзи для сигнала
            signal_emoji = "🟢" if result.final_signal == 'BUY' else "🔴"
            signal_text = "ПОКУПКА" if result.final_signal == 'BUY' else "ПРОДАЖА"
            
            # Форматируем информацию об этапах
            stages_info = []
            for stage, stage_data in result.stages.items():
                if stage_data.get('proceed', False):
                    stages_info.append(f"✅ {stage}: {stage_data.get('reason', 'OK')}")
                else:
                    stages_info.append(f"❌ {stage}: {stage_data.get('reason', 'Failed')}")
            
            stages_text = "\n".join(stages_info)
            
            notification_data = {
                'type': 'cascade_signal',
                'title': f'{signal_emoji} Каскадный сигнал {signal_text}',
                'symbol': result.symbol,
                'signal': result.final_signal,
                'confidence': f"{result.confidence:.1%}",
                'entry_price': f"{result.entry_price:.2f}",
                'stop_loss': f"{result.stop_loss:.2f}",
                'take_profit': f"{result.take_profit:.2f}",
                'risk_reward': f"{result.risk_reward:.1f}",
                'stages': stages_text,
                'auto_trade_enabled': result.auto_trade_enabled,
                'timestamp': result.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            return notification_data
            
        except Exception as e:
            logger.error(f"Error formatting cascade notification: {e}")
            return {}
    
    async def _send_telegram_notification(self, notification_data: Dict[str, Any]) -> bool:
        """Отправить уведомление в Telegram."""
        try:
            if not self.notification_manager:
                return False
            
            message = self._format_telegram_message(notification_data)
            
            # Используем существующий notification_manager
            if hasattr(self.notification_manager, 'send_telegram_message'):
                return await self.notification_manager.send_telegram_message(message)
            else:
                # Fallback - логируем сообщение
                logger.info(f"Telegram notification: {message}")
                return True
                
        except Exception as e:
            logger.error(f"Error sending Telegram notification: {e}")
            return False
    
    async def _send_email_notification(self, notification_data: Dict[str, Any]) -> bool:
        """Отправить уведомление по email."""
        try:
            if not self.notification_manager:
                return False
            
            subject = notification_data.get('title', 'Cascade Signal Notification')
            message = self._format_email_message(notification_data)
            
            # Используем существующий notification_manager
            if hasattr(self.notification_manager, 'send_email'):
                return await self.notification_manager.send_email(subject, message)
            else:
                # Fallback - логируем сообщение
                logger.info(f"Email notification: {subject} - {message}")
                return True
                
        except Exception as e:
            logger.error(f"Error sending email notification: {e}")
            return False
    
    async def _send_webhook_notification(self, notification_data: Dict[str, Any]) -> bool:
        """Отправить уведомление через webhook."""
        try:
            if not self.notification_manager:
                return False
            
            # Используем существующий notification_manager
            if hasattr(self.notification_manager, 'send_webhook'):
                return await self.notification_manager.send_webhook(notification_data)
            else:
                # Fallback - логируем данные
                logger.info(f"Webhook notification: {notification_data}")
                return True
                
        except Exception as e:
            logger.error(f"Error sending webhook notification: {e}")
            return False
    
    def _format_telegram_message(self, notification_data: Dict[str, Any]) -> str:
        """Форматировать сообщение для Telegram."""
        try:
            notification_type = notification_data.get('type', 'unknown')
            
            if notification_type == 'cascade_signal':
                message = f"""
🎯 {notification_data.get('title', 'Каскадный сигнал')}

📊 **{notification_data.get('symbol')}** - {notification_data.get('signal')}
💰 Цена входа: {notification_data.get('entry_price')} ₽
🛡️ Стоп-лосс: {notification_data.get('stop_loss')} ₽
🎯 Тейк-профит: {notification_data.get('take_profit')} ₽
⚖️ Риск/Доходность: {notification_data.get('risk_reward')}
🎯 Уверенность: {notification_data.get('confidence')}

📋 **Этапы анализа:**
{notification_data.get('stages', 'N/A')}

🤖 Автоторговля: {'✅ Включена' if notification_data.get('auto_trade_enabled') else '❌ Отключена'}
🕐 Время: {notification_data.get('timestamp')}
"""
            
            elif notification_type == 'auto_trade_execution':
                message = f"""
🤖 {notification_data.get('title', 'Автоматическая сделка')}

📊 **{notification_data.get('symbol')}** - {notification_data.get('side')}
📦 Количество: {notification_data.get('quantity')} шт.
💰 Цена: {notification_data.get('price')} ₽
💳 Баланс: {notification_data.get('balance')} ₽
🕐 Время: {notification_data.get('timestamp')}
"""
            
            elif notification_type == 'daily_summary':
                message = f"""
📊 {notification_data.get('title', 'Дневная сводка')}

📈 Всего проанализировано: {notification_data.get('total_analyzed')}
✅ Успешных сигналов: {notification_data.get('successful_signals')}
❌ Отклоненных сигналов: {notification_data.get('rejected_signals')}

📊 **Распределение сигналов:**
🟢 Покупки: {notification_data.get('buy_signals')}
🔴 Продажи: {notification_data.get('sell_signals')}

📉 **Отклонения по этапам:**
"""
                for stage, count in notification_data.get('rejection_stats', {}).items():
                    message += f"• {stage}: {count}\n"
                
                avg_conf = notification_data.get('avg_confidence', 0)
                message += f"\n🎯 Средняя уверенность: {avg_conf:.1%}"
                message += f"\n🕐 Дата: {notification_data.get('date')}"
            
            else:
                message = f"🔔 {notification_data.get('title', 'Уведомление')}\n\n{notification_data}"
            
            return message.strip()
            
        except Exception as e:
            logger.error(f"Error formatting Telegram message: {e}")
            return f"🔔 Уведомление: {notification_data.get('title', 'Cascade Signal')}"
    
    def _format_email_message(self, notification_data: Dict[str, Any]) -> str:
        """Форматировать сообщение для email."""
        try:
            notification_type = notification_data.get('type', 'unknown')
            
            if notification_type == 'cascade_signal':
                message = f"""
Каскадный торговый сигнал

Символ: {notification_data.get('symbol')}
Сигнал: {notification_data.get('signal')}
Цена входа: {notification_data.get('entry_price')} ₽
Стоп-лосс: {notification_data.get('stop_loss')} ₽
Тейк-профит: {notification_data.get('take_profit')} ₽
Риск/Доходность: {notification_data.get('risk_reward')}
Уверенность: {notification_data.get('confidence')}

Этапы анализа:
{notification_data.get('stages', 'N/A')}

Автоторговля: {'Включена' if notification_data.get('auto_trade_enabled') else 'Отключена'}
Время: {notification_data.get('timestamp')}
"""
            
            else:
                message = f"Уведомление: {notification_data.get('title', 'Cascade Signal')}\n\n{notification_data}"
            
            return message.strip()
            
        except Exception as e:
            logger.error(f"Error formatting email message: {e}")
            return f"Уведомление: {notification_data.get('title', 'Cascade Signal')}"
    
    def _is_cached(self, cache_key: str) -> bool:
        """Проверить, есть ли уведомление в кэше."""
        try:
            if cache_key in self.notification_cache:
                cache_time = self.notification_cache[cache_key]
                if datetime.now() - cache_time < self.cache_duration:
                    return True
                else:
                    # Удаляем устаревший кэш
                    del self.notification_cache[cache_key]
            return False
        except Exception:
            return False
    
    def _cache_notification(self, cache_key: str):
        """Сохранить уведомление в кэш."""
        try:
            self.notification_cache[cache_key] = datetime.now()
        except Exception as e:
            logger.error(f"Error caching notification: {e}")
    
    def update_notification_config(self, config_updates: Dict[str, Any]):
        """Обновить настройки уведомлений."""
        self.notification_config.update(config_updates)
        logger.info(f"Notification config updated: {config_updates}")
    
    def get_notification_config(self) -> Dict[str, Any]:
        """Получить текущие настройки уведомлений."""
        return self.notification_config.copy()
    
    def clear_notification_cache(self):
        """Очистить кэш уведомлений."""
        self.notification_cache.clear()
        logger.info("Notification cache cleared")




