"""
Database models and session management for CodeNews
"""

import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from dotenv import load_dotenv

load_dotenv()

Base = declarative_base()


class Content(Base):
    """Store RSS feed content items"""
    __tablename__ = 'content'
    
    id = Column(Integer, primary_key=True)
    url = Column(String(500), unique=True, nullable=False, index=True)
    title = Column(String(500), nullable=False)
    summary = Column(Text)
    content = Column(Text)
    category = Column(String(50))  # 'ai' or 'software_dev'
    feed_name = Column(String(200))
    published_date = Column(DateTime)
    fetched_date = Column(DateTime, default=datetime.utcnow)
    notified = Column(Boolean, default=False)
    relevance_score = Column(Float, default=0.0)
    used_in_blog = Column(Boolean, default=False)  # Track if content was used in blog
    
    # Relationships
    feedback = relationship("Feedback", back_populates="content", uselist=False)
    

class Feedback(Base):
    """Store user feedback on content items"""
    __tablename__ = 'feedback'
    
    id = Column(Integer, primary_key=True)
    content_id = Column(Integer, ForeignKey('content.id'), nullable=False)
    sentiment = Column(String(20))  # 'positive', 'negative', 'neutral'
    feedback_text = Column(Text)
    feedback_date = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    content = relationship("Content", back_populates="feedback")


class Preference(Base):
    """Store learned user preferences"""
    __tablename__ = 'preferences'
    
    id = Column(Integer, primary_key=True)
    keyword = Column(String(200), unique=True, nullable=False, index=True)
    category = Column(String(50))
    weight = Column(Float, default=0.0)
    positive_count = Column(Integer, default=0)
    negative_count = Column(Integer, default=0)
    last_updated = Column(DateTime, default=datetime.utcnow)


class BlogPost(Base):
    """Track generated blog posts"""
    __tablename__ = 'blog_posts'
    
    id = Column(Integer, primary_key=True)
    filename = Column(String(200), unique=True, nullable=False)
    title = Column(String(500))
    generated_date = Column(DateTime, default=datetime.utcnow)
    content_ids = Column(Text)  # JSON array of content IDs used
    exported = Column(Boolean, default=False)


# Database initialization
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///data/codenews.db')
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_session():
    """Get a database session (direct access)"""
    return SessionLocal()
