"""HTML generation and template management."""

import re
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
import json

from .data_loader import VerseData
from config.settings import Config

logger = logging.getLogger(__name__)


class HTMLCleaner:
    """Utility class for cleaning HTML content, especially Tafsir text."""
    
    @staticmethod
    def clean_tafsir_html(text: str) -> str:
        """
        Clean Tafsir HTML content while preserving structure.
        
        Args:
            text: Raw HTML text from Tafsir
            
        Returns:
            Cleaned HTML text
        """
        if not text:
            return ""
        
        # Remove script and style tags completely
        text = re.sub(r'<script.*?>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style.*?>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove specific span tags that contain "gray" class or other non-semantic formatting
        text = re.sub(r'<span\s+(?:class="[^"]*?")?[^>]*>(.*?)</span>', 
                     r'\1', text, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove empty p tags or p tags containing only whitespace
        text = re.sub(r'<p[^>]*>\s*</p>', '', text, flags=re.DOTALL)
        
        # Allow specific HTML tags for formatting
        allowed_tags = ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'div', 'em', 'strong', 'b', 'i', 'br', 'ul', 'ol', 'li']
        pattern = r'<(?!/?(?:' + '|'.join(allowed_tags) + r')\b)[^>]*>'
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Remove original newlines, rely on HTML formatting
        text = text.replace('\\n', '')
        
        # Clean up excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        return text
    
    @staticmethod
    def clean_arabic_text(text: str) -> str:
        """
        Clean Arabic text by removing HTML tags while preserving diacritics.
        
        Args:
            text: Arabic text possibly containing HTML
            
        Returns:
            Clean Arabic text
        """
        if not text:
            return ""
        
        # Remove HTML tags but preserve the text content
        cleaned = re.sub(r'<.*?>', '', text)
        
        # Clean up excessive whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned)
        cleaned = cleaned.strip()
        
        return cleaned


class HTMLGenerator:
    """Generate HTML content for displaying verses."""
    
    def __init__(self, config: Config):
        self.config = config
        self.html_cleaner = HTMLCleaner()
    
    def generate_verse_html(self, verse_data: VerseData, 
                           template_style: str = "modern",
                           include_context: bool = False,
                           context_verses: Optional[List[VerseData]] = None) -> str:
        """
        Generate HTML for a single verse display.
        
        Args:
            verse_data: The verse to display
            template_style: Style template to use
            include_context: Whether to include surrounding verses
            context_verses: List of context verses if include_context is True
            
        Returns:
            Complete HTML string
        """
        # Clean the text content
        clean_arabic = self.html_cleaner.clean_arabic_text(verse_data.arabic_text)
        clean_tafsir = self.html_cleaner.clean_tafsir_html(verse_data.tafsir)
        
        # Prepare template variables
        template_vars = {
            'verse_key': verse_data.verse_key,
            'surah_number': verse_data.surah,
            'ayah_number': verse_data.ayah,
            'arabic_text': clean_arabic,
            'translation_text': verse_data.translation,
            'tafsir_content': clean_tafsir,
            'page_title': f"Ayah {verse_data.verse_key}",
        }
        
        if template_style == "modern":\n            return self._generate_modern_template(template_vars, include_context, context_verses)
        elif template_style == "minimal":
            return self._generate_minimal_template(template_vars)
        else:
            return self._generate_classic_template(template_vars)
    
    def _generate_modern_template(self, vars: Dict[str, Any], 
                                include_context: bool = False,
                                context_verses: Optional[List[VerseData]] = None) -> str:
        """Generate modern responsive template."""
        
        # Context section HTML
        context_html = ""
        if include_context and context_verses:
            context_items = []
            for cv in context_verses:
                context_items.append(f'''
                <div class="context-verse p-3 bg-gray-50 rounded border-l-4 border-blue-200">
                    <p class="text-sm text-gray-600 mb-1">Verse {cv.verse_key}</p>
                    <p class="font-amiri text-lg text-right mb-2" dir="rtl">{self.html_cleaner.clean_arabic_text(cv.arabic_text)}</p>
                    <p class="text-sm text-gray-700">{cv.translation}</p>
                </div>
                ''')
            context_html = f'''
            <section class="context-section mb-8">
                <h3 class="text-xl font-semibold text-gray-700 mb-4">Context</h3>
                <div class="space-y-3">
                    {"".join(context_items)}
                </div>
            </section>
            '''
        
        return f'''<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{vars['page_title']} - Ayah App</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Amiri:wght@400;700&family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        body {{ font-family: 'Inter', sans-serif; }}
        .font-amiri {{ font-family: 'Amiri', serif; }}
        .tafsir p, .tafsir h2, .tafsir h3, .tafsir div {{ margin-bottom: 1em; }}
        .tafsir h2, .tafsir h3 {{ font-size: 1.25em; font-weight: 600; margin-top: 1.5em; color: #374151; }}
        .verse-actions {{ opacity: 0; transition: opacity 0.3s ease; }}
        .verse-container:hover .verse-actions {{ opacity: 1; }}
    </style>
</head>
<body class="bg-gradient-to-br from-blue-50 via-white to-indigo-50 min-h-screen">
    <!-- Navigation -->
    <nav class="bg-white shadow-sm border-b">
        <div class="max-w-4xl mx-auto px-4 py-3">
            <div class="flex justify-between items-center">
                <h1 class="text-2xl font-bold text-indigo-800">Ayah App</h1>
                <div class="flex space-x-4">
                    <button id="new-verse-btn" class="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition duration-200">
                        New Verse
                    </button>
                    <button id="bookmark-btn" class="text-indigo-600 hover:text-indigo-800 px-3 py-2 rounded-lg text-sm font-medium transition duration-200">
                        Bookmark
                    </button>
                </div>
            </div>
        </div>
    </nav>

    <main class="max-w-4xl mx-auto px-4 py-8">
        <!-- Main Verse Container -->
        <div class="verse-container bg-white rounded-2xl shadow-xl p-8 mb-8 relative">
            <!-- Verse Actions -->
            <div class="verse-actions absolute top-6 right-6 flex space-x-2">
                <button class="share-btn p-2 text-gray-400 hover:text-indigo-600 rounded-lg transition duration-200">
                    <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                        <path d="M15 8a3 3 0 10-2.977-2.63l-4.94 2.47a3 3 0 100 4.319l4.94 2.47a3 3 0 10.895-1.789l-4.94-2.47a3.027 3.027 0 000-.74l4.94-2.47C13.456 7.68 14.19 8 15 8z"></path>
                    </svg>
                </button>
                <button class="copy-btn p-2 text-gray-400 hover:text-indigo-600 rounded-lg transition duration-200">
                    <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                        <path d="M8 2a1 1 0 000 2h2a1 1 0 100-2H8z"></path>
                        <path d="M3 5a2 2 0 012-2 3 3 0 003 3h6a3 3 0 003-3 2 2 0 012 2v6h-4.586l1.293-1.293a1 1 0 00-1.414-1.414l-3 3a1 1 0 000 1.414l3 3a1 1 0 001.414-1.414L12.414 13H17v3a2 2 0 01-2 2H5a2 2 0 01-2-2V5z"></path>
                    </svg>
                </button>
            </div>

            <!-- Arabic Text -->
            <section class="text-center mb-8 bg-gradient-to-r from-blue-50 to-indigo-50 p-6 rounded-xl">
                <p class="font-amiri text-4xl leading-relaxed text-gray-900 mb-4 font-bold" 
                   lang="ar" dir="rtl" id="arabic-text">
                    {vars['arabic_text']}
                </p>
                <div class="text-lg text-indigo-600 font-medium">
                    <span class="inline-flex items-center bg-white px-4 py-2 rounded-full shadow-sm">
                        Sūrah {vars['surah_number']}, Āyah {vars['ayah_number']} 
                        <span class="ml-2 text-sm text-gray-500">({vars['verse_key']})</span>
                    </span>
                </div>
            </section>

            <!-- New Verse Button -->
            <div class="text-center mb-8">
                <button id="generate-ayah-btn" class="bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 text-white font-semibold py-3 px-8 rounded-xl shadow-lg transform transition duration-300 hover:scale-105 focus:outline-none focus:ring-4 focus:ring-indigo-300">
                    <span class="flex items-center">
                        <svg class="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clip-rule="evenodd"></path>
                        </svg>
                        Generate New Verse
                    </span>
                </button>
            </div>
        </div>

        <!-- Translation Section -->
        <section class="bg-white rounded-xl shadow-lg p-6 mb-6">
            <h2 class="text-2xl font-semibold text-gray-800 mb-4 flex items-center">
                <svg class="w-6 h-6 mr-2 text-indigo-600" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M7 2a1 1 0 011 1v1h3a1 1 0 110 2H9.578a18.87 18.87 0 01-1.724 4.78c.29.354.596.696.914 1.026a1 1 0 11-1.44 1.389c-.188-.196-.373-.396-.554-.6a19.098 19.098 0 01-3.107 3.567 1 1 0 01-1.334-1.49 17.087 17.087 0 003.13-3.733 18.992 18.992 0 01-1.487-2.494 1 1 0 111.79-.89c.234.47.489.928.764 1.372.417-.934.752-1.913.997-2.927H3a1 1 0 110-2h3V3a1 1 0 011-1zm6 6a1 1 0 01.894.553l2.991 5.982a.869.869 0 01.02.037l.99 1.98a1 1 0 11-1.79.895L15.383 16h-4.764l-.724 1.447a1 1 0 11-1.788-.894l.99-1.98.019-.038 2.99-5.982A1 1 0 0113 8zm-1.382 6h2.764L13 12.236 11.618 14z" clip-rule="evenodd"></path>
                </svg>
                Translation
            </h2>
            <p class="text-lg text-gray-700 leading-relaxed" id="translation-text">
                {vars['translation_text']}
            </p>
        </section>

        <!-- Tafsir Section -->
        <section class="bg-white rounded-xl shadow-lg p-6">
            <h2 class="text-2xl font-semibold text-gray-800 mb-4 flex items-center">
                <svg class="w-6 h-6 mr-2 text-indigo-600" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M9 4.804A7.968 7.968 0 005.5 4c-1.255 0-2.443.29-3.5.804v10A7.969 7.969 0 015.5 14c1.669 0 3.218.51 4.5 1.385A7.962 7.962 0 0114.5 14c1.255 0 2.443.29 3.5.804v-10A7.968 7.968 0 0014.5 4c-1.255 0-2.443.29-3.5.804V12a1 1 0 11-2 0V4.804z"></path>
                </svg>
                Commentary (Tafsir)
            </h2>
            <div class="tafsir text-base text-gray-600 leading-relaxed space-y-4" id="tafsir-content">
                {clean_tafsir}
            </div>
        </section>

        {context_html}
    </main>

    <!-- Footer -->
    <footer class="bg-white border-t mt-16">
        <div class="max-w-4xl mx-auto px-4 py-6">
            <div class="text-center text-gray-600 text-sm">
                <p>Ayah App - Daily Quran verses with translations and commentary</p>
                <p class="mt-1">Translation: Taqi Usmani | Commentary: Ibn Kathir</p>
            </div>
        </div>
    </footer>

    <script>
        // JavaScript for interactive functionality will be loaded from external file
        // This keeps the HTML smaller and allows for caching
    </script>
    <script src="/static/js/app.js"></script>
</body>
</html>'''

    def _generate_minimal_template(self, vars: Dict[str, Any]) -> str:
        """Generate minimal template for fast loading."""
        return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{vars['page_title']}</title>
    <style>
        body {{ font-family: system-ui, -apple-system, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; line-height: 1.6; }}
        .arabic {{ font-family: "Noto Sans Arabic", "Amiri", serif; font-size: 2em; text-align: center; direction: rtl; margin: 20px 0; }}
        .verse-info {{ text-align: center; color: #666; margin: 10px 0; }}
        .translation {{ margin: 20px 0; font-size: 1.1em; }}
        .tafsir {{ margin: 20px 0; color: #444; }}
        button {{ background: #0066cc; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; }}
        button:hover {{ background: #0052a3; }}
    </style>
</head>
<body>
    <div class="verse-info">Verse {vars['verse_key']}</div>
    <div class="arabic">{vars['arabic_text']}</div>
    <div class="translation">{vars['translation_text']}</div>
    <div class="tafsir">{self.html_cleaner.clean_tafsir_html(vars['tafsir_content'])}</div>
    <div style="text-align: center; margin: 30px 0;">
        <button onclick="window.location.reload()">New Verse</button>
    </div>
</body>
</html>'''

    def generate_static_verse_json(self, verse_data: VerseData) -> str:
        """Generate JSON representation of verse for API/AJAX calls."""
        return json.dumps({
            'verse_key': verse_data.verse_key,
            'surah': verse_data.surah,
            'ayah': verse_data.ayah,
            'arabic_text': self.html_cleaner.clean_arabic_text(verse_data.arabic_text),
            'translation': verse_data.translation,
            'tafsir': self.html_cleaner.clean_tafsir_html(verse_data.tafsir),
        }, ensure_ascii=False, indent=2)

    def generate_email_html(self, verse_data: VerseData, subscriber_name: str = "") -> str:
        """Generate HTML for email newsletters."""
        greeting = f"Dear {subscriber_name}," if subscriber_name else "Peace be upon you,"
        
        return f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
        .content {{ background: white; padding: 30px; border: 1px solid #e0e0e0; }}
        .arabic {{ font-family: "Noto Sans Arabic", "Amiri", serif; font-size: 24px; text-align: center; direction: rtl; margin: 20px 0; line-height: 1.8; }}
        .verse-info {{ text-align: center; color: #666; margin: 15px 0; font-weight: bold; }}
        .section {{ margin: 25px 0; }}
        .section h3 {{ color: #667eea; border-bottom: 2px solid #f0f0f0; padding-bottom: 10px; }}
        .footer {{ background: #f8f9fa; padding: 20px; text-align: center; font-size: 12px; color: #666; border-radius: 0 0 10px 10px; }}
        .unsubscribe {{ margin-top: 15px; }}
        .unsubscribe a {{ color: #666; text-decoration: none; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🌙 Daily Ayah</h1>
        <p>Your daily verse from the Holy Quran</p>
    </div>
    
    <div class="content">
        <p>{greeting}</p>
        
        <div class="verse-info">Sūrah {verse_data.surah}, Āyah {verse_data.ayah} ({verse_data.verse_key})</div>
        
        <div class="arabic">{self.html_cleaner.clean_arabic_text(verse_data.arabic_text)}</div>
        
        <div class="section">
            <h3>Translation</h3>
            <p>{verse_data.translation}</p>
        </div>
        
        <div class="section">
            <h3>Commentary (Tafsir)</h3>
            <div>{self.html_cleaner.clean_tafsir_html(verse_data.tafsir)}</div>
        </div>
        
        <p style="margin-top: 30px; font-style: italic; color: #666;">
            May this verse bring guidance and peace to your day.
        </p>
    </div>
    
    <div class="footer">
        <p>© Ayah App - Daily Quranic Inspiration</p>
        <p>Translation by Taqi Usmani | Commentary by Ibn Kathir</p>
        <div class="unsubscribe">
            <a href="{{{{ unsubscribe_url }}}}">Unsubscribe from daily emails</a>
        </div>
    </div>
</body>
</html>'''