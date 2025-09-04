"""Data loading and caching module for Quran verses, translations, and Tafsir."""

import json
import logging
import time
from pathlib import Path
from typing import Dict, Any, Optional, Set
import hashlib
from dataclasses import dataclass
from jsonschema import validate, ValidationError

from config.settings import Config

logger = logging.getLogger(__name__)


@dataclass
class VerseData:
    """Structured verse data."""
    verse_key: str
    surah: int
    ayah: int
    arabic_text: str
    translation: str
    tafsir: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'verse_key': self.verse_key,
            'surah': self.surah,
            'ayah': self.ayah,
            'arabic_text': self.arabic_text,
            'translation': self.translation,
            'tafsir': self.tafsir,
        }


class DataValidationError(Exception):
    """Raised when data validation fails."""
    pass


class DataLoader:
    """Handles loading, validation, and caching of Quran data."""
    
    def __init__(self, config: Config):
        self.config = config
        self._unified_data: Optional[Dict[str, VerseData]] = None
        self._data_hash: Optional[str] = None
        
        # JSON schema for verse validation
        self.verse_schema = {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "verse_key": {"type": "string", "pattern": r"^\d+:\d+$"},
                "surah": {"type": "integer", "minimum": 1, "maximum": 114},
                "ayah": {"type": "integer", "minimum": 1},
                "text": {"type": "string", "minLength": 1}
            },
            "required": ["id", "verse_key", "surah", "ayah", "text"]
        }
        
        self.translation_schema = {
            "type": "object",
            "properties": {
                "t": {"type": "string", "minLength": 1}
            },
            "required": ["t"]
        }
    
    def _calculate_data_hash(self) -> str:
        """Calculate hash of all data files to detect changes."""
        hasher = hashlib.sha256()
        
        for file_path in self.config.DATA_FILES.values():
            if file_path.exists():
                hasher.update(file_path.read_bytes())
            else:
                logger.warning(f"Data file not found: {file_path}")
        
        return hasher.hexdigest()
    
    def _is_cache_valid(self) -> bool:
        """Check if cached data is still valid."""
        if not self.config.CACHE_ENABLED:
            return False
            
        cache_file = self.config.UNIFIED_DATA_CACHE_FILE
        if not cache_file.exists():
            return False
        
        # Check if cache is newer than data files
        cache_mtime = cache_file.stat().st_mtime
        for file_path in self.config.DATA_FILES.values():
            if file_path.exists() and file_path.stat().st_mtime > cache_mtime:
                return False
        
        # Check data hash
        current_hash = self._calculate_data_hash()
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)
                return cached_data.get('data_hash') == current_hash
        except (json.JSONDecodeError, FileNotFoundError):
            return False
    
    def _load_json_file(self, file_path: Path) -> Dict[str, Any]:
        """Load and validate JSON file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.info(f"Loaded {len(data)} entries from {file_path.name}")
            return data
        except FileNotFoundError:
            raise DataValidationError(f"Required data file not found: {file_path}")
        except json.JSONDecodeError as e:
            raise DataValidationError(f"Invalid JSON in {file_path}: {e}")
        except Exception as e:
            raise DataValidationError(f"Error loading {file_path}: {e}")
    
    def _validate_verse_data(self, data: Dict[str, Any], file_name: str) -> None:
        """Validate verse data structure."""
        for verse_key, verse_data in data.items():
            try:
                if file_name == 'quran_arabic':
                    validate(verse_data, self.verse_schema)
                elif file_name in ['translation_en', 'tafsir_en']:
                    if isinstance(verse_data, dict):
                        if 't' in verse_data:
                            validate(verse_data, self.translation_schema)
                    elif not isinstance(verse_data, str):
                        raise ValidationError(f"Invalid data type for {verse_key}")
            except ValidationError as e:
                raise DataValidationError(f"Validation error in {file_name} for verse {verse_key}: {e}")
    
    def _extract_tafsir_text(self, tafsir_entry: Any) -> str:
        """Extract text from tafsir entry, handling different formats."""
        if isinstance(tafsir_entry, dict) and 'text' in tafsir_entry:
            return tafsir_entry['text']
        elif isinstance(tafsir_entry, str):
            return tafsir_entry
        else:
            logger.warning(f"Unexpected tafsir format: {type(tafsir_entry)}")
            return ""
    
    def _unify_data(self, quran_data: Dict[str, Any], translation_data: Dict[str, Any], 
                   tafsir_data: Dict[str, Any]) -> Dict[str, VerseData]:
        """Combine all data sources into unified structure."""
        unified_data = {}
        missing_translations = set()
        missing_tafsir = set()
        
        for verse_key, quran_entry in quran_data.items():
            # Check if verse exists in all datasets
            if verse_key not in translation_data:
                missing_translations.add(verse_key)
                continue
            
            if verse_key not in tafsir_data:
                missing_tafsir.add(verse_key)
                continue
            
            # Extract data
            arabic_text = quran_entry["text"]
            translation_text = (translation_data[verse_key]['t'] 
                              if isinstance(translation_data[verse_key], dict) 
                              else translation_data[verse_key])
            tafsir_text = self._extract_tafsir_text(tafsir_data[verse_key])
            
            # Create structured verse data
            verse_data = VerseData(
                verse_key=verse_key,
                surah=quran_entry["surah"],
                ayah=quran_entry["ayah"],
                arabic_text=arabic_text,
                translation=translation_text,
                tafsir=tafsir_text
            )
            
            unified_data[verse_key] = verse_data
        
        # Log missing data
        if missing_translations:
            logger.warning(f"Missing translations for {len(missing_translations)} verses")
        if missing_tafsir:
            logger.warning(f"Missing tafsir for {len(missing_tafsir)} verses")
        
        logger.info(f"Successfully unified {len(unified_data)} verses")
        return unified_data
    
    def _save_cache(self, unified_data: Dict[str, VerseData]) -> None:
        """Save unified data to cache."""
        if not self.config.CACHE_ENABLED:
            return
        
        try:
            cache_data = {
                'data_hash': self._data_hash,
                'timestamp': time.time(),
                'unified_data': {k: v.to_dict() for k, v in unified_data.items()}
            }
            
            self.config.CACHE_DIR.mkdir(exist_ok=True)
            with open(self.config.UNIFIED_DATA_CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Cached unified data to {self.config.UNIFIED_DATA_CACHE_FILE}")
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")
    
    def _load_from_cache(self) -> Dict[str, VerseData]:
        """Load unified data from cache."""
        try:
            with open(self.config.UNIFIED_DATA_CACHE_FILE, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            unified_data = {}
            for verse_key, verse_dict in cache_data['unified_data'].items():
                unified_data[verse_key] = VerseData(**verse_dict)
            
            logger.info(f"Loaded {len(unified_data)} verses from cache")
            return unified_data
        
        except Exception as e:
            logger.error(f"Failed to load from cache: {e}")
            raise DataValidationError(f"Cache loading failed: {e}")
    
    def load_data(self, force_reload: bool = False) -> Dict[str, VerseData]:
        """Load and return unified verse data."""
        # Return cached data if available
        if not force_reload and self._unified_data is not None:
            return self._unified_data
        
        # Check if we can use cached data
        if not force_reload and self._is_cache_valid():
            try:
                self._unified_data = self._load_from_cache()
                return self._unified_data
            except DataValidationError:
                logger.warning("Cache validation failed, reloading from source")
        
        logger.info("Loading data from source files...")
        start_time = time.time()
        
        try:
            # Load raw data files
            quran_data = self._load_json_file(self.config.DATA_FILES['quran_arabic'])
            translation_data = self._load_json_file(self.config.DATA_FILES['translation_en'])
            tafsir_data = self._load_json_file(self.config.DATA_FILES['tafsir_en'])
            
            # Validate data
            self._validate_verse_data(quran_data, 'quran_arabic')
            self._validate_verse_data(translation_data, 'translation_en')
            self._validate_verse_data(tafsir_data, 'tafsir_en')
            
            # Calculate data hash
            self._data_hash = self._calculate_data_hash()
            
            # Unify data
            self._unified_data = self._unify_data(quran_data, translation_data, tafsir_data)
            
            # Cache the result
            self._save_cache(self._unified_data)
            
            load_time = time.time() - start_time
            logger.info(f"Data loading completed in {load_time:.2f} seconds")
            
            return self._unified_data
        
        except Exception as e:
            logger.error(f"Data loading failed: {e}")
            raise DataValidationError(f"Failed to load data: {e}")
    
    def get_verse_keys(self) -> Set[str]:
        """Get all available verse keys."""
        data = self.load_data()
        return set(data.keys())
    
    def get_surah_info(self) -> Dict[int, Dict[str, Any]]:
        """Get information about all surahs."""
        data = self.load_data()
        surah_info = {}
        
        for verse_data in data.values():
            surah_num = verse_data.surah
            if surah_num not in surah_info:
                surah_info[surah_num] = {
                    'surah_number': surah_num,
                    'ayah_count': 0,
                    'first_verse_key': verse_data.verse_key,
                }
            surah_info[surah_num]['ayah_count'] += 1
        
        return surah_info
    
    def validate_data_integrity(self) -> Dict[str, Any]:
        """Perform comprehensive data integrity check."""
        try:
            data = self.load_data()
            
            # Check verse key format
            invalid_keys = []
            for verse_key in data.keys():
                if not verse_key.count(':') == 1:
                    invalid_keys.append(verse_key)
            
            # Check for missing content
            empty_translations = []
            empty_tafsir = []
            
            for verse_key, verse_data in data.items():
                if not verse_data.translation.strip():
                    empty_translations.append(verse_key)
                if not verse_data.tafsir.strip():
                    empty_tafsir.append(verse_key)
            
            return {
                'total_verses': len(data),
                'invalid_keys': invalid_keys,
                'empty_translations': empty_translations,
                'empty_tafsir': empty_tafsir,
                'data_hash': self._data_hash,
                'cache_valid': self._is_cache_valid(),
            }
        
        except Exception as e:
            return {'error': str(e)}