"""
Weekly digest generation for Telegram Telegraph posts
"""

import logging
import json
from datetime import datetime
from pathlib import Path
from telegraph import Telegraph
from src.config import Config
from src.database import get_db_session, Content, Feedback, BlogPost

logger = logging.getLogger(__name__)


class BlogGenerator:
    """Generate curated weekly digests and publish them to Telegraph"""
    
    def __init__(self):
        self.min_items = Config.BLOG_MIN_ITEMS
        self.max_items = Config.BLOG_MAX_ITEMS
        self.telegraph_short_name = Config.TELEGRAPH_SHORT_NAME
        self.telegraph_author_name = Config.TELEGRAPH_AUTHOR_NAME
     
    def select_content_for_blog(self):
        """Select best content items for blog post based on feedback and scores"""
        db = get_db_session()
        
        try:
            # Get content with positive feedback that hasn't been used in blog yet
            # Prioritize recent content but don't exclude older ones
            positive_content = db.query(Content)\
                .join(Feedback, Content.id == Feedback.content_id)\
                .filter(Feedback.sentiment == 'positive')\
                .filter(Content.used_in_blog == False)\
                .order_by(Content.fetched_date.desc())\
                .limit(self.max_items)\
                .all()
            
            logger.info(f"Found {len(positive_content)} items with positive feedback")
            
            # If not enough, add high-scoring content from recent days
            if len(positive_content) < self.min_items:
                from datetime import timedelta
                week_ago = datetime.utcnow() - timedelta(days=14)  # Extended to 2 weeks
                
                additional_needed = self.max_items - len(positive_content)
                
                # Get IDs of already selected content
                selected_ids = [c.id for c in positive_content]
                
                high_scoring = db.query(Content)\
                    .filter(Content.fetched_date >= week_ago)\
                    .filter(Content.relevance_score >= 0.3)\
                    .filter(~Content.id.in_(selected_ids) if selected_ids else True)\
                    .order_by(Content.relevance_score.desc())\
                    .limit(additional_needed)\
                    .all()
                
                positive_content.extend(high_scoring)
                logger.info(f"Added {len(high_scoring)} high-scoring items")
            
            logger.info(f"Selected {len(positive_content)} items for blog post")
            return positive_content
        
        finally:
            db.close()
    
    def generate_blog_title(self, content_list):
        """Generate blog post title"""
        week_num = datetime.now().isocalendar()[1]
        year = datetime.now().year
        return f"Code Report - Hafta {week_num}, {year}"
    
    def slugify(self, text):
        """Convert text to URL-friendly slug for anchors"""
        import re
        # Remove special characters, convert to lowercase
        text = text.lower()
        text = re.sub(r'[^\w\s-]', '', text)
        text = re.sub(r'[-\s]+', '-', text)
        return text[:50]  # Limit length
    
    def generate_headline_and_summary(self, content):
        """Generate both headline and detailed summary in a single LLM call"""
        from src.content_filter import ContentFilter
        filter = ContentFilter()
        
        # Use LLM to generate both headline and summary at once
        if filter.openai_client:
            try:
                text_to_summarize = f"Başlık: {content.title}\n\n"
                if content.summary:
                    text_to_summarize += f"Özet: {filter.clean_text(content.summary)}\n\n"
                if content.content:
                    text_to_summarize += f"İçerik: {filter.clean_text(content.content)[:3000]}"
                
                response = filter.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": """Sen Telegram için haftalık teknoloji özeti hazırlayan bir editörsün. Her haber için kısa bir başlık ve tek sayfada okunabilecek bir özet yaz.

ÇIKTI FORMATI:
İlk satır: Kısa, çarpıcı başlık (maks. 90 karakter)
---AYRAC---
Sonraki satırlar: 1-2 paragraf Türkçe özet (her paragraf 2-3 cümle)

