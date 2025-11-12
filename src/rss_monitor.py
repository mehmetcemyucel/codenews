"""
RSS feed monitoring and content extraction
"""

import logging
import feedparser
import requests
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from src.config import Config
from src.database import get_db_session, Content

logger = logging.getLogger(__name__)


class RSSMonitor:
    """Monitor RSS feeds and extract new content"""
    
    def __init__(self):
        self.feeds = Config.get_enabled_feeds()
        self.timeout = Config.REQUEST_TIMEOUT
    
    def fetch_feed(self, feed_url, timeout=None):
        """Fetch and parse RSS feed"""
        timeout = timeout or self.timeout
        
        try:
            response = requests.get(feed_url, timeout=timeout)
            response.raise_for_status()
            feed = feedparser.parse(response.content)
            return feed
        except requests.RequestException as e:
            logger.error(f"Error fetching feed {feed_url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error parsing feed {feed_url}: {e}")
            return None
    
    def extract_content_data(self, entry, feed_info):
        """Extract relevant data from feed entry"""
        # Get URL
        url = entry.get('link', '')
        if not url:
            return None
        
        # Get title
        title = entry.get('title', 'No title')
        
        # Get summary/description
        summary = entry.get('summary', entry.get('description', ''))
        
        # Get full content if available
        content = ''
        if 'content' in entry:
            content = entry.content[0].get('value', '')
        elif 'description' in entry:
            content = entry.description
        
        # Get published date
        published_date = None
        if 'published_parsed' in entry and entry.published_parsed:
            published_date = datetime(*entry.published_parsed[:6])
        elif 'updated_parsed' in entry and entry.updated_parsed:
            published_date = datetime(*entry.updated_parsed[:6])
        
        return {
            'url': url,
            'title': title,
            'summary': summary,
            'content': content,
            'category': feed_info['category'],
            'feed_name': feed_info['name'],
            'published_date': published_date
        }
    
    def check_feeds(self):
        """Check all enabled feeds for new content"""
        db = get_db_session()
        new_items = []
        
        try:
            for feed_info in self.feeds:
                logger.info(f"Checking feed: {feed_info['name']}")
                
                feed = self.fetch_feed(feed_info['url'])
                if not feed or not feed.entries:
                    logger.warning(f"No entries found in feed: {feed_info['name']}")
                    continue
                
                # Process entries (limit to max items)
                entries = feed.entries[:Config.MAX_ITEMS_PER_FEED]
                
                for entry in entries:
                    content_data = self.extract_content_data(entry, feed_info)
                    
                    if not content_data:
                        continue
                    
                    # Check if content already exists
                    existing = db.query(Content).filter_by(url=content_data['url']).first()
                    if existing:
                        continue
                    
                    # Create new content entry
                    content = Content(**content_data)
                    
                    try:
                        db.add(content)
                        db.commit()
                        db.refresh(content)
                        new_items.append(content)
                        logger.info(f"New content added: {content.title[:50]}")
                    except IntegrityError:
                        db.rollback()
                        logger.debug(f"Content already exists: {content_data['url']}")
                    except Exception as e:
                        db.rollback()
                        logger.error(f"Error saving content: {e}")
            
            logger.info(f"RSS check complete. New items: {len(new_items)}")
            return new_items
        
        finally:
            db.close()
    
    def get_unnotified_content(self):
        """Get content that hasn't been notified yet"""
        db = get_db_session()
        try:
            content = db.query(Content).filter_by(notified=False).all()
            return content
        finally:
            db.close()
    
    def mark_as_notified(self, content_id):
        """Mark content as notified"""
        db = get_db_session()
        try:
            content = db.query(Content).filter_by(id=content_id).first()
            if content:
                content.notified = True
                db.commit()
                return True
            return False
        finally:
            db.close()


def run_rss_check():
    """Standalone function to run RSS check"""
    monitor = RSSMonitor()
    new_items = monitor.check_feeds()
    return new_items
