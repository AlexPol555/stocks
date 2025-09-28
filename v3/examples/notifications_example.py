#!/usr/bin/env python3
"""Example usage of the notifications system."""

import asyncio
import sys
import os
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.notifications import (
    notify_signal,
    notify_error,
    notify_critical,
    notify_trade,
    notification_manager,
    dashboard_alerts
)


async def example_notifications():
    """Example of using the notifications system."""
    
    print("🔔 Testing Notifications System")
    print("=" * 50)
    
    # Test 1: Signal notification
    print("\n1. Testing signal notification...")
    try:
        await notify_signal(
            ticker="AAPL",
            signal_type="Adaptive Buy",
            price=150.25,
            signal_value=1,
            additional_data={"rsi": 30, "atr": 2.5}
        )
        print("✅ Signal notification sent")
    except Exception as e:
        print(f"❌ Signal notification failed: {e}")
    
    # Test 2: Error notification
    print("\n2. Testing error notification...")
    try:
        await notify_error(
            error_type="Database Error",
            error_message="Connection timeout",
            component="Database",
            additional_data={"retry_count": 3}
        )
        print("✅ Error notification sent")
    except Exception as e:
        print(f"❌ Error notification failed: {e}")
    
    # Test 3: Critical notification
    print("\n3. Testing critical notification...")
    try:
        await notify_critical(
            critical_type="System Failure",
            message="Database is down",
            additional_data={"affected_components": ["trading", "analytics"]}
        )
        print("✅ Critical notification sent")
    except Exception as e:
        print(f"❌ Critical notification failed: {e}")
    
    # Test 4: Trade notification
    print("\n4. Testing trade notification...")
    try:
        await notify_trade(
            ticker="AAPL",
            side="BUY",
            quantity=10,
            price=150.30,
            total_value=1503.0,
            additional_data={"commission": 1.50}
        )
        print("✅ Trade notification sent")
    except Exception as e:
        print(f"❌ Trade notification failed: {e}")
    
    # Test 5: Dashboard alerts
    print("\n5. Testing dashboard alerts...")
    try:
        dashboard_alerts.add_signal_alert(
            ticker="MSFT",
            signal_type="New Adaptive Buy",
            price=300.50,
            signal_value=1
        )
        print("✅ Dashboard alert added")
    except Exception as e:
        print(f"❌ Dashboard alert failed: {e}")
    
    # Test 6: Notification manager status
    print("\n6. Testing notification manager...")
    try:
        status = notification_manager.get_status()
        print(f"✅ Notification manager status: {status}")
    except Exception as e:
        print(f"❌ Notification manager status failed: {e}")
    
    # Test 7: Dashboard alerts statistics
    print("\n7. Testing dashboard alerts statistics...")
    try:
        stats = dashboard_alerts.get_notification_stats()
        print(f"✅ Dashboard alerts stats: {stats}")
    except Exception as e:
        print(f"❌ Dashboard alerts stats failed: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 Notifications system test completed!")


def example_sync_usage():
    """Example of synchronous usage (for dashboard)."""
    
    print("\n📊 Testing Synchronous Dashboard Usage")
    print("=" * 50)
    
    # Add notifications to dashboard
    dashboard_alerts.add_signal_alert(
        ticker="GOOGL",
        signal_type="Final Buy",
        price=2500.75,
        signal_value=1
    )
    
    dashboard_alerts.add_error_alert(
        error_type="API Error",
        error_message="Rate limit exceeded",
        component="Data Loader"
    )
    
    dashboard_alerts.add_critical_alert(
        critical_type="Memory Warning",
        message="High memory usage detected"
    )
    
    # Get statistics
    stats = dashboard_alerts.get_notification_stats()
    print(f"📈 Dashboard notifications: {stats['total']} total, {stats['unread']} unread")
    
    # Get notifications
    notifications = dashboard_alerts.get_notifications(limit=5)
    print(f"📋 Recent notifications: {len(notifications)}")
    
    for i, notification in enumerate(notifications, 1):
        print(f"  {i}. {notification['title']} - {notification['message'][:50]}...")


if __name__ == "__main__":
    print("🚀 Starting Notifications System Examples")
    
    # Run synchronous examples
    example_sync_usage()
    
    # Run asynchronous examples
    try:
        asyncio.run(example_notifications())
    except Exception as e:
        print(f"❌ Async examples failed: {e}")
    
    print("\n✨ All examples completed!")
