"""Configuration settings for the Ayah App."""

import os
from pathlib import Path
from typing import Dict, Any, Optional

# Base directory
BASE_DIR = Path(__file__).parent.parent

class Config:
    """Base configuration class."""
    
    # App settings
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    # Data paths
    DATA_DIR = BASE_DIR / 'data'
    CACHE_DIR = BASE_DIR / 'cache'
    LOGS_DIR = BASE_DIR / 'logs'
    
    # Data files
    DATA_FILES = {
        'quran_arabic': DATA_DIR / 'qpc-hafs.json',
        'translation_en': DATA_DIR / 'en-taqi-usmani-simple.json',
        'tafsir_en': DATA_DIR / 'en-tafisr-ibn-kathir.json',
        'tajweed': DATA_DIR / 'qpc-hafs-tajweed.json',
        'word_by_word': DATA_DIR / 'qpc-hafs-word-by-word.json',
    }
    
    # Cache settings
    CACHE_ENABLED = True
    CACHE_TIMEOUT = 3600  # 1 hour in seconds
    UNIFIED_DATA_CACHE_FILE = CACHE_DIR / 'unified_data.json'
    
    # Email settings
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@ayahapp.com')
    
    # Scheduler settings
    SCHEDULER_API_ENABLED = True
    DAILY_EMAIL_TIME = os.environ.get('DAILY_EMAIL_TIME', '06:00')  # 6 AM
    WEEKLY_EMAIL_DAY = int(os.environ.get('WEEKLY_EMAIL_DAY', 4))  # Friday = 4
    
    # Redis settings (for production scaling)
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    
    # Database settings (if we add user management later)
    DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///ayah_app.db')
    
    # API settings
    API_RATE_LIMIT = "100 per hour"
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',')
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # UI Configuration
    UI_CONFIG = {
        'default_theme': 'light',
        'font_sizes': ['small', 'medium', 'large', 'extra-large'],
        'arabic_fonts': ['Amiri', 'Noto Sans Arabic', 'Scheherazade'],
        'supported_languages': {
            'en': 'English',
            'ar': 'العربية',
        },
        'items_per_page': 20,
        'max_search_results': 100,
    }
    
    @classmethod
    def init_app(cls, app: Any) -> None:
        """Initialize app with configuration."""
        # Create necessary directories
        for directory in [cls.CACHE_DIR, cls.LOGS_DIR]:
            directory.mkdir(exist_ok=True)


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    CACHE_ENABLED = False  # Disable caching in development


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    
    # Enhanced security
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        raise ValueError("SECRET_KEY environment variable must be set in production")
    
    # Production email settings
    if not os.environ.get('MAIL_USERNAME') or not os.environ.get('MAIL_PASSWORD'):
        raise ValueError("Email credentials must be set in production")


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    CACHE_ENABLED = False
    MAIL_SUPPRESS_SEND = True
    WTF_CSRF_ENABLED = False


# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config(config_name: Optional[str] = None) -> Config:
    """Get configuration based on environment."""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')
    return config[config_name]