#!/usr/bin/env python3
"""
Test script for CodeNews - manually trigger RSS check and notifications
"""

import asyncio
import sys
from pathlib import Path

try:
    import pytest
except ImportError:  # pragma: no cover
    pytest = None

if pytest:
    pytestmark = pytest.mark.skip(
        reason="Integration script; run manually via `python test_notifications.py`."
    )

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.database import init_db
from src.rss_monitor import run_rss_check
from src.content_filter import filter_content
from src.ml_engine import update_preference_learning
from src.telegram_bot import send_content_notifications
from src.config import Config

async def test_rss_and_notifications():
    """Test RSS monitoring and Telegram notifications"""
    
    print("🔧 CodeNews Test Script\n")
    
    # Validate config
    try:
        Config.validate()
        print("✅ Configuration validated")
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        print("\nMake sure you have:")
        print("1. Created .env file (cp .env.example .env)")
        print("2. Added TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID")
        return
    
    # Initialize database
    print("📊 Initializing database...")
    init_db()
    print("✅ Database ready")
    
    # Check RSS feeds
    print("\n📡 Checking RSS feeds...")
    new_items = run_rss_check()
    
    if not new_items:
        print("ℹ️  No new items found")
        print("\nTips:")
        print("- Check if RSS feeds in data/feeds.json are accessible")
        print("- Content might already be in database")
        print("- Try deleting data/codenews.db to start fresh")
        return
    
    print(f"✅ Found {len(new_items)} new items")
    
    # Filter and categorize
    print("\n🔍 Filtering and categorizing content...")
    filtered_items = filter_content()
    
    if not filtered_items:
        print("ℹ️  No relevant items after filtering")
        print("\nTips:")
        print("- Lower the relevance_threshold in config.yaml")
        print("- Check keyword lists in config.yaml")
        return
    
    print(f"✅ {len(filtered_items)} relevant items after filtering")
    
    # Update ML scores
    print("\n🧠 Updating ML scores...")
    update_preference_learning()
    print("✅ Scores updated")
    
    # Display items (filtered_items now returns dictionaries)
    print("\n📋 Items to be sent:")
    for i, item in enumerate(filtered_items[:5], 1):
        print(f"\n{i}. {item['title'][:60]}...")
        print(f"   Category: {item['category']}")
        print(f"   Score: {item['relevance_score']:.2f}")
        print(f"   URL: {item['url'][:50]}...")
    
    # Send notifications
    print("\n📱 Sending Telegram notifications...")
    try:
        sent_count = await send_content_notifications(filtered_items)
        print(f"✅ Sent {sent_count} notification(s)")
        
        if sent_count > 0:
            print("\n🎉 Success! Check your Telegram for notifications.")
            print("💡 Use 👍/👎 buttons to train the ML model.")
        
    except Exception as e:
        print(f"❌ Error sending notifications: {e}")
        print("\nTroubleshooting:")
        print("- Verify TELEGRAM_BOT_TOKEN is correct")
        print("- Verify TELEGRAM_CHAT_ID is correct")
        print("- Start a chat with your bot first (/start)")
        print("- Check logs/codenews.log for details")

if __name__ == "__main__":
    print("Starting test...\n")
    try:
        asyncio.run(test_rss_and_notifications())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
