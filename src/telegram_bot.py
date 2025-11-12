"""
Telegram bot integration for notifications and feedback collection
"""

import logging
import asyncio
import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from src.config import Config
from src.database import get_db_session, Content, Feedback
from src.content_filter import ContentFilter
from src.ml_engine import MLEngine

logger = logging.getLogger(__name__)

FEEDS_FILE = "data/feeds.json"


class TelegramBot:
    """Telegram bot for content notifications and feedback"""
    
    def __init__(self):
        self.bot_token = Config.TELEGRAM_BOT_TOKEN
        self.chat_id = Config.TELEGRAM_CHAT_ID
        self.filter = ContentFilter()
        self.ml_engine = MLEngine()
        self.app = None
    
    async def send_notification(self, content):
        """Send notification for a single content item"""
        if not self.app:
            return False
        
        try:
            # Generate concise summary
            summary = self.filter.generate_summary(content)
            
            # Determine category emoji and label dynamically
            category_map = {
                "ai": ("🤖", "AI"),
                "software_dev": ("💻", "Dev")
            }
            category_emoji, category_label = category_map.get(
                content.category,
                ("🗞️", (content.category or "Tech").title())
            )
            
            # Create compact message (plain text to avoid parsing issues)
            message = f"{category_emoji} {category_label} | {summary}\n\n🔗 {content.url}"
            
            # Create inline keyboard for feedback
            keyboard = [
                [
                    InlineKeyboardButton("👍 İlginç", callback_data=f"positive_{content.id}"),
                    InlineKeyboardButton("👎 İlgisiz", callback_data=f"negative_{content.id}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Send message without parse_mode to avoid Markdown issues
            await self.app.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                reply_markup=reply_markup,
                disable_web_page_preview=True
            )
            
            logger.info(f"Notification sent for: {content.title[:50]}")
            return True
        
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
            return False
    
    async def handle_feedback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle feedback button clicks"""
        query = update.callback_query
        await query.answer()
        
        try:
            # Parse callback data
            data_parts = query.data.split('_')
            sentiment = data_parts[0]  # 'positive' or 'negative'
            content_id = int(data_parts[1])
            
            # Store feedback
            db = get_db_session()
            try:
                # Check if feedback already exists
                existing_feedback = db.query(Feedback).filter_by(content_id=content_id).first()
                
                if existing_feedback:
                    # Update existing feedback
                    existing_feedback.sentiment = sentiment
                    logger.info(f"Updated feedback for content {content_id}: {sentiment}")
                else:
                    # Create new feedback
                    feedback = Feedback(
                        content_id=content_id,
                        sentiment=sentiment
                    )
                    db.add(feedback)
                    logger.info(f"Saved feedback for content {content_id}: {sentiment}")
                
                db.commit()
                
                # Update ML model
                self.ml_engine.update_preferences(content_id, sentiment)
                
                # Update message to show feedback received
                sentiment_emoji = "✅ İlginç olarak işaretlendi" if sentiment == "positive" else "❌ İlgisiz olarak işaretlendi"
                await query.edit_message_reply_markup(reply_markup=None)
                await query.message.reply_text(sentiment_emoji)
            
            finally:
                db.close()
        
        except Exception as e:
            logger.error(f"Error handling feedback: {e}")
            await query.message.reply_text("Geri bildirim kaydedilirken hata oluştu.")
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        await update.message.reply_text(
            "**CodeNews Bot Yardım**\n\n"
            "Bot, RSS kaynaklarından teknik haberleri izler, Telegram'da özelleştirilmiş bildirimler ve haftalık Telegraph blog özetleri paylaşır.\n\n"
            "**Temel Komutlar:**\n"
            "/start - Bu yardım mesajı\n"
            "/help - Bu yardım mesajı\n"
            "/stats - İstatistikleri görüntüle\n"
            "/trg - Manuel haber taraması\n"
            "/blog - Haftalık özeti oluştur ve içerikleri işaretle\n"
            "/testblog - Haftalık özeti oluştur (işaretleme yapmadan)\n"
            "/list - Beğenilen haberlerin listesi\n\n"
            "**RSS Feed Yönetimi:**\n"
            "/feeds - Feed listesini göster\n"
            "/addfeed <isim> <url> <kategori> - Feed ekle\n"
            "/removefeed <numara> - Feed sil\n"
            "/togglefeed <numara> - Feed aktif/pasif\n\n"
            "**Geri Bildirim:**\n"
            "Bildirimlere 👍/👎 ile tepki verin",
            parse_mode='Markdown'
        )
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command"""
        db = get_db_session()
        try:
            total_content = db.query(Content).count()
            notified_content = db.query(Content).filter_by(notified=True).count()
            total_feedback = db.query(Feedback).count()
            positive_feedback = db.query(Feedback).filter_by(sentiment='positive').count()
            
            stats = (
                f"📊 **İstatistikler**\n\n"
                f"Toplam içerik: {total_content}\n"
                f"Bildirim gönderilen: {notified_content}\n"
                f"Toplam geri bildirim: {total_feedback}\n"
                f"Olumlu geri bildirim: {positive_feedback}\n"
            )
            
            await update.message.reply_text(stats, parse_mode='Markdown')
        finally:
            db.close()
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        await update.message.reply_text(
            "**CodeNews Bot Yardım**\n\n"
            "Bot, RSS kaynaklarından teknik haberleri izler, Telegram bildirimleri gönderir ve Telegraph üzerinden haftalık özetler paylaşır.\n\n"
            "**Temel Komutlar:**\n"
            "/start - Bu yardım mesajı\n"
            "/help - Bu yardım mesajı\n"
            "/stats - İstatistikleri görüntüle\n"
            "/trg - Manuel haber taraması\n"
            "/blog - Haftalık özeti oluştur ve içerikleri işaretle\n"
            "/testblog - Haftalık özeti oluştur (işaretleme yapmadan)\n"
            "/list - Beğenilen haberlerin listesi\n\n"
            "**RSS Feed Yönetimi:**\n"
            "/feeds - Feed listesini göster\n"
            "/addfeed <isim> <url> <kategori> - Feed ekle\n"
            "/removefeed <numara> - Feed sil\n"
            "/togglefeed <numara> - Feed aktif/pasif\n\n"
            "**Geri Bildirim:**\n"
            "Bildirimlere 👍/👎 ile tepki verin",
            parse_mode='Markdown'
        )
    
    async def feeds_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /feeds command - List all RSS feeds"""
        try:
            if not os.path.exists(FEEDS_FILE):
                await update.message.reply_text("❌ RSS feed dosyası bulunamadı.")
                return
            
            with open(FEEDS_FILE, 'r', encoding='utf-8') as f:
                feeds = json.load(f)
            
            if not feeds:
                await update.message.reply_text("ℹ️ Henüz RSS feed eklenmemiş.")
                return
            
            message = "📡 RSS Feed Listesi\n\n"
            for i, feed in enumerate(feeds, 1):
                status = "✅" if feed.get('enabled', True) else "❌"
                category = feed.get('category', 'unknown')
                url_preview = feed['url'][:50] + "..." if len(feed['url']) > 50 else feed['url']
                message += f"{i}. {status} {feed['name']}\n"
                message += f"   └─ URL: {url_preview}\n"
                message += f"   └─ Kategori: {category}\n\n"
            
            message += f"Toplam: {len(feeds)} feed\n\n"
            message += "Komutlar:\n"
            message += "/addfeed <isim> <url> <kategori> - Feed ekle\n"
            message += "/removefeed <numara> - Feed sil\n"
            message += "/togglefeed <numara> - Feed aktif/pasif"
            
            await update.message.reply_text(message)
            
        except Exception as e:
            logger.error(f"Error in feeds command: {e}")
            await update.message.reply_text(f"❌ Hata: {str(e)}")
    
    async def addfeed_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /addfeed command - Add new RSS feed
        Usage: /addfeed <name> <url> <category>
        Example: /addfeed "TechCrunch AI" https://techcrunch.com/feed/ ai
        """
        try:
            if len(context.args) < 3:
                await update.message.reply_text(
                    "❌ Kullanım: `/addfeed <isim> <url> <kategori>`\n\n"
                    "Örnek:\n"
                    "`/addfeed \"TechCrunch AI\" https://techcrunch.com/feed/ ai`\n\n"
                    "Kategori etiketi serbesttir (örn: ai, devops, security).",
                    parse_mode='Markdown'
                )
                return
            
            # Parse arguments
            name = context.args[0]
            url = context.args[1]
            category = context.args[2] if len(context.args) > 2 else 'ai'
            
            # Load existing feeds
            feeds = []
            if os.path.exists(FEEDS_FILE):
                with open(FEEDS_FILE, 'r', encoding='utf-8') as f:
                    feeds = json.load(f)
            
            # Check for duplicate URL
            if any(f['url'] == url for f in feeds):
                await update.message.reply_text("❌ Bu URL zaten ekli!")
                return
            
            # Add new feed
            new_feed = {
                "name": name,
                "url": url,
                "category": category,
                "enabled": True
            }
            feeds.append(new_feed)
            
            # Save to file
            with open(FEEDS_FILE, 'w', encoding='utf-8') as f:
                json.dump(feeds, f, indent=2, ensure_ascii=False)
            
            await update.message.reply_text(
                f"✅ Feed eklendi!\n\n"
                f"**{name}**\n"
                f"URL: {url}\n"
                f"Kategori: {category}\n\n"
                f"Toplam feed sayısı: {len(feeds)}"
            )
            logger.info(f"Added RSS feed: {name} ({url})")
            
        except Exception as e:
            logger.error(f"Error in addfeed command: {e}")
            await update.message.reply_text(f"❌ Hata: {str(e)}")
    
    async def removefeed_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /removefeed command - Remove RSS feed
        Usage: /removefeed <number>
        """
        try:
            if len(context.args) < 1:
                await update.message.reply_text(
                    "❌ Kullanım: `/removefeed <numara>`\n\n"
                    "Feed numarasını görmek için /feeds komutunu kullanın.",
                    parse_mode='Markdown'
                )
                return
            
            try:
                index = int(context.args[0]) - 1
            except ValueError:
                await update.message.reply_text("❌ Geçersiz numara!")
                return
            
            # Load feeds
            if not os.path.exists(FEEDS_FILE):
                await update.message.reply_text("❌ RSS feed dosyası bulunamadı.")
                return
            
            with open(FEEDS_FILE, 'r', encoding='utf-8') as f:
                feeds = json.load(f)
            
            if index < 0 or index >= len(feeds):
                await update.message.reply_text(
                    f"❌ Geçersiz numara! (1-{len(feeds)} arası olmalı)"
                )
                return
            
            # Remove feed
            removed_feed = feeds.pop(index)
            
            # Save
            with open(FEEDS_FILE, 'w', encoding='utf-8') as f:
                json.dump(feeds, f, indent=2, ensure_ascii=False)
            
            await update.message.reply_text(
                f"✅ Feed silindi!\n\n"
                f"**{removed_feed['name']}**\n"
                f"URL: {removed_feed['url']}\n\n"
                f"Kalan feed sayısı: {len(feeds)}"
            )
            logger.info(f"Removed RSS feed: {removed_feed['name']}")
            
        except Exception as e:
            logger.error(f"Error in removefeed command: {e}")
            await update.message.reply_text(f"❌ Hata: {str(e)}")
    
    async def togglefeed_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /togglefeed command - Toggle feed enabled/disabled
        Usage: /togglefeed <number>
        """
        try:
            if len(context.args) < 1:
                await update.message.reply_text(
                    "❌ Kullanım: `/togglefeed <numara>`\n\n"
                    "Feed numarasını görmek için /feeds komutunu kullanın.",
                    parse_mode='Markdown'
                )
                return
            
            try:
                index = int(context.args[0]) - 1
            except ValueError:
                await update.message.reply_text("❌ Geçersiz numara!")
                return
            
            # Load feeds
            if not os.path.exists(FEEDS_FILE):
                await update.message.reply_text("❌ RSS feed dosyası bulunamadı.")
                return
            
            with open(FEEDS_FILE, 'r', encoding='utf-8') as f:
                feeds = json.load(f)
            
            if index < 0 or index >= len(feeds):
                await update.message.reply_text(
                    f"❌ Geçersiz numara! (1-{len(feeds)} arası olmalı)"
                )
                return
            
            # Toggle enabled status
            feeds[index]['enabled'] = not feeds[index].get('enabled', True)
            new_status = "aktif" if feeds[index]['enabled'] else "pasif"
            
            # Save
            with open(FEEDS_FILE, 'w', encoding='utf-8') as f:
                json.dump(feeds, f, indent=2, ensure_ascii=False)
            
            status_emoji = "✅" if feeds[index]['enabled'] else "❌"
            await update.message.reply_text(
                f"{status_emoji} Feed durumu değiştirildi!\n\n"
                f"**{feeds[index]['name']}**\n"
                f"Yeni durum: {new_status}"
            )
            logger.info(f"Toggled RSS feed: {feeds[index]['name']} -> {new_status}")
            
        except Exception as e:
            logger.error(f"Error in togglefeed command: {e}")
            await update.message.reply_text(f"❌ Hata: {str(e)}")
    
    async def list_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /list command - List liked articles"""
        db = get_db_session()
        try:
            # Get all content with positive feedback
            liked_content = db.query(Content)\
                .join(Feedback, Content.id == Feedback.content_id)\
                .filter(Feedback.sentiment == 'positive')\
                .order_by(Content.fetched_date.desc())\
                .limit(50)\
                .all()
            
            if not liked_content:
                await update.message.reply_text("ℹ️ Henüz beğenilen haber yok.")
                return
            
            message = "👍 **Beğenilen Haberler**\n\n"
            for idx, content in enumerate(liked_content, 1):
                category_emoji = "🤖" if content.category == "ai" else "💻"
                title = content.title[:60] + "..." if len(content.title) > 60 else content.title
                blog_mark = " 📝" if content.used_in_blog else ""
                message += f"{idx}. {category_emoji} {title}{blog_mark}\n"
                
                # Split message if too long
                if len(message) > 3500:
                    await update.message.reply_text(message, parse_mode='Markdown')
                    message = ""
            
            if message:
                message += f"\nToplam: {len(liked_content)} haber\n\n"
                message += "📝 = Blog'da kullanıldı\n"
                message += "`/removefeedback <numara>` ile beğeniyi kaldırabilirsiniz"
                await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in list command: {e}")
            await update.message.reply_text(f"❌ Hata: {str(e)}")
        finally:
            db.close()
    
    async def removefeedback_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /removefeedback command - Remove feedback for a news item
        Usage: /removefeedback <number>
        """
        try:
            if len(context.args) < 1:
                await update.message.reply_text(
                    "❌ Kullanım: `/removefeedback <numara>`\n\n"
                    "Haber numarasını görmek için /list komutunu kullanın.",
                    parse_mode='Markdown'
                )
                return
            
            try:
                index = int(context.args[0]) - 1
            except ValueError:
                await update.message.reply_text("❌ Geçersiz numara!")
                return
            
            db = get_db_session()
            try:
                # Get liked content
                liked_content = db.query(Content)\
                    .join(Feedback, Content.id == Feedback.content_id)\
                    .filter(Feedback.sentiment == 'positive')\
                    .order_by(Content.fetched_date.desc())\
                    .limit(50)\
                    .all()
                
                if index < 0 or index >= len(liked_content):
                    await update.message.reply_text(
                        f"❌ Geçersiz numara! (1-{len(liked_content)} arası olmalı)"
                    )
                    return
                
                # Remove feedback
                content = liked_content[index]
                feedback = db.query(Feedback).filter_by(content_id=content.id).first()
                if feedback:
                    db.delete(feedback)
                    db.commit()
                    
                    title = content.title[:60] + "..." if len(content.title) > 60 else content.title
                    await update.message.reply_text(
                        f"✅ Beğeni kaldırıldı!\n\n"
                        f"**{title}**"
                    )
                    logger.info(f"Removed feedback for content {content.id}")
                else:
                    await update.message.reply_text("❌ Beğeni bulunamadı!")
                    
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error in removefeedback command: {e}")
            await update.message.reply_text(f"❌ Hata: {str(e)}")
    
    async def blog_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /blog command - Publish Telegram digest and mark content as used"""
        await update.message.reply_text("📝 Haftalık özet hazırlanıyor...")
        
        try:
            # Import here to avoid circular imports
            from src.blog_generator import generate_weekly_blog, mark_content_as_used
            
            await update.message.reply_text("📊 Son 1 haftanın öne çıkan haberleri toplanıyor...")
            digest = generate_weekly_blog()
            
            if digest:
                mark_content_as_used(digest.get("content_ids"))
                await update.message.reply_text(
                    f"🎉 **Code Report hazır!**\n\n"
                    f"🌐 Telegraph: {digest['telegraph_url']}\n"
                    f"🗞️ Haber sayısı: {digest['item_count']}",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    "⚠️ Özet oluşturulamadı.\n\n"
                    "Olası sebepler:\n"
                    "• Yeterli 'ilginç' haber yok\n"
                    "• En az 5 haber gerekiyor\n\n"
                    "Daha fazla habere 👍 vererek blog içeriği oluşturabilirsiniz."
                )
            
        except Exception as e:
            logger.error(f"Error in blog command: {e}")
            await update.message.reply_text(
                f"❌ Hata oluştu: {str(e)}\n\n"
                f"Detaylar için logları kontrol edin."
            )
    
    async def testblog_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /testblog command - Publish digest without marking content"""
        await update.message.reply_text("📝 Test özeti hazırlanıyor...")
        
        try:
            # Import here to avoid circular imports
            from src.blog_generator import generate_weekly_blog
            
            await update.message.reply_text("📊 Son 1 haftanın öne çıkan haberleri toplanıyor...")
            digest = generate_weekly_blog()
            
            if digest:
                await update.message.reply_text(
                    f"🎉 **Test Code Report hazır!**\n\n"
                    f"🌐 Telegraph: {digest['telegraph_url']}\n"
                    f"🗞️ Haber sayısı: {digest['item_count']}\n\n"
                    f"⚠️ Not: Haberler işaretlenmedi, tekrar kullanılabilir.",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    "⚠️ Özet oluşturulamadı.\n\n"
                    "Olası sebepler:\n"
                    "• Yeterli 'ilginç' haber yok\n"
                    "• En az 5 haber gerekiyor\n\n"
                    "Daha fazla habere 👍 vererek blog içeriği oluşturabilirsiniz."
                )
            
        except Exception as e:
            logger.error(f"Error in testblog command: {e}")
            await update.message.reply_text(
                f"❌ Hata oluştu: {str(e)}\n\n"
                f"Detaylar için logları kontrol edin."
            )
    
    async def trigger_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /trg command - Manually trigger news check"""
        await update.message.reply_text("🔍 Haber taraması başlatılıyor...")
        
        try:
            # Import here to avoid circular imports
            from src.rss_monitor import run_rss_check
            from src.content_filter import filter_content
            from src.ml_engine import update_preference_learning
            
            # Step 1: Check RSS feeds
            await update.message.reply_text("📡 RSS feedleri kontrol ediliyor...")
            new_items = run_rss_check()
            
            if not new_items:
                await update.message.reply_text(
                    "ℹ️ Yeni içerik bulunamadı.\n\n"
                    "Tüm feedler kontrol edildi ancak yeni haber bulunamadı."
                )
                return
            
            await update.message.reply_text(f"✅ {len(new_items)} yeni öğe bulundu.")
            
            # Step 2: Filter and categorize
            await update.message.reply_text("🔍 İçerikler filtreleniyor...")
            filtered_items = filter_content()
            
            if not filtered_items:
                await update.message.reply_text(
                    "ℹ️ İlgili içerik bulunamadı.\n\n"
                    "Yeni öğeler bulundu ancak filtreleme kriterlerine uymadı."
                )
                return
            
            await update.message.reply_text(f"✅ {len(filtered_items)} ilgili içerik bulundu.")
            
            # Step 3: Update ML scores
            await update.message.reply_text("🧠 ML skorları güncelleniyor...")
            update_preference_learning()
            
            # Step 4: Send notifications
            await update.message.reply_text(f"📱 Bildirimler gönderiliyor...")
            sent_count = await send_content_notifications(filtered_items)
            
            # Final summary
            await update.message.reply_text(
                f"✅ **Tarama tamamlandı!**\n\n"
                f"📊 Özet:\n"
                f"• Yeni öğe: {len(new_items)}\n"
                f"• Filtrelenmiş: {len(filtered_items)}\n"
                f"• Bildirim gönderilen: {sent_count}\n\n"
                f"🎉 Haberleriniz hazır!",
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error in trigger command: {e}")
            await update.message.reply_text(
                f"❌ Hata oluştu: {str(e)}\n\n"
                f"Detaylar için logları kontrol edin."
            )
    
    def setup_handlers(self):
        """Setup bot handlers"""
        if not self.app:
            return
        
        # Command handlers
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("stats", self.stats_command))
        self.app.add_handler(CommandHandler("trg", self.trigger_command))
        self.app.add_handler(CommandHandler("blog", self.blog_command))
        self.app.add_handler(CommandHandler("testblog", self.testblog_command))
        self.app.add_handler(CommandHandler("list", self.list_command))
        self.app.add_handler(CommandHandler("removefeedback", self.removefeedback_command))
        self.app.add_handler(CommandHandler("feeds", self.feeds_command))
        self.app.add_handler(CommandHandler("addfeed", self.addfeed_command))
        self.app.add_handler(CommandHandler("removefeed", self.removefeed_command))
        self.app.add_handler(CommandHandler("togglefeed", self.togglefeed_command))
        self.app.add_handler(CommandHandler("help", self.help_command))
        
        # Callback query handler for feedback buttons
        self.app.add_handler(CallbackQueryHandler(self.handle_feedback))
    
    async def initialize(self):
        """Initialize bot application"""
        self.app = Application.builder().token(self.bot_token).build()
        self.setup_handlers()
        logger.info("Telegram bot initialized")
    
    async def start_polling(self):
        """Start bot in polling mode"""
        if not self.app:
            await self.initialize()
        
        logger.info("Starting Telegram bot polling...")
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()
    
    async def stop(self):
        """Stop the bot"""
        if self.app:
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()


async def send_content_notifications(content_list):
    """Send notifications for a list of content items
    
    Args:
        content_list: List of dictionaries with content data (from filter_content)
    """
    bot = TelegramBot()
    await bot.initialize()
    
    # Extract content IDs (content_list is now list of dicts)
    content_ids = [item['id'] for item in content_list[:Config.MAX_NOTIFICATIONS_PER_HOUR]]
    
    sent_count = 0
    for content_id in content_ids:
        # Fetch fresh content from database for each notification
        db = get_db_session()
        try:
            content = db.query(Content).filter_by(id=content_id).first()
            if not content:
                continue
            
            # Send notification with fresh content
            success = await bot.send_notification(content)
            
            if success:
                sent_count += 1
                # Mark as notified
                content.notified = True
                db.commit()
        except Exception as e:
            logger.error(f"Error sending notification for content {content_id}: {e}")
            db.rollback()
        finally:
            db.close()
    
    logger.info(f"Sent {sent_count} notifications")
    return sent_count