KURALLAR:
- Bağlamı koru, gereksiz jargon ekleme
- Okuyucuyu Telegraph sayfasında hızlıca bilgilendirecek netlikte yaz
- Liste veya emoji kullanma, sadece düz metin yaz
- Eğer rakam/istatistik varsa vurgula
"""
                        },
                        {
                            "role": "user",
                            "content": text_to_summarize
                        }
                    ],
                    max_tokens=450,
                    temperature=0.7
                )
                
                full_text = response.choices[0].message.content.strip()
                
                # Split by separator
                if "---AYRAC---" in full_text:
                    parts = full_text.split("---AYRAC---")
                    headline = parts[0].strip()
                    summary = parts[1].strip() if len(parts) > 1 else content.title
                else:
                    # Fallback: first line is headline, rest is summary
                    lines = full_text.split('\n', 1)
                    headline = lines[0].strip()
                    summary = lines[1].strip() if len(lines) > 1 else content.title
                
                return headline, summary
                
            except Exception as e:
                logger.error(f"Error generating headline and summary: {e}")
        
        # Fallback
        headline = content.title[:100] if content.title else "Haber"
        summary = filter.clean_text(content.summary) if content.summary else content.title
        return headline, summary
    
    def generate_content_section(self, content_list):
        """Generate the main content section of the digest"""
        from src.content_filter import ContentFilter
        filter = ContentFilter()
        
        # Group by category label for flexible sections
        grouped_items = {}
        for content in content_list:
            category_key = content.category if content.category else 'general'
            grouped_items.setdefault(category_key, []).append(content)
        
        def category_label(key):
            if key == 'ai':
                return "Yapay Zeka"
            if key == 'software_dev':
                return "Yazılım Geliştirme"
            return key.replace('_', ' ').title()
        
        def category_emoji(key):
            if key == 'ai':
                return "🤖"
            if key == 'software_dev':
                return "💻"
            return "🗞️"
        
        # Pre-generate all headlines and summaries (one LLM call per item)
        logger.info("Generating headlines and summaries (optimized)...")
        headlines_cache = {}
        summaries_cache = {}
        
        for item in content_list:
            headline, summary = self.generate_headline_and_summary(item)
            headlines_cache[item.id] = headline
            summaries_cache[item.id] = summary
        
        content_md = ""
        
        # Generate TOC (Table of Contents)
        content_md += "## 📋 İçindekiler\n\n"
        for key, items in grouped_items.items():
            label = category_label(key)
            emoji = category_emoji(key)
            content_md += f"**{emoji} {label}**\n\n"
            for idx, item in enumerate(items, 1):
                headline = headlines_cache[item.id]
                slug = self.slugify(headline)
                content_md += f"{idx}. [{headline}](#{slug})\n"
            content_md += "\n"
        
        content_md += "---\n\n"
        
        # Detailed sections
        for key, items in grouped_items.items():
            label = category_label(key)
            emoji = category_emoji(key)
            content_md += f"## {emoji} {label}\n\n"
            
            for item in items:
                headline = headlines_cache[item.id]
                slug = self.slugify(headline)
                detailed_summary = summaries_cache[item.id]
                
                content_md += f"### <a id=\"{slug}\"></a>{headline}\n\n"
                content_md += f"{detailed_summary}\n\n"
                content_md += f"**🔗 Kaynak:** [{item.feed_name}]({item.url})\n\n"
                content_md += "---\n\n"
        
        # Footer
        content_md += "\n## 💡 Hakkında\n\n"
        content_md += "Bu özet, CodeNews botu tarafından otomatik olarak oluşturulmuştur. "
        content_md += "AI ve yazılım geliştirme alanındaki en önemli haberleri her hafta derleyerek sizlerle paylaşıyoruz.\n\n"
        content_md += "*Not: Özetler ve yorumlar yapay zeka destekli araçlar kullanılarak oluşturulmuştur. "
        content_md += "Detaylı bilgi için kaynak linkleri ziyaret edebilirsiniz.*\n"
        
        return content_md

    def build_digest_package(self):
        """Prepare digest payload with markdown and Telegraph-ready HTML"""
        content_list = self.select_content_for_blog()
        
        if len(content_list) < self.min_items:
            logger.warning(
                f"Not enough content for digest. Need {self.min_items}, have {len(content_list)}"
            )
            return None
        
        content_md = self.generate_content_section(content_list)
        title = self.generate_blog_title(content_list)
        html_content = self.convert_markdown_to_telegraph_html(content_md)
        
        return {
            "title": title,
            "markdown": content_md,
            "html_content": html_content,
            "content_ids": [c.id for c in content_list]
        }
    
    def convert_markdown_to_telegraph_html(self, content_md):
        """Convert markdown content to Telegraph-compatible HTML
        
        Telegraph supports limited HTML tags:
        a, aside, b, blockquote, br, code, em, figcaption, figure, 
        h3, h4, hr, i, iframe, img, li, ol, p, pre, s, strong, u, ul, video
        
        Note: h1, h2 are NOT supported!
        """
        import re
        
        content_md = re.sub(r'^---.*?---\n', '', content_md, flags=re.DOTALL)
        
        html = content_md
        
        # Convert headers (Telegraph only supports h3 and h4)
        html = re.sub(r'####\s+(.+)', r'<h4>\1</h4>', html)
        html = re.sub(r'###\s+(.+)', r'<h3>\1</h3>', html)
        html = re.sub(r'##\s+(.+)', r'<h3>\1</h3>', html)  # h2 -> h3
        html = re.sub(r'#\s+(.+)', r'<h3>\1</h3>', html)   # h1 -> h3
        
        # Convert bold and italic
        html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
        html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)
        
        # Convert links - handle both markdown links and anchor tags
        html = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', html)
        
        # Remove anchor id tags (Telegraph doesn't support them)
        html = re.sub(r'<a id="[^"]+"></a>', '', html)
        
        # Convert horizontal rules
        html = re.sub(r'^---\s*$', '<hr>', html, flags=re.MULTILINE)
        
        # Convert paragraphs - split by double newlines
        paragraphs = html.split('\n\n')
        formatted_paragraphs = []
        
        for para in paragraphs:
            para = para.strip()
            if para and not para.startswith('<h') and not para.startswith('<hr>'):
                # Skip if already wrapped in tags
                if not para.startswith('<'):
                    formatted_paragraphs.append(f'<p>{para}</p>')
                else:
                    formatted_paragraphs.append(para)
            elif para:
                formatted_paragraphs.append(para)
        
        html = '\n'.join(formatted_paragraphs)
        
        # Clean up multiple newlines
        html = re.sub(r'\n{3,}', '\n\n', html)
        
        return html
    
    def upload_to_telegraph(self, title, html_content):
        """Upload digest to Telegraph and return URL"""
        try:
            telegraph = Telegraph()
            telegraph.create_account(
                short_name=self.telegraph_short_name,
                author_name=self.telegraph_author_name
            )
            
            response = telegraph.create_page(
                title=title,
                html_content=html_content,
                author_name=self.telegraph_author_name
            )
            
            telegraph_url = f"https://telegra.ph/{response['path']}"
            logger.info(f"Digest uploaded to Telegraph: {telegraph_url}")
            return telegraph_url
        
        except Exception as e:
            logger.error(f"Error uploading to Telegraph: {e}")
            return None


    def save_digest_record(self, digest_title, content_ids, telegraph_url):
        """Persist digest metadata to the database (for history)"""
        db = get_db_session()
        try:
            content_ids_json = json.dumps(content_ids)
            telegraph_path = telegraph_url.rsplit('/', 1)[-1]
            
            existing = db.query(BlogPost).filter_by(filename=telegraph_path).first()
            if existing:
                existing.title = digest_title
                existing.content_ids = content_ids_json
                existing.exported = True
                existing.generated_date = datetime.utcnow()
            else:
                blog_post = BlogPost(
                    filename=telegraph_path,
                    title=digest_title,
                    content_ids=content_ids_json,
                    exported=True
                )
                db.add(blog_post)
            
            db.commit()
        except Exception as e:
            db.rollback()
            logger.warning(f"Could not save digest record: {e}")
        finally:
            db.close()

    def publish_digest(self):
        """Build digest package and publish it to Telegraph"""
        digest = self.build_digest_package()
        if not digest:
            return None
        
        telegraph_url = self.upload_to_telegraph(
            title=digest["title"],
            html_content=digest["html_content"]
        )
        
        if not telegraph_url:
            return None
        
        digest["telegraph_url"] = telegraph_url
        digest["item_count"] = len(digest["content_ids"])
        self.save_digest_record(digest["title"], digest["content_ids"], telegraph_url)
        return digest

def generate_weekly_blog():
    """Generate and publish weekly digest to Telegraph"""
    generator = BlogGenerator()
    return generator.publish_digest()


def mark_content_as_used(content_ids=None):
    """Mark digest content as used and clear their feedback"""
    generator = BlogGenerator()
    db = get_db_session()
    
    try:
        if content_ids is None:
            content_list = generator.select_content_for_blog()
            target_ids = [content.id for content in content_list]
        else:
            target_ids = content_ids
        
        if not target_ids:
            logger.info("No content IDs provided to mark as used.")
            return
        
        # Fetch content within the same session to ensure persistence
        items = db.query(Content).filter(Content.id.in_(target_ids)).all()
        
        for item in items:
            item.used_in_blog = True
            feedback = db.query(Feedback).filter_by(content_id=item.id).first()
            if feedback:
                db.delete(feedback)
        
        db.commit()
        logger.info(f"Marked {len(items)} items as used and removed their feedback.")
        
    except Exception as e:
        logger.error(f"Error marking content as used: {e}")
        db.rollback()
    finally:
        db.close()
