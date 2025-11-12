"""
Machine learning engine for preference learning and content scoring
"""

import logging
from datetime import datetime
from collections import defaultdict
from src.config import Config
from src.database import get_db_session, Content, Feedback, Preference

logger = logging.getLogger(__name__)


class MLEngine:
    """Machine learning engine for personalization"""
    
    def __init__(self):
        self.learning_rate = Config.LEARNING_RATE
        self.min_feedback_count = Config.MIN_FEEDBACK_COUNT
    
    def extract_keywords(self, text):
        """Extract keywords from text (simple word extraction)"""
        if not text:
            return []
        
        # Simple keyword extraction - split by spaces and filter
        words = text.lower().split()
        
        # Filter out common words and short words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 've', 'is', 'are', 'was', 'were', 'be', 'been', 'being'}
        keywords = [word.strip('.,!?;:()[]{}') for word in words if len(word) > 3 and word not in stop_words]
        
        return keywords
    
    def update_preferences(self, content_id, sentiment):
        """Update user preferences based on feedback"""
        db = get_db_session()
        
        try:
            # Get content
            content = db.query(Content).filter_by(id=content_id).first()
            if not content:
                logger.warning(f"Content {content_id} not found")
                return
            
            # Extract keywords from content
            combined_text = f"{content.title} {content.summary}"
            keywords = self.extract_keywords(combined_text)
            
            # Update preference for each keyword
            for keyword in keywords:
                try:
                    preference = db.query(Preference).filter_by(keyword=keyword).first()
                    
                    if not preference:
                        # Create new preference
                        preference = Preference(
                            keyword=keyword,
                            category=content.category,
                            weight=0.0,
                            positive_count=0,
                            negative_count=0
                        )
                        db.add(preference)
                        db.flush()  # Flush to detect conflicts early
                    
                    # Update counts and weight
                    if sentiment == 'positive':
                        preference.positive_count += 1
                        preference.weight += self.learning_rate
                    elif sentiment == 'negative':
                        preference.negative_count += 1
                        preference.weight -= self.learning_rate
                    
                    # Clamp weight between -1.0 and 1.0
                    preference.weight = max(-1.0, min(1.0, preference.weight))
                    preference.last_updated = datetime.utcnow()
                
                except Exception as keyword_error:
                    # Handle race condition: keyword was inserted by another process
                    db.rollback()
                    logger.warning(f"Race condition for keyword '{keyword}': {keyword_error}")
                    
                    # Retry: query again and update
                    preference = db.query(Preference).filter_by(keyword=keyword).first()
                    if preference:
                        if sentiment == 'positive':
                            preference.positive_count += 1
                            preference.weight += self.learning_rate
                        elif sentiment == 'negative':
                            preference.negative_count += 1
                            preference.weight -= self.learning_rate
                        
                        preference.weight = max(-1.0, min(1.0, preference.weight))
                        preference.last_updated = datetime.utcnow()
            
            db.commit()
            logger.info(f"Updated preferences for {len(keywords)} keywords from content {content_id}")
        
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating preferences: {e}")
        finally:
            db.close()
    
    def calculate_content_score(self, content):
        """Calculate personalized score for content based on learned preferences"""
        db = get_db_session()
        
        try:
            # Extract keywords
            combined_text = f"{content.title} {content.summary}"
            keywords = self.extract_keywords(combined_text)
            
            if not keywords:
                return content.relevance_score
            
            # Get preferences for keywords
            preferences = db.query(Preference).filter(Preference.keyword.in_(keywords)).all()
            
            if not preferences:
                # No learned preferences yet, use base score
                return content.relevance_score
            
            # Calculate weighted score
            total_weight = 0.0
            keyword_count = 0
            
            for pref in preferences:
                # Only use preferences with minimum feedback
                if (pref.positive_count + pref.negative_count) >= self.min_feedback_count:
                    total_weight += pref.weight
                    keyword_count += 1
            
            if keyword_count == 0:
                return content.relevance_score
            
            # Average weight
            avg_weight = total_weight / keyword_count
            
            # Combine with base relevance score
            # Base score: 0.0-1.0, weight: -1.0 to 1.0
            # Final score: base * (1 + weight adjustment)
            adjustment = (1.0 + avg_weight) / 2.0  # Convert -1..1 to 0..1
            final_score = content.relevance_score * adjustment
            
            return max(0.0, min(1.0, final_score))
        
        finally:
            db.close()
    
    def rescore_unnotified_content(self):
        """Rescore all unnotified content based on current preferences"""
        db = get_db_session()
        
        try:
            content_list = db.query(Content).filter_by(notified=False).all()
            
            if not content_list:
                logger.info("No content to rescore")
                return
            
            logger.info(f"Rescoring {len(content_list)} items")
            
            for content in content_list:
                new_score = self.calculate_content_score(content)
                
                db_content = db.query(Content).filter_by(id=content.id).first()
                if db_content:
                    db_content.relevance_score = new_score
            
            db.commit()
            logger.info("Rescoring complete")
        
        finally:
            db.close()
    
    def get_top_preferences(self, limit=20):
        """Get top positive and negative preferences"""
        db = get_db_session()
        
        try:
            # Get top positive preferences
            positive = db.query(Preference)\
                .filter(Preference.weight > 0)\
                .order_by(Preference.weight.desc())\
                .limit(limit)\
                .all()
            
            # Get top negative preferences
            negative = db.query(Preference)\
                .filter(Preference.weight < 0)\
                .order_by(Preference.weight.asc())\
                .limit(limit)\
                .all()
            
            return {
                'positive': [(p.keyword, p.weight) for p in positive],
                'negative': [(p.keyword, p.weight) for p in negative]
            }
        
        finally:
            db.close()
    
    def get_preference_stats(self):
        """Get statistics about learned preferences"""
        db = get_db_session()
        
        try:
            total_prefs = db.query(Preference).count()
            positive_prefs = db.query(Preference).filter(Preference.weight > 0).count()
            negative_prefs = db.query(Preference).filter(Preference.weight < 0).count()
            
            total_feedback = db.query(Feedback).count()
            positive_feedback = db.query(Feedback).filter_by(sentiment='positive').count()
            negative_feedback = db.query(Feedback).filter_by(sentiment='negative').count()
            
            return {
                'total_preferences': total_prefs,
                'positive_preferences': positive_prefs,
                'negative_preferences': negative_prefs,
                'total_feedback': total_feedback,
                'positive_feedback': positive_feedback,
                'negative_feedback': negative_feedback
            }
        
        finally:
            db.close()


def update_preference_learning():
    """Standalone function to update preference learning"""
    engine = MLEngine()
    engine.rescore_unnotified_content()
