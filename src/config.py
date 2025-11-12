"""
Configuration management for CodeNews
"""

import os
import yaml
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Base paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
EXPORTS_DIR = BASE_DIR / "exports"

# Load YAML configuration
CONFIG_FILE = BASE_DIR / "config.yaml"
with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
    CONFIG = yaml.safe_load(f)

# Load RSS feeds
FEEDS_FILE = DATA_DIR / "feeds.json"

# Create feeds.json if it doesn't exist
if not FEEDS_FILE.exists():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    default_feeds = []
    with open(FEEDS_FILE, 'w', encoding='utf-8') as f:
        json.dump(default_feeds, f, indent=2, ensure_ascii=False)
    FEEDS = default_feeds
else:
    with open(FEEDS_FILE, 'r', encoding='utf-8') as f:
        FEEDS = json.load(f)


def _env_int(name, default):
    value = os.getenv(name)
    return int(value) if value is not None else default


def _env_float(name, default):
    value = os.getenv(name)
    return float(value) if value is not None else default


def _env_bool(name, default):
    value = os.getenv(name)
    if value is None:
        return default
    return str(value).lower() in {'1', 'true', 'yes', 'on'}


def _env_list(name, default):
    value = os.getenv(name)
    if value is None:
        return default
    return [item.strip() for item in value.split(',') if item.strip()]


class Config:
    """Application configuration"""
    
    # Telegram
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
    
    # Database
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///data/codenews.db')
    
    # OpenAI (optional)
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    
    # System
    TIMEZONE = os.getenv('TIMEZONE', 'Europe/Istanbul')
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    # RSS Monitoring
    RSS_CHECK_INTERVAL = _env_int('RSS_CHECK_INTERVAL_HOURS', CONFIG.get('rss_check_interval_hours', 3))
    MAX_ITEMS_PER_FEED = _env_int('MAX_ITEMS_PER_FEED', CONFIG.get('max_items_per_feed', 50))
    REQUEST_TIMEOUT = _env_int('REQUEST_TIMEOUT_SECONDS', CONFIG.get('request_timeout_seconds', 30))
    
    # Content Filtering
    KEYWORDS = _env_list('KEYWORDS', CONFIG.get('keywords', []))
    
    # Telegram
    MAX_NOTIFICATIONS_PER_HOUR = _env_int('MAX_NOTIFICATIONS_PER_HOUR', CONFIG.get('max_notifications_per_hour', 50))
    SUMMARY_MAX_LENGTH = _env_int('SUMMARY_MAX_LENGTH', CONFIG.get('summary_max_length', 300))
    TRANSLATE_SUMMARIES_TO_TURKISH = _env_bool('TRANSLATE_SUMMARIES_TO_TURKISH', CONFIG.get('translate_summaries_to_turkish', True))
    
    # Content Freshness
    MAX_ARTICLE_AGE_HOURS = _env_int('MAX_ARTICLE_AGE_HOURS', CONFIG.get('max_article_age_hours', 48))
    NEWS_KEYWORDS = _env_list('NEWS_KEYWORDS', CONFIG.get('news_keywords', []))
    
    # Personalization
    INITIAL_RELEVANCE_THRESHOLD = _env_float('INITIAL_RELEVANCE_THRESHOLD', CONFIG.get('initial_relevance_threshold', 0.1))
    LEARNING_RATE = _env_float('LEARNING_RATE', CONFIG.get('learning_rate', 0.1))
    MIN_FEEDBACK_COUNT = _env_int('MIN_FEEDBACK_COUNT', CONFIG.get('min_feedback_count', 5))
    
    # Blog Generation
    BLOG_SCHEDULE_DAY = _env_int('BLOG_SCHEDULE_DAY', CONFIG.get('blog_schedule_day', 6))
    BLOG_SCHEDULE_HOUR = _env_int('BLOG_SCHEDULE_HOUR', CONFIG.get('blog_schedule_hour', 6))
    BLOG_SCHEDULE_MINUTE = _env_int('BLOG_SCHEDULE_MINUTE', CONFIG.get('blog_schedule_minute', 0))
    BLOG_MIN_ITEMS = _env_int('BLOG_MIN_ITEMS', CONFIG.get('blog_min_items', 5))
    BLOG_MAX_ITEMS = _env_int('BLOG_MAX_ITEMS', CONFIG.get('blog_max_items', 15))
    TELEGRAPH_SHORT_NAME = os.getenv('TELEGRAPH_SHORT_NAME', CONFIG.get('telegraph_short_name', 'CodeNews'))
    TELEGRAPH_AUTHOR_NAME = os.getenv('TELEGRAPH_AUTHOR_NAME', CONFIG.get('telegraph_author_name', 'CodeNews Bot'))
    
    # Paths
    DATA_DIR = DATA_DIR
    LOGS_DIR = LOGS_DIR
    EXPORTS_DIR = EXPORTS_DIR
    
    @classmethod
    def get_enabled_feeds(cls):
        """Get list of enabled RSS feeds"""
        return [feed for feed in FEEDS if feed.get('enabled', True)]
    
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        errors = []
        
        if not cls.TELEGRAM_BOT_TOKEN:
            errors.append("TELEGRAM_BOT_TOKEN not set in .env")
        
        if not cls.TELEGRAM_CHAT_ID:
            errors.append("TELEGRAM_CHAT_ID not set in .env")
        
        if errors:
            raise ValueError(f"Configuration errors: {', '.join(errors)}")
        
        return True
