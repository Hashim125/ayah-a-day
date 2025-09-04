"""Email subscription and management system."""

import json
import hashlib
import secrets
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass, asdict
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from flask_mail import Mail, Message

from .data_loader import VerseData
from .html_generator import HTMLGenerator
from config.settings import Config

logger = logging.getLogger(__name__)


@dataclass
class Subscriber:
    """Email subscriber data structure."""
    email: str
    name: str
    frequency: str  # 'daily' or 'weekly'
    subscribed_at: str
    unsubscribe_token: str
    active: bool = True
    last_email_sent: Optional[str] = None
    total_emails_sent: int = 0
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Subscriber':
        """Create from dictionary."""
        return cls(**data)


class EmailSubscriptionManager:
    """Manages email subscriptions and sending."""
    
    def __init__(self, config: Config, mail: Mail):
        self.config = config
        self.mail = mail
        self.html_generator = HTMLGenerator(config)
        
        # Subscribers data file
        self.subscribers_file = config.DATA_DIR / 'subscribers.json'
        self.subscribers_file.parent.mkdir(exist_ok=True)
        
        # Email templates
        self.templates_dir = Path(__file__).parent.parent.parent / 'templates'
        
        # Load existing subscribers
        self._subscribers: Dict[str, Subscriber] = self._load_subscribers()
        
        # Email sending statistics
        self._stats = {
            'emails_sent_today': 0,
            'last_reset_date': datetime.now().strftime('%Y-%m-%d'),
            'total_emails_sent': 0,
            'failed_emails': 0
        }
    
    def _load_subscribers(self) -> Dict[str, Subscriber]:
        """Load subscribers from JSON file."""
        try:
            if self.subscribers_file.exists():
                with open(self.subscribers_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return {
                        email: Subscriber.from_dict(sub_data) 
                        for email, sub_data in data.items()
                    }
        except Exception as e:
            logger.error(f"Error loading subscribers: {e}")
        
        return {}
    
    def _save_subscribers(self) -> None:
        """Save subscribers to JSON file."""
        try:
            data = {email: sub.to_dict() for email, sub in self._subscribers.items()}
            with open(self.subscribers_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving subscribers: {e}")
    
    def _generate_unsubscribe_token(self, email: str) -> str:
        """Generate secure unsubscribe token."""
        # Use email + secret + timestamp for security
        secret_data = f"{email}{self.config.SECRET_KEY}{datetime.now().isoformat()}"
        return hashlib.sha256(secret_data.encode()).hexdigest()[:32]
    
    def _validate_email(self, email: str) -> bool:
        """Basic email validation."""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def subscribe_user(self, email: str, name: str = "", frequency: str = "daily") -> Tuple[bool, str]:
        """
        Subscribe a user to email updates.
        
        Args:
            email: User's email address
            name: User's name (optional)
            frequency: 'daily' or 'weekly'
            
        Returns:
            Tuple of (success, message)
        """
        # Validate inputs
        if not self._validate_email(email):
            return False, "Invalid email address format."
        
        if frequency not in ['daily', 'weekly']:
            frequency = 'daily'
        
        email = email.lower().strip()
        
        try:
            # Check if already subscribed
            if email in self._subscribers:
                existing_sub = self._subscribers[email]
                if existing_sub.active:
                    return False, "This email is already subscribed."
                else:
                    # Reactivate subscription
                    existing_sub.active = True
                    existing_sub.frequency = frequency
                    existing_sub.name = name or existing_sub.name
                    self._save_subscribers()
                    
                    logger.info(f"Reactivated subscription for {email}")
                    return True, "Successfully reactivated your subscription!"
            
            # Create new subscription
            subscriber = Subscriber(
                email=email,
                name=name,
                frequency=frequency,
                subscribed_at=datetime.now().isoformat(),
                unsubscribe_token=self._generate_unsubscribe_token(email),
                active=True
            )
            
            self._subscribers[email] = subscriber
            self._save_subscribers()
            
            # Send welcome email
            self._send_welcome_email(subscriber)
            
            logger.info(f"New subscription: {email} ({frequency})")
            return True, f"Successfully subscribed to {frequency} Ayah emails!"
        
        except Exception as e:
            logger.error(f"Error subscribing {email}: {e}")
            return False, "An error occurred. Please try again later."
    
    def unsubscribe_user(self, token: str) -> bool:
        """
        Unsubscribe a user using their token.
        
        Args:
            token: Unsubscribe token
            
        Returns:
            Success status
        """
        try:
            # Find subscriber by token
            for email, subscriber in self._subscribers.items():
                if subscriber.unsubscribe_token == token and subscriber.active:
                    subscriber.active = False
                    self._save_subscribers()
                    
                    logger.info(f"Unsubscribed: {email}")
                    return True
            
            logger.warning(f"Invalid unsubscribe token: {token}")
            return False
        
        except Exception as e:
            logger.error(f"Error unsubscribing with token {token}: {e}")
            return False
    
    def get_active_subscribers(self, frequency: Optional[str] = None) -> List[Subscriber]:
        """Get list of active subscribers, optionally filtered by frequency."""
        subscribers = [s for s in self._subscribers.values() if s.active]
        
        if frequency:
            subscribers = [s for s in subscribers if s.frequency == frequency]
        
        return subscribers
    
    def _send_welcome_email(self, subscriber: Subscriber) -> bool:
        """Send welcome email to new subscriber."""
        try:
            subject = "Welcome to Daily Ayah - Your Spiritual Journey Begins"
            
            # Create welcome message
            greeting = f"Dear {subscriber.name}," if subscriber.name else "Peace be upon you,"
            
            html_body = f'''
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center;">
                    <h1>🌙 Welcome to Daily Ayah</h1>
                    <p>Your spiritual journey begins now</p>
                </div>
                
                <div style="padding: 30px; background: white;">
                    <p>{greeting}</p>
                    
                    <p>Thank you for subscribing to Daily Ayah! You will now receive beautiful verses from the Holy Quran with translations and commentary {subscriber.frequency}.</p>
                    
                    <div style="background: #f8f9fa; padding: 20px; border-left: 4px solid #667eea; margin: 20px 0;">
                        <h3 style="color: #667eea; margin-top: 0;">What to Expect:</h3>
                        <ul>
                            <li>Authentic verses from the Holy Quran</li>
                            <li>English translations by Taqi Usmani</li>
                            <li>Detailed commentary (Tafsir) by Ibn Kathir</li>
                            <li>Beautiful, easy-to-read formatting</li>
                        </ul>
                    </div>
                    
                    <p>May these verses bring guidance, peace, and blessings to your life.</p>
                    
                    <p style="margin-top: 30px;">
                        <a href="{self.config.BASE_URL if hasattr(self.config, 'BASE_URL') else 'https://ayahapp.com'}" 
                           style="background: #667eea; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px;">
                            Visit Ayah App
                        </a>
                    </p>
                </div>
                
                <div style="background: #f8f9fa; padding: 20px; text-align: center; font-size: 12px; color: #666;">
                    <p>You're receiving this because you subscribed to Daily Ayah.</p>
                    <p>
                        <a href="{self._get_unsubscribe_url(subscriber.unsubscribe_token)}" 
                           style="color: #666;">Unsubscribe</a>
                    </p>
                </div>
            </div>
            '''
            
            return self._send_email(
                to_email=subscriber.email,
                to_name=subscriber.name,
                subject=subject,
                html_body=html_body
            )
        
        except Exception as e:
            logger.error(f"Error sending welcome email to {subscriber.email}: {e}")
            return False
    
    def send_daily_email(self, verse: VerseData) -> Dict[str, int]:
        """Send daily email to all daily subscribers."""
        daily_subscribers = self.get_active_subscribers('daily')
        return self._send_verse_email(verse, daily_subscribers, "Daily Ayah")
    
    def send_weekly_email(self, verse: VerseData) -> Dict[str, int]:
        """Send weekly email to all weekly subscribers."""
        weekly_subscribers = self.get_active_subscribers('weekly')
        return self._send_verse_email(verse, weekly_subscribers, "Weekly Ayah")
    
    def _send_verse_email(self, verse: VerseData, subscribers: List[Subscriber], 
                         email_type: str) -> Dict[str, int]:
        """Send verse email to list of subscribers."""
        stats = {'sent': 0, 'failed': 0}
        
        if not subscribers:
            logger.info(f"No subscribers for {email_type}")
            return stats
        
        logger.info(f"Sending {email_type} to {len(subscribers)} subscribers")
        
        for subscriber in subscribers:
            try:
                success = self._send_verse_to_subscriber(verse, subscriber, email_type)
                if success:
                    stats['sent'] += 1
                    # Update subscriber stats
                    subscriber.last_email_sent = datetime.now().isoformat()
                    subscriber.total_emails_sent += 1
                else:
                    stats['failed'] += 1
                    
            except Exception as e:
                logger.error(f"Error sending {email_type} to {subscriber.email}: {e}")
                stats['failed'] += 1
        
        # Save updated subscriber data
        self._save_subscribers()
        
        logger.info(f"{email_type} summary: {stats['sent']} sent, {stats['failed']} failed")
        return stats
    
    def _send_verse_to_subscriber(self, verse: VerseData, subscriber: Subscriber, 
                                 email_type: str) -> bool:
        """Send verse email to individual subscriber."""
        try:
            subject = f"{email_type} - Verse {verse.verse_key}"
            
            # Generate HTML content
            html_body = self.html_generator.generate_email_html(verse, subscriber.name)
            
            # Add unsubscribe URL
            unsubscribe_url = self._get_unsubscribe_url(subscriber.unsubscribe_token)
            html_body = html_body.replace('{{ unsubscribe_url }}', unsubscribe_url)
            
            return self._send_email(
                to_email=subscriber.email,
                to_name=subscriber.name,
                subject=subject,
                html_body=html_body
            )
        
        except Exception as e:
            logger.error(f"Error creating verse email for {subscriber.email}: {e}")
            return False
    
    def _send_email(self, to_email: str, to_name: str, subject: str, 
                   html_body: str, text_body: str = None) -> bool:
        """Send email using Flask-Mail."""
        try:
            msg = Message(
                subject=subject,
                sender=self.config.MAIL_DEFAULT_SENDER,
                recipients=[to_email]
            )
            
            # Set HTML body
            msg.html = html_body
            
            # Generate text version if not provided
            if text_body:
                msg.body = text_body
            else:
                # Simple HTML to text conversion
                import re
                text_body = re.sub(r'<[^>]+>', '', html_body)
                text_body = re.sub(r'\\s+', ' ', text_body).strip()
                msg.body = text_body
            
            # Send email
            self.mail.send(msg)
            
            logger.debug(f"Email sent successfully to {to_email}")
            return True
        
        except Exception as e:
            logger.error(f"Error sending email to {to_email}: {e}")
            return False
    
    def _get_unsubscribe_url(self, token: str) -> str:
        """Generate unsubscribe URL."""
        base_url = getattr(self.config, 'BASE_URL', 'http://localhost:5000')
        return f"{base_url}/unsubscribe/{token}"
    
    def get_subscription_stats(self) -> Dict[str, int]:
        """Get subscription statistics."""
        active_subs = self.get_active_subscribers()
        daily_subs = [s for s in active_subs if s.frequency == 'daily']
        weekly_subs = [s for s in active_subs if s.frequency == 'weekly']
        
        return {
            'total_subscribers': len(self._subscribers),
            'active_subscribers': len(active_subs),
            'daily_subscribers': len(daily_subs),
            'weekly_subscribers': len(weekly_subs),
            'inactive_subscribers': len(self._subscribers) - len(active_subs)
        }
    
    def cleanup_inactive_subscribers(self, days: int = 365) -> int:
        """Remove subscribers who have been inactive for specified days."""
        cutoff_date = datetime.now() - timedelta(days=days)
        removed_count = 0
        
        emails_to_remove = []
        for email, subscriber in self._subscribers.items():
            if not subscriber.active:
                sub_date = datetime.fromisoformat(subscriber.subscribed_at)
                if sub_date < cutoff_date:
                    emails_to_remove.append(email)
        
        for email in emails_to_remove:
            del self._subscribers[email]
            removed_count += 1
        
        if removed_count > 0:
            self._save_subscribers()
            logger.info(f"Cleaned up {removed_count} inactive subscribers")
        
        return removed_count
    
    def export_subscribers(self, file_path: Optional[Path] = None) -> Path:
        """Export subscribers to JSON file."""
        if file_path is None:
            file_path = self.config.DATA_DIR / f"subscribers_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        export_data = {
            'exported_at': datetime.now().isoformat(),
            'stats': self.get_subscription_stats(),
            'subscribers': {email: sub.to_dict() for email, sub in self._subscribers.items()}
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Subscribers exported to {file_path}")
        return file_path