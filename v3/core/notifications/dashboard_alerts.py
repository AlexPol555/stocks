"""Dashboard alerts and notifications display."""

from __future__ import annotations

import streamlit as st
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
import json

from .message_formatter import MessageFormatter, NotificationData, NotificationType


class DashboardAlerts:
    """Manages dashboard alerts and notifications."""
    
    def __init__(self):
        """Initialize dashboard alerts."""
        self.formatter = MessageFormatter()
        self.session_key = "dashboard_notifications"
        
        # Initialize session state if not exists
        if self.session_key not in st.session_state:
            st.session_state[self.session_key] = {
                "notifications": [],
                "last_cleanup": datetime.now()
            }
    
    def add_notification(self, notification: Union[NotificationData, Dict[str, Any]]) -> None:
        """Add a notification to the dashboard.
        
        Args:
            notification: Notification to add (NotificationData object or dict)
        """
        # Handle both NotificationData objects and dictionaries
        if isinstance(notification, dict):
            # If it's already a dictionary, use it directly
            dashboard_notification = notification
        else:
            # If it's a NotificationData object, format it
            dashboard_notification = self.formatter.format_dashboard(notification)
        
        # Add to session state
        notifications = st.session_state[self.session_key]["notifications"]
        notifications.append(dashboard_notification)
        
        # Keep only last 100 notifications
        if len(notifications) > 100:
            notifications[:] = notifications[-100:]
        
        st.session_state[self.session_key]["notifications"] = notifications
    
    def add_signal_alert(
        self,
        ticker: str,
        signal_type: str,
        price: float,
        signal_value: int,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add a signal alert to the dashboard.
        
        Args:
            ticker: Stock ticker
            signal_type: Type of signal
            price: Stock price
            signal_value: Signal value (1 for buy, -1 for sell)
            additional_data: Additional data
        """
        notification = self.formatter.format_signal_notification(
            ticker=ticker,
            signal_type=signal_type,
            price=price,
            signal_value=signal_value,
            additional_data=additional_data
        )
        self.add_notification(notification)
    
    def add_error_alert(
        self,
        error_type: str,
        error_message: str,
        component: str,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add an error alert to the dashboard.
        
        Args:
            error_type: Type of error
            error_message: Error message
            component: Component where error occurred
            additional_data: Additional data
        """
        notification = self.formatter.format_error_notification(
            error_type=error_type,
            error_message=error_message,
            component=component,
            additional_data=additional_data
        )
        self.add_notification(notification)
    
    def add_critical_alert(
        self,
        critical_type: str,
        message: str,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add a critical alert to the dashboard.
        
        Args:
            critical_type: Type of critical event
            message: Critical message
            additional_data: Additional data
        """
        notification = self.formatter.format_critical_notification(
            critical_type=critical_type,
            message=message,
            additional_data=additional_data
        )
        self.add_notification(notification)
    
    def add_trade_alert(
        self,
        ticker: str,
        side: str,
        quantity: int,
        price: float,
        total_value: float,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add a trade execution alert to the dashboard.
        
        Args:
            ticker: Stock ticker
            side: Trade side (BUY/SELL)
            quantity: Quantity traded
            price: Execution price
            total_value: Total trade value
            additional_data: Additional data
        """
        # Create NotificationData object
        notification_data = self.formatter.format_trade_executed_notification(
            ticker=ticker,
            side=side,
            quantity=quantity,
            price=price,
            total_value=total_value,
            additional_data=additional_data
        )
        # Add directly to dashboard (format_dashboard will be called in add_notification)
        self.add_notification(notification_data)
    
    def add_health_check_alert(
        self,
        component: str,
        status: str,
        details: Optional[Dict[str, Any]] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add a health check alert to the dashboard.
        
        Args:
            component: Component name
            status: Health status
            details: Health check details
            additional_data: Additional data
        """
        # Create NotificationData object
        notification_data = self.formatter.format_health_check_notification(
            component=component,
            status=status,
            details=details,
            additional_data=additional_data
        )
        # Add directly to dashboard (format_dashboard will be called in add_notification)
        self.add_notification(notification_data)
    
    def get_notifications(
        self,
        notification_type: Optional[NotificationType] = None,
        unread_only: bool = False,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get notifications from the dashboard.
        
        Args:
            notification_type: Filter by notification type
            unread_only: Only return unread notifications
            limit: Maximum number of notifications to return
            
        Returns:
            List of notification dictionaries
        """
        # Initialize session state if not exists
        if self.session_key not in st.session_state:
            st.session_state[self.session_key] = {
                "notifications": [],
                "last_cleanup": datetime.now()
            }
        
        notifications = st.session_state[self.session_key]["notifications"]
        
        # Filter by type
        if notification_type:
            notifications = [
                n for n in notifications
                if n["type"] == notification_type.value
            ]
        
        # Filter by read status
        if unread_only:
            notifications = [
                n for n in notifications
                if not n.get("is_read", False)
            ]
        
        # Apply limit
        if limit:
            notifications = notifications[-limit:]
        
        return notifications
    
    def mark_as_read(self, notification_id: str) -> None:
        """Mark a notification as read.
        
        Args:
            notification_id: ID of the notification to mark as read
        """
        notifications = st.session_state[self.session_key]["notifications"]
        for notification in notifications:
            if notification["id"] == notification_id:
                notification["is_read"] = True
                break
    
    def mark_all_as_read(self) -> None:
        """Mark all notifications as read."""
        notifications = st.session_state[self.session_key]["notifications"]
        for notification in notifications:
            notification["is_read"] = True
    
    def clear_notifications(self, notification_type: Optional[NotificationType] = None) -> None:
        """Clear notifications from the dashboard.
        
        Args:
            notification_type: Clear only specific type, or all if None
        """
        if notification_type:
            notifications = st.session_state[self.session_key]["notifications"]
            st.session_state[self.session_key]["notifications"] = [
                n for n in notifications
                if n["type"] != notification_type.value
            ]
        else:
            st.session_state[self.session_key]["notifications"] = []
    
    def cleanup_old_notifications(self, hours: int = 24) -> None:
        """Remove notifications older than specified hours.
        
        Args:
            hours: Remove notifications older than this many hours
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        notifications = st.session_state[self.session_key]["notifications"]
        
        st.session_state[self.session_key]["notifications"] = [
            n for n in notifications
            if n["timestamp"] >= cutoff_time
        ]
    
    def get_notification_stats(self) -> Dict[str, int]:
        """Get notification statistics.
        
        Returns:
            Dictionary with notification counts by type and status
        """
        # Initialize session state if not exists
        if self.session_key not in st.session_state:
            st.session_state[self.session_key] = {
                "notifications": [],
                "last_cleanup": datetime.now()
            }
        
        notifications = st.session_state[self.session_key]["notifications"]
        
        stats = {
            "total": len(notifications),
            "unread": sum(1 for n in notifications if not n.get("is_read", False)),
            "by_type": {},
            "by_priority": {1: 0, 2: 0, 3: 0, 4: 0}
        }
        
        for notification in notifications:
            # Count by type
            ntype = notification["type"]
            stats["by_type"][ntype] = stats["by_type"].get(ntype, 0) + 1
            
            # Count by priority
            priority = notification.get("priority", 1)
            stats["by_priority"][priority] = stats["by_priority"].get(priority, 0) + 1
        
        return stats
    
    def render_notifications_panel(self, max_notifications: int = 10) -> None:
        """Render the notifications panel in the dashboard.
        
        Args:
            max_notifications: Maximum number of notifications to display
        """
        notifications = self.get_notifications(limit=max_notifications)
        
        if not notifications:
            st.info("Нет новых уведомлений")
            return
        
        # Group by priority
        critical_notifications = [n for n in notifications if n.get("priority", 1) >= 4]
        high_notifications = [n for n in notifications if n.get("priority", 1) == 3]
        other_notifications = [n for n in notifications if n.get("priority", 1) <= 2]
        
        # Display critical notifications first
        if critical_notifications:
            st.error("🚨 Критические уведомления")
            for notification in critical_notifications:
                self._render_single_notification(notification)
        
        # Display high priority notifications
        if high_notifications:
            st.warning("⚠️ Важные уведомления")
            for notification in high_notifications:
                self._render_single_notification(notification)
        
        # Display other notifications
        if other_notifications:
            st.info("📢 Обычные уведомления")
            for notification in other_notifications:
                self._render_single_notification(notification)
    
    def _render_single_notification(self, notification: Dict[str, Any]) -> None:
        """Render a single notification.
        
        Args:
            notification: Notification dictionary
        """
        with st.container():
            col1, col2 = st.columns([4, 1])
            
            with col1:
                # Notification content
                st.markdown(f"**{notification['title']}**")
                st.caption(notification['message'])
                
                # Additional data
                if notification.get('data'):
                    with st.expander("Детали"):
                        st.json(notification['data'])
            
            with col2:
                # Timestamp and actions
                timestamp = notification['timestamp']
                if isinstance(timestamp, str):
                    timestamp = datetime.fromisoformat(timestamp)
                
                st.caption(timestamp.strftime("%H:%M:%S"))
                
                # Mark as read button
                if not notification.get('is_read', False):
                    if st.button("✓", key=f"read_{notification['id']}", help="Отметить как прочитанное"):
                        self.mark_as_read(notification['id'])
                        st.rerun()
    
    def render_notification_badge(self) -> None:
        """Render a notification badge in the sidebar."""
        stats = self.get_notification_stats()
        
        if stats["unread"] > 0:
            st.sidebar.markdown("---")
            st.sidebar.markdown("### 🔔 Уведомления")
            
            # Badge with count
            if stats["unread"] > 99:
                badge_text = "99+"
            else:
                badge_text = str(stats["unread"])
            
            st.sidebar.markdown(f"**Непрочитанных: {badge_text}**")
            
            # Quick actions
            col1, col2 = st.sidebar.columns(2)
            with col1:
                if st.button("Показать все", key="show_all_notifications"):
                    st.session_state["show_notifications"] = True
            with col2:
                if st.button("Отметить все", key="mark_all_read"):
                    self.mark_all_as_read()
                    st.rerun()
            
            # Show critical notifications count
            critical_count = stats["by_priority"].get(4, 0)
            if critical_count > 0:
                st.sidebar.error(f"🚨 Критических: {critical_count}")
    
    def render_full_notifications_page(self) -> None:
        """Render a full notifications page."""
        st.title("🔔 Уведомления")
        
        # Statistics
        stats = self.get_notification_stats()
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Всего", stats["total"])
        with col2:
            st.metric("Непрочитанных", stats["unread"])
        with col3:
            st.metric("Критических", stats["by_priority"].get(4, 0))
        with col4:
            st.metric("Важных", stats["by_priority"].get(3, 0))
        
        # Filters
        st.subheader("Фильтры")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            notification_types = [t.value for t in NotificationType]
            selected_type = st.selectbox(
                "Тип уведомления",
                ["Все"] + notification_types,
                key="notification_type_filter"
            )
        
        with col2:
            show_unread_only = st.checkbox("Только непрочитанные", key="unread_only_filter")
        
        with col3:
            limit = st.number_input("Лимит", min_value=1, max_value=100, value=50, key="limit_filter")
        
        # Apply filters
        filter_type = None
        if selected_type != "Все":
            filter_type = NotificationType(selected_type)
        
        notifications = self.get_notifications(
            notification_type=filter_type,
            unread_only=show_unread_only,
            limit=limit
        )
        
        # Display notifications
        if notifications:
            st.subheader(f"Уведомления ({len(notifications)})")
            
            # Bulk actions
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("Отметить все как прочитанные"):
                    self.mark_all_as_read()
                    st.rerun()
            with col2:
                if st.button("Очистить все"):
                    self.clear_notifications()
                    st.rerun()
            with col3:
                if st.button("Очистить старые (24ч)"):
                    self.cleanup_old_notifications(24)
                    st.rerun()
            
            # Notifications list
            for notification in reversed(notifications):  # Show newest first
                self._render_single_notification(notification)
        else:
            st.info("Нет уведомлений, соответствующих фильтрам")


# Global instance for easy access
dashboard_alerts = DashboardAlerts()
