"""Pytest configuration and fixtures for testing."""

import pytest
import tempfile
import shutil
from pathlib import Path
import json
from unittest.mock import Mock

from config.settings import TestingConfig
from src.ayah_app.data_loader import DataLoader, VerseData
from src.ayah_app.verse_selector import VerseSelector
from src.ayah_app.html_generator import HTMLGenerator
from src.ayah_app.email_system import EmailSubscriptionManager
from src.ayah_app.app import create_app


@pytest.fixture
def temp_config():
    """Create a temporary configuration for testing."""
    temp_dir = Path(tempfile.mkdtemp())
    
    class TestConfig(TestingConfig):
        DATA_DIR = temp_dir / 'data'
        CACHE_DIR = temp_dir / 'cache'
        LOGS_DIR = temp_dir / 'logs'
        
        DATA_FILES = {
            'quran_arabic': temp_dir / 'data' / 'qpc-hafs.json',
            'translation_en': temp_dir / 'data' / 'en-taqi-usmani-simple.json',
            'tafsir_en': temp_dir / 'data' / 'en-tafisr-ibn-kathir.json',
        }
    
    config = TestConfig()
    
    # Create directories
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    config.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    config.LOGS_DIR.mkdir(parents=True, exist_ok=True)
    
    yield config
    
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sample_verse_data():
    """Sample verse data for testing."""
    return VerseData(
        verse_key="2:255",
        surah=2,
        ayah=255,
        arabic_text="ٱللَّهُ لَآ إِلَٰهَ إِلَّا هُوَ ٱلۡحَىُّ ٱلۡقَيُّومُ",
        translation="Allah - there is no deity except Him, the Ever-Living, the Self-Sustaining.",
        tafsir="This is Ayat al-Kursi, one of the most powerful verses in the Quran..."
    )


@pytest.fixture
def sample_json_data():
    """Sample JSON data matching the expected format."""
    return {
        "quran_arabic": {
            "1:1": {
                "id": 1,
                "verse_key": "1:1",
                "surah": 1,
                "ayah": 1,
                "text": "بِسۡمِ ٱللَّهِ ٱلرَّحۡمَٰنِ ٱلرَّحِيمِ ١"
            },
            "2:255": {
                "id": 255,
                "verse_key": "2:255",
                "surah": 2,
                "ayah": 255,
                "text": "ٱللَّهُ لَآ إِلَٰهَ إِلَّا هُوَ ٱلۡحَىُّ ٱلۡقَيُّومُ"
            }
        },
        "translation_en": {
            "1:1": {"t": "In the name of Allah, the Entirely Merciful, the Especially Merciful."},
            "2:255": {"t": "Allah - there is no deity except Him, the Ever-Living, the Self-Sustaining."}
        },
        "tafsir_en": {
            "1:1": {"text": "This is the opening verse of the Quran..."},
            "2:255": {"text": "This is Ayat al-Kursi, one of the most powerful verses in the Quran..."}
        }
    }


@pytest.fixture
def setup_test_data(temp_config, sample_json_data):
    """Setup test data files."""
    # Write sample data to JSON files
    for file_key, data in sample_json_data.items():
        file_path = temp_config.DATA_FILES[file_key]
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    return temp_config


@pytest.fixture
def data_loader(setup_test_data):
    """DataLoader instance with test data."""
    return DataLoader(setup_test_data)


@pytest.fixture
def verse_selector(data_loader):
    """VerseSelector instance with test data."""
    return VerseSelector(data_loader)


@pytest.fixture
def html_generator(setup_test_data):
    """HTMLGenerator instance."""
    return HTMLGenerator(setup_test_data)


@pytest.fixture
def mock_mail():
    """Mock Flask-Mail instance."""
    mail = Mock()
    mail.send = Mock()
    return mail


@pytest.fixture
def email_manager(setup_test_data, mock_mail):
    """EmailSubscriptionManager with mocked mail."""
    return EmailSubscriptionManager(setup_test_data, mock_mail)


@pytest.fixture
def flask_app(setup_test_data):
    """Flask app instance for testing."""
    app = create_app('testing')
    app.config['TESTING'] = True
    return app


@pytest.fixture
def client(flask_app):
    """Flask test client."""
    return flask_app.test_client()


@pytest.fixture
def runner(flask_app):
    """Flask CLI test runner."""
    return flask_app.test_cli_runner()


# Helper fixtures for common test scenarios

@pytest.fixture
def populated_data_loader(data_loader):
    """DataLoader with loaded data."""
    data_loader.load_data()
    return data_loader


@pytest.fixture
def verse_with_context(verse_selector):
    """Get a verse with its context."""
    verse = verse_selector.get_verse_by_key("2:255")
    context = verse_selector.get_verse_context("2:255")
    return verse, context


@pytest.fixture
def email_subscribers(email_manager):
    """Setup test email subscribers."""
    # Add test subscribers
    email_manager.subscribe_user("daily@test.com", "Daily User", "daily")
    email_manager.subscribe_user("weekly@test.com", "Weekly User", "weekly")
    email_manager.subscribe_user("inactive@test.com", "Inactive User", "daily")
    
    # Deactivate one subscriber
    email_manager.unsubscribe_user(
        email_manager._subscribers["inactive@test.com"].unsubscribe_token
    )
    
    return email_manager


# Test utilities

def assert_verse_data_valid(verse_data):
    """Assert that verse data is valid."""
    assert isinstance(verse_data, VerseData)
    assert verse_data.verse_key
    assert verse_data.surah >= 1
    assert verse_data.ayah >= 1
    assert verse_data.arabic_text
    assert verse_data.translation
    assert isinstance(verse_data.tafsir, str)  # Can be empty


def assert_html_valid(html_content):
    """Basic HTML validation."""
    assert isinstance(html_content, str)
    assert '<!DOCTYPE html>' in html_content
    assert '<html' in html_content
    assert '</html>' in html_content
    assert '<head>' in html_content
    assert '<body>' in html_content


# Custom pytest markers

def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "email: marks tests that require email functionality"
    )
    config.addinivalue_line(
        "markers", "data: marks tests that require data files"
    )