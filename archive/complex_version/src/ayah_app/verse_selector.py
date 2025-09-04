"""Verse selection and search functionality."""

import random
import re
import logging
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass

from .data_loader import VerseData, DataLoader

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Search result with relevance scoring."""
    verse_data: VerseData
    relevance_score: float
    matched_fields: List[str]


class VerseSelector:
    """Handles verse selection, search, and filtering."""
    
    def __init__(self, data_loader: DataLoader):
        self.data_loader = data_loader
        self._search_index: Optional[Dict[str, Set[str]]] = None
    
    def _build_search_index(self) -> Dict[str, Set[str]]:
        """Build search index for faster text search."""
        if self._search_index is not None:
            return self._search_index
        
        logger.info("Building search index...")
        data = self.data_loader.load_data()
        index = {}
        
        for verse_key, verse_data in data.items():
            # Index words from translation and tafsir (lowercased)
            text_content = f"{verse_data.translation} {verse_data.tafsir}".lower()
            words = re.findall(r'\b\w+\b', text_content)
            
            for word in words:
                if len(word) >= 3:  # Only index words with 3+ characters
                    if word not in index:
                        index[word] = set()
                    index[word].add(verse_key)
        
        self._search_index = index
        logger.info(f"Search index built with {len(index)} unique terms")
        return self._search_index
    
    def get_random_verse(self) -> VerseData:
        """Get a random verse."""
        data = self.data_loader.load_data()
        if not data:
            raise ValueError("No verse data available")
        
        verse_key = random.choice(list(data.keys()))
        return data[verse_key]
    
    def get_verse_by_key(self, verse_key: str) -> Optional[VerseData]:
        """Get a specific verse by its key (e.g., '2:255')."""
        data = self.data_loader.load_data()
        return data.get(verse_key)
    
    def get_verses_by_surah(self, surah_number: int, 
                           start_ayah: Optional[int] = None,
                           end_ayah: Optional[int] = None) -> List[VerseData]:
        """Get verses from a specific surah, optionally with ayah range."""
        data = self.data_loader.load_data()
        verses = []
        
        for verse_key, verse_data in data.items():
            if verse_data.surah == surah_number:
                # Apply ayah range filter if specified
                if start_ayah is not None and verse_data.ayah < start_ayah:
                    continue
                if end_ayah is not None and verse_data.ayah > end_ayah:
                    continue
                verses.append(verse_data)
        
        # Sort by ayah number
        verses.sort(key=lambda v: v.ayah)
        return verses
    
    def search_verses(self, query: str, limit: int = 50) -> List[SearchResult]:
        """Search verses by text content."""
        if not query.strip():
            return []
        
        query = query.lower().strip()
        data = self.data_loader.load_data()
        search_index = self._build_search_index()
        
        # Extract search terms
        search_terms = re.findall(r'\b\w+\b', query)
        search_terms = [term for term in search_terms if len(term) >= 3]
        
        if not search_terms:
            return []
        
        # Find matching verses
        verse_scores = {}
        
        for term in search_terms:
            matching_verses = search_index.get(term, set())
            for verse_key in matching_verses:
                if verse_key not in verse_scores:
                    verse_scores[verse_key] = {'score': 0, 'matched_fields': set()}
                verse_scores[verse_key]['score'] += 1
                verse_scores[verse_key]['matched_fields'].add(term)
        
        # Calculate relevance scores and create results
        results = []
        for verse_key, score_data in verse_scores.items():
            verse_data = data[verse_key]
            
            # Calculate relevance score based on:
            # 1. Number of matching terms
            # 2. Frequency of matches in text
            # 3. Position of matches (earlier = better)
            base_score = score_data['score'] / len(search_terms)
            
            # Boost score for exact phrase matches
            full_text = f"{verse_data.translation} {verse_data.tafsir}".lower()
            if query in full_text:
                base_score *= 2
            
            # Boost score for matches in translation vs tafsir
            translation_matches = sum(1 for term in score_data['matched_fields'] 
                                    if term in verse_data.translation.lower())
            if translation_matches > 0:
                base_score *= 1.5
            
            results.append(SearchResult(
                verse_data=verse_data,
                relevance_score=base_score,
                matched_fields=list(score_data['matched_fields'])
            ))
        
        # Sort by relevance score (highest first)
        results.sort(key=lambda r: r.relevance_score, reverse=True)
        
        return results[:limit]
    
    def get_verses_containing_words(self, words: List[str]) -> List[VerseData]:
        """Get all verses containing any of the specified words."""
        data = self.data_loader.load_data()
        matching_verses = []
        
        # Convert words to lowercase for case-insensitive search
        words_lower = [word.lower() for word in words]
        
        for verse_data in data.values():
            text_content = f"{verse_data.translation} {verse_data.tafsir}".lower()
            
            # Check if any of the words appear in the content
            if any(word in text_content for word in words_lower):
                matching_verses.append(verse_data)
        
        return matching_verses
    
    def get_daily_verse(self, date_seed: Optional[str] = None) -> VerseData:
        """Get a consistent verse for a specific date."""
        import datetime
        
        if date_seed is None:
            date_seed = datetime.date.today().strftime('%Y-%m-%d')
        
        # Use date as random seed for consistent daily verses
        random.seed(date_seed)
        verse = self.get_random_verse()
        random.seed()  # Reset random seed
        
        return verse
    
    def get_verse_context(self, verse_key: str, context_size: int = 2) -> Dict[str, List[VerseData]]:
        """Get verses before and after the specified verse for context."""
        verse_data = self.get_verse_by_key(verse_key)
        if not verse_data:
            return {'before': [], 'current': [], 'after': []}
        
        surah_verses = self.get_verses_by_surah(verse_data.surah)
        
        # Find the current verse index
        current_index = None
        for i, v in enumerate(surah_verses):
            if v.verse_key == verse_key:
                current_index = i
                break
        
        if current_index is None:
            return {'before': [], 'current': [verse_data], 'after': []}
        
        # Get context verses
        start_index = max(0, current_index - context_size)
        end_index = min(len(surah_verses), current_index + context_size + 1)
        
        before = surah_verses[start_index:current_index]
        after = surah_verses[current_index + 1:end_index]
        
        return {
            'before': before,
            'current': [verse_data],
            'after': after
        }
    
    def get_surah_statistics(self) -> Dict[int, Dict[str, int]]:
        """Get statistics for all surahs."""
        data = self.data_loader.load_data()
        stats = {}
        
        for verse_data in data.values():
            surah_num = verse_data.surah
            if surah_num not in stats:
                stats[surah_num] = {
                    'verse_count': 0,
                    'avg_translation_length': 0,
                    'avg_tafsir_length': 0,
                    'total_translation_words': 0,
                    'total_tafsir_words': 0
                }
            
            stats[surah_num]['verse_count'] += 1
            stats[surah_num]['total_translation_words'] += len(verse_data.translation.split())
            stats[surah_num]['total_tafsir_words'] += len(verse_data.tafsir.split())
        
        # Calculate averages
        for surah_stats in stats.values():
            verse_count = surah_stats['verse_count']
            surah_stats['avg_translation_length'] = surah_stats['total_translation_words'] // verse_count
            surah_stats['avg_tafsir_length'] = surah_stats['total_tafsir_words'] // verse_count
        
        return stats
    
    def get_random_verses_by_theme(self, theme_words: List[str], count: int = 5) -> List[VerseData]:
        """Get random verses related to a theme (based on keywords)."""
        matching_verses = self.get_verses_containing_words(theme_words)
        
        if not matching_verses:
            return []
        
        # Return random selection from matching verses
        if len(matching_verses) <= count:
            return matching_verses
        
        return random.sample(matching_verses, count)
    
    def validate_verse_key_format(self, verse_key: str) -> bool:
        """Validate verse key format (surah:ayah)."""
        if not isinstance(verse_key, str):
            return False
        
        parts = verse_key.split(':')
        if len(parts) != 2:
            return False
        
        try:
            surah, ayah = int(parts[0]), int(parts[1])
            return 1 <= surah <= 114 and ayah >= 1
        except ValueError:
            return False