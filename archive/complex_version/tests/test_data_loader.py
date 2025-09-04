"""Tests for data_loader module."""

import pytest
import json
import tempfile
from pathlib import Path

from src.ayah_app.data_loader import DataLoader, DataValidationError, VerseData
from tests.conftest import assert_verse_data_valid


class TestDataLoader:
    """Test DataLoader functionality."""

    @pytest.mark.data
    def test_load_valid_data(self, data_loader):
        """Test loading valid data."""
        data = data_loader.load_data()
        
        assert len(data) == 2  # We have 2 verses in test data
        assert "1:1" in data
        assert "2:255" in data
        
        # Verify data structure
        for verse_key, verse_data in data.items():
            assert_verse_data_valid(verse_data)
            assert verse_data.verse_key == verse_key

    @pytest.mark.data
    def test_cache_functionality(self, data_loader):
        """Test data caching."""
        # First load
        data1 = data_loader.load_data()
        
        # Second load should use cache (if enabled)
        data2 = data_loader.load_data()
        
        assert data1 == data2

    def test_invalid_json_handling(self, temp_config):
        """Test handling of invalid JSON files."""
        # Create invalid JSON file
        invalid_file = temp_config.DATA_FILES['quran_arabic']
        invalid_file.parent.mkdir(parents=True, exist_ok=True)
        with open(invalid_file, 'w') as f:
            f.write('invalid json content')
        
        data_loader = DataLoader(temp_config)
        
        with pytest.raises(DataValidationError):
            data_loader.load_data()

    def test_missing_file_handling(self, temp_config):
        """Test handling of missing data files."""
        # Don't create any files
        data_loader = DataLoader(temp_config)
        
        with pytest.raises(DataValidationError):
            data_loader.load_data()

    def test_data_validation(self, temp_config, sample_json_data):
        """Test data validation with invalid data."""
        # Create invalid verse data
        invalid_data = sample_json_data.copy()
        invalid_data['quran_arabic']['1:1']['surah'] = -1  # Invalid surah number
        
        # Write invalid data
        with open(temp_config.DATA_FILES['quran_arabic'], 'w') as f:
            json.dump(invalid_data['quran_arabic'], f)
        
        # Write other valid files
        for key in ['translation_en', 'tafsir_en']:
            with open(temp_config.DATA_FILES[key], 'w') as f:
                json.dump(sample_json_data[key], f)
        
        data_loader = DataLoader(temp_config)
        
        with pytest.raises(DataValidationError):
            data_loader.load_data()

    @pytest.mark.data
    def test_get_verse_keys(self, populated_data_loader):
        """Test getting all verse keys."""
        verse_keys = populated_data_loader.get_verse_keys()
        
        assert isinstance(verse_keys, set)
        assert "1:1" in verse_keys
        assert "2:255" in verse_keys
        assert len(verse_keys) == 2

    @pytest.mark.data
    def test_get_surah_info(self, populated_data_loader):
        """Test getting surah information."""
        surah_info = populated_data_loader.get_surah_info()
        
        assert isinstance(surah_info, dict)
        assert 1 in surah_info
        assert 2 in surah_info
        
        # Check surah 1 info
        assert surah_info[1]['surah_number'] == 1
        assert surah_info[1]['ayah_count'] == 1
        assert surah_info[1]['first_verse_key'] == "1:1"

    @pytest.mark.data
    def test_data_integrity_check(self, populated_data_loader):
        """Test data integrity validation."""
        integrity_info = populated_data_loader.validate_data_integrity()
        
        assert 'total_verses' in integrity_info
        assert 'invalid_keys' in integrity_info
        assert 'empty_translations' in integrity_info
        assert 'empty_tafsir' in integrity_info
        
        assert integrity_info['total_verses'] == 2
        assert len(integrity_info['invalid_keys']) == 0

    def test_force_reload(self, data_loader):
        """Test forcing data reload."""
        # Load data normally
        data1 = data_loader.load_data()
        
        # Force reload
        data2 = data_loader.load_data(force_reload=True)
        
        assert data1 == data2  # Data should be the same

    @pytest.mark.slow
    def test_large_dataset_handling(self, temp_config):
        """Test handling of larger datasets."""
        # Create larger test dataset
        large_data = {
            'quran_arabic': {},
            'translation_en': {},
            'tafsir_en': {}
        }
        
        # Generate 100 verses
        for i in range(1, 101):
            verse_key = f"1:{i}"
            large_data['quran_arabic'][verse_key] = {
                "id": i,
                "verse_key": verse_key,
                "surah": 1,
                "ayah": i,
                "text": f"Arabic text for verse {i}"
            }
            large_data['translation_en'][verse_key] = {
                "t": f"Translation for verse {i}"
            }
            large_data['tafsir_en'][verse_key] = {
                "text": f"Tafsir for verse {i}"
            }
        
        # Write data files
        for file_key, data in large_data.items():
            file_path = temp_config.DATA_FILES[file_key]
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)
        
        data_loader = DataLoader(temp_config)
        data = data_loader.load_data()
        
        assert len(data) == 100

    def test_hash_calculation(self, data_loader):
        """Test data hash calculation for cache invalidation."""
        hash1 = data_loader._calculate_data_hash()
        hash2 = data_loader._calculate_data_hash()
        
        assert hash1 == hash2  # Should be consistent
        assert len(hash1) == 64  # SHA256 hash length

    def test_tafsir_text_extraction(self, data_loader):
        """Test different tafsir text formats."""
        # Test dict format
        dict_entry = {"text": "Test tafsir text"}
        extracted = data_loader._extract_tafsir_text(dict_entry)
        assert extracted == "Test tafsir text"
        
        # Test string format
        string_entry = "Direct tafsir text"
        extracted = data_loader._extract_tafsir_text(string_entry)
        assert extracted == "Direct tafsir text"
        
        # Test invalid format
        invalid_entry = 12345
        extracted = data_loader._extract_tafsir_text(invalid_entry)
        assert extracted == ""


class TestVerseData:
    """Test VerseData class."""

    def test_verse_data_creation(self, sample_verse_data):
        """Test creating VerseData instance."""
        assert_verse_data_valid(sample_verse_data)
        assert sample_verse_data.verse_key == "2:255"

    def test_verse_data_to_dict(self, sample_verse_data):
        """Test converting VerseData to dictionary."""
        verse_dict = sample_verse_data.to_dict()
        
        assert isinstance(verse_dict, dict)
        assert verse_dict['verse_key'] == "2:255"
        assert verse_dict['surah'] == 2
        assert verse_dict['ayah'] == 255
        assert 'arabic_text' in verse_dict
        assert 'translation' in verse_dict
        assert 'tafsir' in verse_dict