"""
Content filtering, categorization, and summarization
"""

import logging
import re
import os
from datetime import datetime, timedelta
from src.config import Config
from src.database import get_db_session, Content

# Try to import OpenAI for LLM summarization
try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

logger = logging.getLogger(__name__)


class ContentFilter:
    """Filter and categorize content based on keywords"""
    
    def __init__(self):
        self.keywords = [kw.lower() for kw in Config.KEYWORDS]
        self.news_keywords = [kw.lower() for kw in Config.NEWS_KEYWORDS]
        self.max_age = timedelta(hours=Config.MAX_ARTICLE_AGE_HOURS)
        self.translate_to_turkish = Config.TRANSLATE_SUMMARIES_TO_TURKISH
        
        # Initialize OpenAI client if API key is available
        self.openai_client = None
        if HAS_OPENAI and Config.OPENAI_API_KEY:
            self.openai_client = OpenAI(api_key=Config.OPENAI_API_KEY)
            logger.info("OpenAI client initialized for LLM summarization")
    
    def calculate_category_score(self, text, keywords):
        """Calculate relevance score for a category based on keyword matches"""
        if not text:
            return 0.0
        
        text_lower = text.lower()
        matches = sum(1 for keyword in keywords if keyword in text_lower)
        
        # Normalize score (0.0 to 1.0)
        max_possible = len(keywords)
        if max_possible == 0:
            return 0.0
        
        return min(matches / max_possible * 2.0, 1.0)  # Scale up matches
    
    def categorize_content(self, content):
        """Calculate relevance score using unified keyword list"""
        combined_text = f"{content.title} {content.summary} {content.content}"
        relevance_score = self.calculate_category_score(combined_text, self.keywords)
        
        if relevance_score > 0:
            # Preserve feed category metadata if available
            category = content.category or 'tech'
            return category, relevance_score
        
        return None, 0.0
    
    def generate_summary_with_llm(self, content):
        """Generate Turkish summary using LLM"""
        if not self.openai_client:
            return None
        
        try:
            # Prepare content for summarization
            text_to_summarize = f"Başlık: {content.title}\n\n"
            
            if content.summary:
                text_to_summarize += f"Özet: {self.clean_text(content.summary)}\n\n"
            
            if content.content:
                # Limit content length to avoid token limits
                cleaned_content = self.clean_text(content.content)[:2000]
                text_to_summarize += f"İçerik: {cleaned_content}"
            
            # Call OpenAI API
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",  # Cheaper and faster model
                messages=[
                    {
                        "role": "system",
                        "content": """Sen teknik haber başlık yazarısın. Verilen haberi Türkçe olarak ÇOK KISA ve ETKİLİ bir başlık haline getir.

KURALLAR:
- Maksimum 10-12 kelime kullan
- Sayıları ve büyük rakamları vurgula (örn: "1 trilyon $", "30.000 kişi", "5 trilyon $")
- Şirket/ürün isimlerini koru
- Etkili ve dikkat çekici ol
- Nokta ile bitir
- Gereksiz kelimeleri atla, sadece önemli bilgiyi ver

ÖRNEK FORMAT:
- OpenAI'nin 1 trilyon $ halka arz iddiası.
- Amazon'un 30.000 kişilik dev işten çıkarması.
- Nvidia, 5 trilyon $ değerlemeyle tarih yazdı.

Sadece başlığı yaz, başka açıklama ekleme."""
                    },
                    {
                        "role": "user",
                        "content": text_to_summarize
                    }
                ],
                max_tokens=80,
                temperature=0.5
            )
            
            summary = response.choices[0].message.content.strip()
            logger.info(f"LLM summary generated for: {content.title[:50]}")
            return summary
            
        except Exception as e:
            logger.error(f"Error generating LLM summary: {e}")
            return None
    
    def generate_summary(self, content, max_length=None):
        """Generate a one-sentence summary of the content"""
        max_length = max_length or Config.SUMMARY_MAX_LENGTH
        
        # Try LLM summarization first if available
        if self.openai_client and self.translate_to_turkish:
            llm_summary = self.generate_summary_with_llm(content)
            if llm_summary:
                return self.truncate_text(llm_summary, max_length)
        
        # Fallback to simple extraction
        summary = None
        
        # Try to use existing summary first
        if content.summary:
            summary = self.clean_text(content.summary)
        
        # Fall back to title + first sentence of content
        if not summary and content.content:
            first_sentence = self.extract_first_sentence(content.content)
            if first_sentence:
                summary = first_sentence
        
        # Last resort: just use title
        if not summary:
            summary = content.title
        
        # Simple translation if LLM not available
        if self.translate_to_turkish and summary:
            summary = self.translate_to_turkish_text(summary)
        
        return self.truncate_text(summary, max_length)
    
    def clean_text(self, text):
        """Clean HTML tags and extra whitespace from text"""
        if not text:
            return ""
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        # Decode HTML entities
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&quot;', '"')
        
        return text.strip()
    
    def extract_first_sentence(self, text):
        """Extract the first sentence from text"""
        text = self.clean_text(text)
        
        # Split by sentence ending punctuation
        sentences = re.split(r'[.!?]\s+', text)
        
        if sentences:
            return sentences[0]
        
        return text
    
    def truncate_text(self, text, max_length):
        """Truncate text to max length, ending at word boundary"""
        if len(text) <= max_length:
            return text
        
        # Find last space before max_length
        truncated = text[:max_length]
        last_space = truncated.rfind(' ')
        
        if last_space > 0:
            truncated = truncated[:last_space]
        
        return truncated + '...'
    
    def is_news_content(self, content):
        """Check if content is actual news (not tutorial, guide, etc.)"""
        combined_text = f"{content.title} {content.summary}".lower()
        
        # Check for news keywords (more lenient - just a bonus, not required)
        has_news_indicator = any(keyword in combined_text for keyword in self.news_keywords)
        
        # Be more lenient - if it has news keywords great, otherwise still allow it
        # Only filter out obvious tutorials/guides
        tutorial_keywords = ['tutorial', 'guide', 'how to', 'step by step', 'nasıl', 'rehber']
        is_tutorial = any(kw in combined_text for kw in tutorial_keywords)
        
        return has_news_indicator or not is_tutorial
    
    def is_fresh_content(self, content):
        """Check if content is recent enough"""
        if not content.published_date:
            # If no date, allow it (assume it's recent)
            return True
        
        age = datetime.utcnow() - content.published_date
        return age <= self.max_age
    
    def translate_to_turkish_text(self, text):
        """Simple translation helper - in production use a translation API"""
        # Simple keyword replacements for common phrases
        translations = {
            'announces': 'duyurdu',
            'releases': 'yayınladı',
            'launches': 'başlattı',
            'introduces': 'tanıttı',
            'new': 'yeni',
            'artificial intelligence': 'yapay zeka',
            'machine learning': 'makine öğrenmesi',
            'breakthrough': 'çığır açan gelişme',
            'researchers': 'araştırmacılar',
            'develops': 'geliştirdi',
            'achieves': 'başardı'
        }
        
        result = text
        for eng, tr in translations.items():
            result = result.replace(eng, tr)
        
        return result
    
    def filter_and_score_content(self, content_list):
        """Filter content and assign relevance scores"""
        filtered = []
        
        for content in content_list:
            # Check if it's actually news
            if not self.is_news_content(content):
                logger.debug(f"Filtered out (not news): {content.title[:50]}")
                continue
            
            # Check if it's fresh enough
            if not self.is_fresh_content(content):
                logger.debug(f"Filtered out (too old): {content.title[:50]}")
                continue
            
            # Categorize and score
            category, score = self.categorize_content(content)
            
            if category and score >= Config.INITIAL_RELEVANCE_THRESHOLD:
                # Update content with category and score
                content.category = category
                content.relevance_score = score
                filtered.append(content)
            else:
                logger.debug(f"Filtered out (low score): {content.title[:50]} (score: {score})")
        
        return filtered
    
    def process_new_content(self):
        """Process all unnotified content: categorize and score
        
        Returns: List of dictionaries with content data (to avoid session issues)
        """
        db = get_db_session()
        
        try:
            # Get unnotified content
            content_list = db.query(Content).filter_by(notified=False).all()
            
            if not content_list:
                logger.info("No new content to process")
                return []
            
            logger.info(f"Processing {len(content_list)} new items")
            
            # Filter and score
            filtered = self.filter_and_score_content(content_list)
            
            # Update database with scores and extract data
            filtered_data = []
            for content in filtered:
                db_content = db.query(Content).filter_by(id=content.id).first()
                if db_content:
                    db_content.category = content.category
                    db_content.relevance_score = content.relevance_score
                    
                    # Extract data while session is still active
                    filtered_data.append({
                        'id': db_content.id,
                        'title': db_content.title,
                        'summary': db_content.summary,
                        'content': db_content.content,
                        'category': db_content.category,
                        'relevance_score': db_content.relevance_score,
                        'url': db_content.url
                    })
            
            db.commit()
            
            logger.info(f"Processed {len(filtered_data)} relevant items")
            return filtered_data
        
        finally:
            db.close()


def filter_content():
    """Standalone function to filter content"""
    filter = ContentFilter()
    return filter.process_new_content()
