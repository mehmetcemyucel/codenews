"""
Main entry point for CodeNews application
"""

import logging
import asyncio
import sys
from pathlib import Path
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import Config
from src.database import init_db
from src.rss_monitor import run_rss_check
from src.content_filter import filter_content
from src.ml_engine import update_preference_learning
from src.telegram_bot import TelegramBot, send_content_notifications
from src.blog_generator import generate_weekly_blog

# Load environment variables
load_dotenv()

# Setup logging
def setup_logging():
    """Configure logging for the application"""
    log_level = getattr(logging, Config.LOG_LEVEL, logging.INFO)
    
    # Create logs directory if it doesn't exist
    Config.LOGS_DIR.mkdir(exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(Config.LOGS_DIR / 'codenews.log'),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger(__name__)


logger = setup_logging()


async def hourly_rss_job():
    """Job to check RSS feeds hourly"""
    try:
        logger.info("Starting hourly RSS check...")
        
        # 1. Check RSS feeds for new content
        new_items = run_rss_check()
        
        if not new_items:
            logger.info("No new items found")
            return
        
        # 2. Filter and categorize content
        filtered_items = filter_content()
        
        if not filtered_items:
            logger.info("No relevant items after filtering")
            return
        
        # 3. Update ML scores based on preferences
        update_preference_learning()
        
        # 4. Send notifications via Telegram
        await send_content_notifications(filtered_items)
        
        logger.info(f"Hourly job complete. Processed {len(new_items)} new items, sent {len(filtered_items)} notifications")
    
    except Exception as e:
        logger.error(f"Error in hourly job: {e}", exc_info=True)


async def weekly_blog_job():
    """Job to generate weekly blog post"""
    try:
        logger.info("Starting weekly blog generation...")
        
        digest = generate_weekly_blog()
        
        if digest:
            logger.info(f"Weekly digest published: {digest['telegraph_url']}")
        else:
            logger.warning("Weekly digest generation failed or insufficient content")
    
    except Exception as e:
        logger.error(f"Error in weekly blog job: {e}", exc_info=True)


async def daily_cleanup_job():
    """Job to clean up old database records (30+ days)"""
    try:
        logger.info("Starting daily cleanup...")
        
        from datetime import datetime, timedelta
        from src.database import get_db_session, Content, Feedback
        
        db = get_db_session()
        try:
            # Delete content older than 30 days
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            
            # Get old content IDs
            old_content = db.query(Content).filter(Content.fetched_date < thirty_days_ago).all()
            old_content_ids = [c.id for c in old_content]
            
            if old_content_ids:
                # Delete associated feedbacks first (foreign key constraint)
                deleted_feedback = db.query(Feedback).filter(Feedback.content_id.in_(old_content_ids)).delete(synchronize_session=False)
                
                # Delete old content
                deleted_content = db.query(Content).filter(Content.id.in_(old_content_ids)).delete(synchronize_session=False)
                
                db.commit()
                logger.info(f"Cleanup complete: Deleted {deleted_content} content items and {deleted_feedback} feedbacks (30+ days old)")
            else:
                logger.info("No old records to clean up")
        
        finally:
            db.close()
    
    except Exception as e:
        logger.error(f"Error in daily cleanup job: {e}", exc_info=True)


async def main():
    """Main application entry point"""
    try:
        logger.info("Starting CodeNews application...")
        
        # Validate configuration
        Config.validate()
        
        # Initialize database
        logger.info("Initializing database...")
        init_db()
        
        # Create scheduler
        scheduler = AsyncIOScheduler()
        
        # Schedule hourly RSS check
        scheduler.add_job(
            hourly_rss_job,
            trigger=CronTrigger(minute=0),  # Every hour at :00
            id='hourly_rss_check',
            name='Hourly RSS Check',
            replace_existing=True
        )
        
        # Schedule daily cleanup (every day at 3 AM)
        scheduler.add_job(
            daily_cleanup_job,
            trigger=CronTrigger(hour=3, minute=0),
            id='daily_cleanup',
            name='Daily Cleanup',
            replace_existing=True
        )
        
        # Start scheduler
        scheduler.start()
        logger.info("Scheduler started")
        logger.info(f"- Hourly RSS check: Every hour at :00")
        logger.info(f"- Daily cleanup: Every day at 03:00 (removes 30+ days old records)")
        
        # Run initial RSS check
        logger.info("Running initial RSS check...")
        await hourly_rss_job()
        
        # Start Telegram bot
        logger.info("Starting Telegram bot...")
        bot = TelegramBot()
        await bot.start_polling()
        
        # Keep the application running
        logger.info("CodeNews is running. Press Ctrl+C to stop.")
        
        try:
            # Wait indefinitely
            await asyncio.Event().wait()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Shutting down...")
        finally:
            # Cleanup
            scheduler.shutdown()
            await bot.stop()
            logger.info("CodeNews stopped")
    
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
        sys.exit(1)
