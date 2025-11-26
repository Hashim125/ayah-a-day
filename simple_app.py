"""Simple Ayah App - A web version with Verse of the Day, Random Generator, and Search."""

import json
import random
import re
import datetime
from flask import Flask, render_template_string, request, jsonify
import config

app = Flask(__name__, static_folder=config.STATIC_FOLDER, static_url_path='/static')

# Global data storage (loaded once at startup)
unified_data = {}
tafsir_cache = {}  # Cache for resolved tafsir references

def load_data():
    """Load and unify JSON data files with proper tafsir reference resolution."""
    global unified_data, tafsir_cache

    # Validate data directory and files
    is_valid, message = config.validate_data_directory()
    if not is_valid:
        print(f"❌ Error: {message}")
        return False

    try:
        # Load JSON files with better error handling
        print("📚 Loading Arabic text...")
        with open(config.get_data_file_path('quran'), 'r', encoding='utf-8') as f:
            quran_data = json.load(f)

        print("🔤 Loading translations...")
        with open(config.get_data_file_path('translation'), 'r', encoding='utf-8') as f:
            translation_data = json.load(f)

        print("📖 Loading tafsir...")
        with open(config.get_data_file_path('tafsir'), 'r', encoding='utf-8') as f:
            tafsir_data = json.load(f)
            
        print(f"Loaded {len(quran_data)} Arabic verses, {len(translation_data)} translations, {len(tafsir_data)} tafsir entries")
        
        # First pass: Build tafsir cache and analyze reference patterns
        reference_count = 0
        direct_tafsir_count = 0
        
        for verse_key, tafsir_entry in tafsir_data.items():
            if isinstance(tafsir_entry, dict):
                # This is a complete tafsir entry
                tafsir_text = tafsir_entry.get('text', '')
                tafsir_cache[verse_key] = tafsir_text
                direct_tafsir_count += 1
            elif isinstance(tafsir_entry, str):
                # This is a reference to another verse
                if ':' in tafsir_entry and len(tafsir_entry) < 10:
                    # It's a verse reference like "1:6"
                    reference_count += 1
                    tafsir_cache[verse_key] = tafsir_entry  # Store the reference for now
                else:
                    # It's direct text
                    tafsir_cache[verse_key] = tafsir_entry
                    direct_tafsir_count += 1
            else:
                tafsir_cache[verse_key] = ""
        
        print(f"Tafsir analysis: {direct_tafsir_count} direct entries, {reference_count} references")
        
        # Second pass: Resolve tafsir references
        for verse_key in tafsir_cache.keys():
            tafsir_cache[verse_key] = resolve_tafsir_reference(verse_key, tafsir_data, max_depth=3)
        
        # Third pass: Unify all data
        unified_data = {}
        for verse_key, q_data in quran_data.items():
            if verse_key in translation_data and verse_key in tafsir_cache:
                # Handle translation format
                translation_entry = translation_data[verse_key]
                if isinstance(translation_entry, dict) and 't' in translation_entry:
                    current_translation_text = translation_entry['t']
                elif isinstance(translation_entry, str):
                    current_translation_text = translation_entry
                else:
                    current_translation_text = ""
                
                # Get resolved tafsir
                current_tafsir_text = tafsir_cache[verse_key]
                
                unified_data[verse_key] = {
                    "quran_text": q_data["text"],
                    "surah": q_data["surah"],
                    "ayah": q_data["ayah"],
                    "verse_key": verse_key,
                    "translation_text": current_translation_text,
                    "tafsir_text": current_tafsir_text
                }
        
        print(f"Successfully unified {len(unified_data)} verses with resolved tafsir references")
        
        # Check some examples
        examples = ['1:7', '2:255', '18:1']
        for ex in examples:
            if ex in unified_data:
                tafsir_len = len(unified_data[ex]['tafsir_text'])
                print(f"  {ex}: Tafsir length = {tafsir_len} chars")
        
    except Exception as e:
        print(f"Error loading data: {e}")
        return False
    
    return True

def resolve_tafsir_reference(verse_key, tafsir_data, max_depth=None, depth=0):
    """Resolve tafsir references by following the chain."""
    if max_depth is None:
        max_depth = config.MAX_TAFSIR_REFERENCE_DEPTH
    if depth >= max_depth:
        return f"[Tafsir reference chain too deep for {verse_key}]"
    
    if verse_key not in tafsir_data:
        return ""
    
    entry = tafsir_data[verse_key]
    
    if isinstance(entry, dict):
        # Direct tafsir content
        return entry.get('text', '')
    elif isinstance(entry, str):
        # Check if it's a verse reference
        if ':' in entry and len(entry.strip()) < 10 and entry.strip().replace(':', '').replace('.', '').isdigit():
            # It's a reference, follow it
            referenced_verse = entry.strip()
            if referenced_verse in tafsir_data:
                return resolve_tafsir_reference(referenced_verse, tafsir_data, max_depth, depth + 1)
            else:
                return f"[Referenced tafsir not found: {referenced_verse}]"
        else:
            # It's direct text content
            return entry
    else:
        return ""

def clean_tafsir_html(text):
    """Clean Tafsir HTML (same as your original function)."""
    if not text:
        return ""
    
    # Remove script and style tags completely
    text = re.sub(r'<script.*?>.*?</script>', '', text, flags=re.DOTALL)
    text = re.sub(r'<style.*?>.*?</style>', '', text, flags=re.DOTALL)
    
    # Remove specific span tags
    text = re.sub(r'<span\s+(?:class="[^"]*?")?[^>]*>(.*?)</span>', r'\1', text, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove empty p tags
    text = re.sub(r'<p[^>]*>\s*</p>', '', text, flags=re.DOTALL)
    
    # Allow basic HTML tags
    text = re.sub(r'<(?!/?(?:p|h2|div|em|strong|b|i|br|ul|ol|li)\b)[^>]*>', '', text)
    
    # Remove newlines
    text = text.replace('\n', '')
    return text

def get_verse_of_the_day():
    """Get the same verse for everyone today."""
    if not unified_data:
        return None
    
    # Use today's date as seed for consistent daily verse
    today = datetime.date.today()
    date_string = today.strftime('%Y-%m-%d')
    
    # Set random seed based on date
    random.seed(date_string)
    verse_key = random.choice(list(unified_data.keys()))
    random.seed()  # Reset random seed
    
    return get_verse_data(verse_key)

def get_random_ayah():
    """Get a random ayah (different each time)."""
    if not unified_data:
        return None
    
    random_verse_key = random.choice(list(unified_data.keys()))
    return get_verse_data(random_verse_key)

def get_verse_data(verse_key):
    """Get formatted verse data for a specific verse key."""
    if verse_key not in unified_data:
        return None
    
    selected_ayah_data = unified_data[verse_key]
    
    clean_ayah_text = re.sub(r'<.*?>', '', selected_ayah_data["quran_text"])
    translation_text = selected_ayah_data["translation_text"]
    tafsir_html_content = clean_tafsir_html(selected_ayah_data["tafsir_text"])
    
    return {
        "clean_ayah_text": clean_ayah_text,
        "translation_text": translation_text,
        "tafsir_html_content": tafsir_html_content,
        "surah_number": selected_ayah_data["surah"],
        "ayah_number": selected_ayah_data["ayah"],
        "verse_key": selected_ayah_data["verse_key"]
    }

def get_verse_themes():
    """Get common Quranic themes for categorization from config."""
    return config.VERSE_THEMES

def search_by_theme(theme_name):
    """Search verses by thematic category using regular search."""
    themes = get_verse_themes()
    if theme_name not in themes:
        print(f"Theme '{theme_name}' not found in available themes: {list(themes.keys())}")
        return []
    
    # Use the first few keywords from the theme to search
    theme_keywords = themes[theme_name][:3]  # Take first 3 keywords
    print(f"Searching for theme '{theme_name}' with keywords: {theme_keywords}")
    
    # Try each keyword and combine results
    all_results = []
    seen_verses = set()
    
    for keyword in theme_keywords:
        results = search_verses(keyword, max_results=15)
        print(f"Keyword '{keyword}' found {len(results)} results")
        for result in results:
            verse_key = result.get('verse_key')
            if verse_key not in seen_verses:
                seen_verses.add(verse_key)
                all_results.append(result)
    
    print(f"Total unique results for theme '{theme_name}': {len(all_results)}")
    return all_results[:config.MAX_THEME_RESULTS]

def search_verses(query, max_results=None):
    """Enhanced search function with theme support."""
    if max_results is None:
        max_results = config.MAX_SEARCH_RESULTS

    if not query or not unified_data:
        return []

    # Input validation and sanitization
    query = query.strip()
    if len(query) > config.MAX_QUERY_LENGTH:
        query = query[:config.MAX_QUERY_LENGTH]
    if len(query) < config.MIN_QUERY_LENGTH:
        return []

    query_lower = query.lower()
    results = []
    
    # Check if query looks like a verse reference (e.g., "2:255", "2:1-10")
    verse_ref_pattern = r'^(\d+):(\d+)(?:-(\d+))?$'
    match = re.match(verse_ref_pattern, query.strip())
    
    if match:
        surah = int(match.group(1))
        start_ayah = int(match.group(2))
        end_ayah = int(match.group(3)) if match.group(3) else start_ayah
        
        # Search by verse reference
        for verse_key, verse_data in unified_data.items():
            if verse_data["surah"] == surah and start_ayah <= verse_data["ayah"] <= end_ayah:
                verse_result = get_verse_data(verse_key)
                if verse_result:
                    results.append(verse_result)
                
                if len(results) >= max_results:
                    break
    else:
        # Search by text content
        for verse_key, verse_data in unified_data.items():
            translation = verse_data["translation_text"].lower()
            tafsir = verse_data["tafsir_text"].lower()
            
            if query_lower in translation or query_lower in tafsir:
                verse_result = get_verse_data(verse_key)
                if verse_result:
                    results.append(verse_result)
                
                if len(results) >= max_results:
                    break
    
    return results

# Navigation HTML
NAVIGATION = '''
<nav class="bg-white shadow-sm border-b mb-6">
    <div class="max-w-4xl mx-auto px-4 py-4">
        <div class="flex flex-col sm:flex-row justify-between items-center gap-4">
            <h1 class="text-xl sm:text-2xl font-bold text-indigo-800">
                <a href="/" class="hover:text-indigo-600">🌙 Ayah App</a>
            </h1>
            <div class="flex items-center flex-wrap justify-center gap-4 sm:gap-6">
                <a href="/" class="text-gray-700 hover:text-indigo-600 font-medium text-sm sm:text-base">Verse of the Day</a>
                <a href="/random" class="text-gray-700 hover:text-indigo-600 font-medium text-sm sm:text-base">Random Ayah</a>
                <a href="/search" class="text-gray-700 hover:text-indigo-600 font-medium text-sm sm:text-base">Search</a>
                <a href="/bookmarks" class="text-gray-700 hover:text-indigo-600 font-medium text-sm sm:text-base">⭐ Bookmarks</a>
            </div>
        </div>
    </div>
</nav>
'''

# Base HTML Template
BASE_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }} - Ayah App</title>
    <meta name="description" content="{{ description|default('Daily Quranic verses with translations and Tafsir commentary. Discover the beauty and wisdom of the Quran with verse of the day, random ayah generator, and powerful search.', true) }}">
    <meta name="keywords" content="Quran, Ayah, Tafsir, Ibn Kathir, Islamic, Verse of the Day, Translation, Taqi Usmani">

    <!-- Open Graph / Facebook -->
    <meta property="og:type" content="website">
    <meta property="og:url" content="{{ og_url|default('https://ayahapp.com', true) }}">
    <meta property="og:title" content="{{ og_title|default(title ~ ' - Ayah App', true) }}">
    <meta property="og:description" content="{{ og_description|default('Daily Quranic verses with translations and Tafsir commentary', true) }}">
    <meta property="og:image" content="{{ og_image|default('https://ayahapp.com/static/og-image.png', true) }}">

    <!-- Twitter -->
    <meta property="twitter:card" content="summary_large_image">
    <meta property="twitter:url" content="{{ og_url|default('https://ayahapp.com', true) }}">
    <meta property="twitter:title" content="{{ og_title|default(title ~ ' - Ayah App', true) }}">
    <meta property="twitter:description" content="{{ og_description|default('Daily Quranic verses with translations and Tafsir commentary', true) }}">
    <meta property="twitter:image" content="{{ og_image|default('https://ayahapp.com/static/og-image.png', true) }}">

    <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🌙</text></svg>">
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Amiri:wght@400;700&family=Inter:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Inter', sans-serif; }
        .font-amiri { font-family: 'Amiri', serif; }
        .tafsir p, .tafsir h2, .tafsir div { margin-bottom: 1em; }
        .tafsir h2 { font-size: 1.25em; font-weight: 600; margin-top: 1.5em; color: #374151; }
        .active-nav { color: #4F46E5 !important; font-weight: 600; }
    </style>
</head>
<body class="bg-gradient-to-br from-blue-50 to-indigo-100 min-h-screen">
    {{ navigation|safe }}
    
    <main class="max-w-4xl mx-auto px-4 pb-8">
        {{ content|safe }}
    </main>
    
    <footer class="bg-white border-t mt-16">
        <div class="max-w-4xl mx-auto px-4 py-6 text-center text-gray-600 text-sm">
            <p class="font-medium">Translation: Taqi Usmani | Commentary: Ibn Kathir</p>
            <p class="mt-1 text-xs">Tafsir references are automatically resolved for complete commentary</p>
            <p class="mt-2 text-xs text-gray-500">{{ stats_text|default('', true) }}</p>
        </div>
    </footer>
    
    <script>
        // Loading indicator for buttons
        document.addEventListener('DOMContentLoaded', function() {
            const loadingBtn = document.getElementById('loading-btn');
            if (loadingBtn) {
                loadingBtn.addEventListener('click', function(e) {
                    const btnText = this.querySelector('.btn-text');
                    const spinner = this.querySelector('.loading-spinner');
                    if (btnText && spinner) {
                        btnText.classList.add('hidden');
                        spinner.classList.remove('hidden');
                        this.disabled = true;
                    }
                });
            }
            
            // Initialize bookmarks display
            updateBookmarkDisplay();
        });
        
        // Bookmark functionality using localStorage
        function toggleBookmark(verseKey) {
            let bookmarks = JSON.parse(localStorage.getItem('ayah-bookmarks') || '[]');
            const index = bookmarks.indexOf(verseKey);
            
            if (index === -1) {
                bookmarks.push(verseKey);
                showNotification('Verse bookmarked! ⭐');
            } else {
                bookmarks.splice(index, 1);
                showNotification('Bookmark removed');
            }
            
            localStorage.setItem('ayah-bookmarks', JSON.stringify(bookmarks));
            updateBookmarkDisplay();
        }
        
        function updateBookmarkDisplay() {
            const bookmarks = JSON.parse(localStorage.getItem('ayah-bookmarks') || '[]');
            bookmarks.forEach(verseKey => {
                const icon = document.getElementById('bookmark-icon-' + verseKey);
                if (icon) {
                    icon.textContent = '★';
                    icon.parentElement.classList.add('text-yellow-600');
                }
            });
        }
        
        // Copy verse permalink
        function copyVerseLink(verseKey) {
            const url = window.location.origin + '/verse/' + verseKey;
            navigator.clipboard.writeText(url).then(function() {
                showNotification('Link copied! 📋');
            }).catch(function() {
                // Fallback for older browsers
                const textArea = document.createElement('textarea');
                textArea.value = url;
                document.body.appendChild(textArea);
                textArea.select();
                document.execCommand('copy');
                document.body.removeChild(textArea);
                showNotification('Link copied! 📋');
            });
        }
        
        // Share on WhatsApp
        function shareWhatsApp(verseKey, arabicText, translation) {
            const message = `🌙 ${arabicText}\\n\\n"${translation}"\\n\\nSūrah ${verseKey}\\n\\n${window.location.origin}/verse/${verseKey}`;
            const url = `https://wa.me/?text=${encodeURIComponent(message)}`;
            window.open(url, '_blank');
        }
        
        // Share on Twitter
        function shareTwitter(verseKey, translation) {
            const message = `"${translation}" - Quran ${verseKey}\\n\\n${window.location.origin}/verse/${verseKey}`;
            const url = `https://twitter.com/intent/tweet?text=${encodeURIComponent(message)}`;
            window.open(url, '_blank');
        }

        // Show Instagram style options modal
        function showInstagramOptions(verseKey, arabicText, translation, surahNumber, ayahNumber) {
            // Create modal
            const modal = document.createElement('div');
            modal.className = 'fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4';
            modal.innerHTML = `
                <div class="bg-white rounded-xl shadow-2xl max-w-md w-full p-6">
                    <div class="flex justify-between items-center mb-4">
                        <h3 class="text-xl font-bold text-gray-800">Choose Instagram Style</h3>
                        <button onclick="this.closest('.fixed').remove()" class="text-gray-500 hover:text-gray-700 text-2xl">×</button>
                    </div>
                    <p class="text-gray-600 mb-4 text-sm">Select a background style for your verse image:</p>
                    <div class="space-y-3">
                        <button onclick="shareInstagram('${verseKey}', '${arabicText}', '${translation}', ${surahNumber}, ${ayahNumber}); this.closest('.fixed').remove();"
                                class="w-full bg-gradient-to-r from-blue-500 to-purple-600 text-white p-4 rounded-lg hover:from-blue-600 hover:to-purple-700 transition-all duration-200 flex items-center justify-between">
                            <span class="font-medium">🕌 Mosque Background</span>
                            <span class="text-xs opacity-75">Beautiful</span>
                        </button>
                        <button onclick="shareInstagramMinimal('${verseKey}', '${arabicText}', '${translation}', ${surahNumber}, ${ayahNumber}); this.closest('.fixed').remove();"
                                class="w-full bg-gradient-to-r from-gray-600 to-gray-800 text-white p-4 rounded-lg hover:from-gray-700 hover:to-gray-900 transition-all duration-200 flex items-center justify-between">
                            <span class="font-medium">⚪ Minimal White</span>
                            <span class="text-xs opacity-75">Professional</span>
                        </button>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
        }
        
        // Generate beautiful Instagram card with mosque background
        function shareInstagram(verseKey, arabicText, translation, surahNumber, ayahNumber) {
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            
            // Instagram story dimensions
            canvas.width = 1080;
            canvas.height = 1920;
            
            // Load the mosque image
            const img = new Image();
            img.onload = function() {
                // Draw the mosque image as background
                ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
                
                // Add a subtle dark overlay to make text readable
                ctx.fillStyle = 'rgba(0, 0, 0, 0.4)';
                ctx.fillRect(0, 0, canvas.width, canvas.height);
                
                // Create a white semi-transparent card in the center for text
                const cardPadding = 80;
                const cardWidth = canvas.width - (cardPadding * 2);
                const cardHeight = 800;
                const cardY = (canvas.height - cardHeight) / 2;
                
                // White card background with rounded corners effect
                ctx.fillStyle = 'rgba(255, 255, 255, 0.95)';
                ctx.fillRect(cardPadding, cardY, cardWidth, cardHeight);
                
                // Add subtle border to the card
                ctx.strokeStyle = 'rgba(0, 0, 0, 0.1)';
                ctx.lineWidth = 2;
                ctx.strokeRect(cardPadding, cardY, cardWidth, cardHeight);
                
                // Center content within the card
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                
                const cardCenterY = cardY + cardHeight / 2;
                
                // Arabic text - elegant and prominent
                ctx.font = 'bold 44px serif';
                ctx.fillStyle = '#1F2937';
                
                const arabicLines = wrapText(ctx, arabicText, cardWidth - 120);
                const arabicHeight = arabicLines.length * 60;
                const arabicStartY = cardCenterY - arabicHeight / 2 - 80;
                
                arabicLines.forEach((line, index) => {
                    ctx.fillText(line, canvas.width / 2, arabicStartY + (index * 60));
                });
                
                // Decorative separator
                const separatorY = arabicStartY + arabicHeight + 40;
                ctx.strokeStyle = '#D1D5DB';
                ctx.lineWidth = 1;
                ctx.beginPath();
                ctx.moveTo(canvas.width / 2 - 100, separatorY);
                ctx.lineTo(canvas.width / 2 + 100, separatorY);
                ctx.stroke();
                
                // Translation - clean and readable
                ctx.font = '32px serif';
                ctx.fillStyle = '#4B5563';
                
                const translationLines = wrapText(ctx, `"${translation}"`, cardWidth - 120);
                const translationStartY = separatorY + 60;
                
                translationLines.forEach((line, index) => {
                    ctx.fillText(line, canvas.width / 2, translationStartY + (index * 45));
                });
                
                // Reference at bottom of card
                ctx.font = 'bold 28px serif';
                ctx.fillStyle = '#6366F1';
                ctx.fillText(`— Quran ${surahNumber}:${ayahNumber} —`, canvas.width / 2, cardY + cardHeight - 60);
                
                // Subtle app watermark at bottom
                ctx.font = '20px serif';
                ctx.fillStyle = 'rgba(255, 255, 255, 0.8)';
                ctx.fillText('🌙 AyahApp.com', canvas.width / 2, canvas.height - 40);
                
                // Convert to download
                canvas.toBlob(function(blob) {
                    const url = URL.createObjectURL(blob);
                    const link = document.createElement('a');
                    link.download = `quran-${verseKey.replace(':', '-')}-mosque.png`;
                    link.href = url;
                    link.click();
                    URL.revokeObjectURL(url);
                    showNotification('🕌 Beautiful mosque card downloaded!');
                }, 'image/png');
            };
            
            img.onerror = function() {
                // Fallback to simple design if image fails to load
                console.error('Failed to load mosque background image');
                showNotification('📱 Using simple design (mosque image unavailable)');
                shareInstagramSimple(verseKey, arabicText, translation, surahNumber, ayahNumber);
            };

            // Load the mosque image with better path handling
            img.crossOrigin = 'anonymous';
            // Try to load the mosque background image
            img.src = window.location.origin + '/static/PXL_20250601_024336215.jpg';
        }
        
        // Minimal white Instagram design
        function shareInstagramMinimal(verseKey, arabicText, translation, surahNumber, ayahNumber) {
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');

            canvas.width = 1080;
            canvas.height = 1920;

            // Clean white background
            ctx.fillStyle = '#FFFFFF';
            ctx.fillRect(0, 0, canvas.width, canvas.height);

            // Add minimal decorative top border
            ctx.fillStyle = '#6366F1';
            ctx.fillRect(0, 0, canvas.width, 8);

            // Center content
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            const centerY = canvas.height / 2;

            // Arabic text - elegant
            ctx.font = 'bold 48px serif';
            ctx.fillStyle = '#111827';
            const arabicLines = wrapText(ctx, arabicText, 920);
            const arabicHeight = arabicLines.length * 70;
            const arabicStartY = centerY - arabicHeight / 2 - 120;

            arabicLines.forEach((line, index) => {
                ctx.fillText(line, canvas.width / 2, arabicStartY + (index * 70));
            });

            // Minimal separator line
            const separatorY = arabicStartY + arabicHeight + 60;
            ctx.strokeStyle = '#E5E7EB';
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.moveTo(canvas.width / 2 - 80, separatorY);
            ctx.lineTo(canvas.width / 2 + 80, separatorY);
            ctx.stroke();

            // Translation - clean
            ctx.font = '34px serif';
            ctx.fillStyle = '#374151';
            const translationLines = wrapText(ctx, `"${translation}"`, 920);
            const translationStartY = separatorY + 70;

            translationLines.forEach((line, index) => {
                ctx.fillText(line, canvas.width / 2, translationStartY + (index * 50));
            });

            // Reference - minimalist
            ctx.font = 'bold 30px serif';
            ctx.fillStyle = '#6366F1';
            const referenceY = translationStartY + (translationLines.length * 50) + 80;
            ctx.fillText(`Quran ${surahNumber}:${ayahNumber}`, canvas.width / 2, referenceY);

            // Subtle bottom watermark
            ctx.font = '18px serif';
            ctx.fillStyle = '#9CA3AF';
            ctx.fillText('🌙 AyahApp', canvas.width / 2, canvas.height - 50);

            canvas.toBlob(function(blob) {
                const url = URL.createObjectURL(blob);
                const link = document.createElement('a');
                link.download = `quran-${verseKey.replace(':', '-')}-minimal.png`;
                link.href = url;
                link.click();
                URL.revokeObjectURL(url);
                showNotification('⚪ Minimal design downloaded!');
            }, 'image/png');
        }

        // Helper function to wrap text
        function wrapText(ctx, text, maxWidth) {
            const words = text.split(' ');
            const lines = [];
            let currentLine = words[0];
            
            for (let i = 1; i < words.length; i++) {
                const word = words[i];
                const width = ctx.measureText(currentLine + ' ' + word).width;
                if (width < maxWidth) {
                    currentLine += ' ' + word;
                } else {
                    lines.push(currentLine);
                    currentLine = word;
                }
            }
            lines.push(currentLine);
            return lines;
        }
        
        // Show notification
        function showNotification(message) {
            const notification = document.createElement('div');
            notification.className = 'fixed top-4 right-4 bg-green-500 text-white px-6 py-3 rounded-lg shadow-lg z-50 transform translate-x-full transition-transform duration-300';
            notification.textContent = message;
            document.body.appendChild(notification);
            
            setTimeout(() => {
                notification.classList.remove('translate-x-full');
            }, 100);
            
            setTimeout(() => {
                notification.classList.add('translate-x-full');
                setTimeout(() => {
                    document.body.removeChild(notification);
                }, 300);
            }, 3000);
        }
        
        // Error handling for missing resources
        window.addEventListener('error', function(e) {
            if (e.target.tagName === 'SCRIPT' || e.target.tagName === 'LINK') {
                console.warn('Failed to load resource:', e.target.src || e.target.href);
                showNotification('Some features may be limited due to network issues');
            }
        });
        
        // Toggle collapsible search result cards
        function toggleCard(cardId) {
            const card = document.getElementById(cardId);
            const icon = document.getElementById('icon-' + cardId.replace('card-', ''));
            
            if (card.classList.contains('hidden')) {
                card.classList.remove('hidden');
                icon.style.transform = 'rotate(180deg)';
            } else {
                card.classList.add('hidden');
                icon.style.transform = 'rotate(0deg)';
            }
        }
    </script>
</body>
</html>
'''

# Verse Display Component
VERSE_DISPLAY = '''
<div class="bg-white rounded-xl shadow-2xl p-8">
    <div class="text-center mb-6">
        <h2 class="text-2xl font-semibold text-gray-800 mb-4">{{ section_title }}</h2>
        {% if show_date %}
        <p class="text-gray-600 mb-4">{{ current_date }}</p>
        {% endif %}
    </div>
    
    <section class="text-center mb-8 bg-gray-50 p-6 rounded-lg">
        <p class="font-amiri text-4xl leading-relaxed text-gray-900 mb-4 font-bold" dir="rtl">
            {{ verse.clean_ayah_text }}
        </p>
        <p class="text-lg text-indigo-600 font-medium">
            Sūrah {{ verse.surah_number }}, Āyah {{ verse.ayah_number }} ({{ verse.verse_key }})
        </p>
    </section>

    <!-- Main Action Button (if present) -->
    {% if show_button %}
    <div class="text-center mb-6">
        <button id="loading-btn" onclick="window.location.href='{{ button_link }}'" class="bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-3 px-8 rounded-lg shadow-lg transform transition duration-300 hover:scale-105">
            <span class="btn-text">{{ button_text }}</span>
            <span class="loading-spinner hidden">
                <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white inline" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Loading...
            </span>
        </button>
    </div>
    {% endif %}
    
    <!-- Share and Bookmark Buttons -->
    <div class="flex flex-wrap justify-center gap-3 mb-8">
        <button onclick="toggleBookmark('{{ verse.verse_key }}')" id="bookmark-btn-{{ verse.verse_key }}" class="bg-gray-100 hover:bg-gray-200 text-gray-700 font-medium py-2 px-4 rounded-lg border border-gray-300 transition duration-300 text-sm" aria-label="Bookmark this verse">
            <span id="bookmark-icon-{{ verse.verse_key }}">☆</span> Bookmark
        </button>

        <button onclick="copyVerseLink('{{ verse.verse_key }}')" class="bg-gray-100 hover:bg-gray-200 text-gray-700 font-medium py-2 px-4 rounded-lg border border-gray-300 transition duration-300 text-sm" aria-label="Copy verse link to clipboard">
            📋 Copy Link
        </button>

        <button onclick="shareWhatsApp('{{ verse.verse_key }}', '{{ verse.clean_ayah_text|replace("'", "\\'")|replace('"', '\\"') }}', '{{ verse.translation_text|replace("'", "\\'")|replace('"', '\\"') }}')" class="bg-green-500 hover:bg-green-600 text-white font-medium py-2 px-4 rounded-lg transition duration-300 text-sm" aria-label="Share verse on WhatsApp">
            📱 WhatsApp
        </button>

        <button onclick="shareTwitter('{{ verse.verse_key }}', '{{ verse.translation_text|replace("'", "\\'")|replace('"', '\\"') }}')" class="bg-blue-400 hover:bg-blue-500 text-white font-medium py-2 px-4 rounded-lg transition duration-300 text-sm" aria-label="Share verse on Twitter">
            🐦 Tweet
        </button>

        <button onclick="showInstagramOptions('{{ verse.verse_key }}', '{{ verse.clean_ayah_text|replace("'", "\\'")|replace('"', '\\"') }}', '{{ verse.translation_text|replace("'", "\\'")|replace('"', '\\"') }}', {{ verse.surah_number }}, {{ verse.ayah_number }})" class="bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600 text-white font-medium py-2 px-4 rounded-lg transition duration-300 text-sm" aria-label="Download verse as Instagram image">
            📷 Instagram
        </button>
    </div>

    <section class="mb-8">
        <h3 class="text-xl font-semibold text-gray-800 mb-3 border-b-2 border-indigo-200 pb-2">Translation</h3>
        <p class="text-lg text-gray-700 leading-relaxed">{{ verse.translation_text }}</p>
    </section>

    {% if verse.tafsir_html_content %}
    <section>
        <h3 class="text-xl font-semibold text-gray-800 mb-3 border-b-2 border-indigo-200 pb-2">Commentary (Tafsir)</h3>
        <div class="tafsir text-base text-gray-600 leading-relaxed">{{ verse.tafsir_html_content|safe }}</div>
    </section>
    {% else %}
    <section>
        <h3 class="text-xl font-semibold text-gray-800 mb-3 border-b-2 border-indigo-200 pb-2">Commentary (Tafsir)</h3>
        <p class="text-gray-500 italic">Commentary not available for this verse.</p>
    </section>
    {% endif %}
</div>
'''

@app.route('/')
def verse_of_the_day():
    """Home page - Verse of the Day (same for everyone)."""
    verse = get_verse_of_the_day()
    if not verse:
        return "Error loading verses. Please check your data files.", 500
    
    today = datetime.date.today()
    formatted_date = today.strftime('%A, %B %d, %Y')
    
    # Add active class to navigation
    nav_with_active = NAVIGATION.replace('href="/"', 'href="/" class="active-nav"')
    
    content = render_template_string(VERSE_DISPLAY, 
                                   verse=verse,
                                   section_title="Verse of the Day",
                                   current_date=formatted_date,
                                   show_date=True,
                                   show_button=False)
    
    return render_template_string(BASE_TEMPLATE,
                                title="Verse of the Day",
                                navigation=nav_with_active,
                                content=content,
                                stats_text=f"📖 {len(unified_data):,} verses available")

@app.route('/random')
def random_page():
    """Random Ayah Generator page."""
    verse = get_random_ayah()
    if not verse:
        return "Error loading verses. Please check your data files.", 500
    
    # Add active class to navigation
    nav_with_active = NAVIGATION.replace('href="/random"', 'href="/random" class="active-nav"')
    
    content = render_template_string(VERSE_DISPLAY, 
                                   verse=verse,
                                   section_title="Random Ayah",
                                   show_date=False,
                                   show_button=True,
                                   button_link="/random",
                                   button_text="Generate New Random Ayah")
    
    return render_template_string(BASE_TEMPLATE, 
                                title="Random Ayah",
                                navigation=nav_with_active,
                                content=content)

@app.route('/search')
def search_page():
    """Enhanced search page with theme categories."""
    from urllib.parse import unquote

    query = request.args.get('q', '').strip()
    theme = request.args.get('theme', '').strip()

    # URL decode the theme (handles "Faith%20&%20Belief" -> "Faith & Belief")
    if theme:
        theme = unquote(theme)

    search_results = []

    # Validate and sanitize inputs
    if query:
        query = query[:config.MAX_QUERY_LENGTH]
    if theme:
        theme = theme[:100]  # Limit theme name length

    if theme:
        search_results = search_by_theme(theme)
        print(f"DEBUG: Theme search for '{theme}' returned {len(search_results)} results")
    elif query:
        search_results = search_verses(query)
    
    # Add active class to navigation
    nav_with_active = NAVIGATION.replace('href="/search"', 'href="/search" class="active-nav"')
    
    # Get available themes for the UI
    themes = get_verse_themes()
    
    # Search page content with theme categories
    search_content = f'''
    <div class="bg-white rounded-xl shadow-lg p-6 mb-6">
        <h2 class="text-2xl font-semibold text-gray-800 mb-4">Search Verses</h2>
        
        <!-- Text Search Form -->
        <form method="GET" class="flex flex-col sm:flex-row gap-2 mb-6">
            <input type="text" name="q" value="{query}" placeholder="Search by text or verse reference (e.g., 2:255, prayer, guidance)" 
                   class="flex-1 px-4 py-3 border border-gray-300 bg-white text-gray-900 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent text-lg">
            <button type="submit" class="bg-indigo-600 hover:bg-indigo-700 text-white px-8 py-3 rounded-lg font-medium transition-colors duration-200 whitespace-nowrap">
                Search
            </button>
        </form>
        
        <!-- Theme Categories -->
        <div class="mb-4">
            <h3 class="text-lg font-medium text-gray-800 mb-3">Browse by Theme:</h3>
            <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
    '''
    
    # Add theme buttons
    from urllib.parse import quote
    for theme_name in themes.keys():
        active_class = "bg-indigo-600 text-white" if theme == theme_name else "bg-gray-100 text-gray-700 hover:bg-gray-200"
        search_content += f'''
                <a href="?theme={quote(theme_name)}" class="{active_class} px-3 py-2 rounded-lg text-sm font-medium transition-colors duration-200 text-center block">
                    {theme_name}
                </a>
        '''
    
    search_content += '''
            </div>
        </div>
        
        <p class="text-sm text-gray-600">
            💡 <strong>Tips:</strong> Search by verse reference (2:255), topic (prayer, forgiveness), or browse themes above
        </p>
    </div>
    '''
    
    if search_results:
        result_title = f"Theme: {theme}" if theme else f'Search Results for "{query}"'
        search_content += f'''
        <div class="space-y-6">
            <div class="flex justify-between items-center">
                <h3 class="text-xl font-bold text-gray-800">{result_title} ({len(search_results)} found)</h3>
                {f'<a href="/search" class="text-indigo-600 hover:text-indigo-800 text-sm font-medium">← Back to Search</a>' if theme or query else ''}
            </div>
        '''
        
        for verse in search_results:
            tafsir_section = ''
            if verse['tafsir_html_content']:
                tafsir_section = f'''
                <div class="mt-4">
                    <h4 class="font-medium text-gray-800 mb-2">Commentary (Tafsir)</h4>
                    <div class="tafsir text-sm text-gray-600">{verse['tafsir_html_content']}</div>
                </div>
                '''
            else:
                tafsir_section = '<div class="mt-4"><p class="text-sm text-gray-500 italic">No commentary available</p></div>'
            
            search_content += f'''
            <div class="bg-white rounded-xl shadow-lg overflow-hidden">
                <!-- Card Header - Always Visible -->
                <div class="p-4 cursor-pointer hover:bg-gray-50 transition-colors" onclick="toggleCard('card-{verse['verse_key'].replace(':', '-')}')">
                    <div class="flex justify-between items-center">
                        <div class="flex-1">
                            <p class="font-amiri text-xl text-gray-900 mb-1" dir="rtl">
                                {verse['clean_ayah_text'][:100]}{'...' if len(verse['clean_ayah_text']) > 100 else ''}
                            </p>
                            <p class="text-indigo-600 font-medium text-sm">
                                Sūrah {verse['surah_number']}, Āyah {verse['ayah_number']} ({verse['verse_key']})
                            </p>
                            <p class="text-gray-600 text-sm mt-1">
                                {verse['translation_text'][:150]}{'...' if len(verse['translation_text']) > 150 else ''}
                            </p>
                        </div>
                        <div class="ml-4">
                            <svg class="w-5 h-5 text-gray-400 transform transition-transform duration-200" id="icon-{verse['verse_key'].replace(':', '-')}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
                            </svg>
                        </div>
                    </div>
                </div>
                
                <!-- Card Content - Collapsible -->
                <div class="hidden border-t bg-gray-50" id="card-{verse['verse_key'].replace(':', '-')}">
                    <div class="p-6">
                        <!-- Full Arabic Text -->
                        <div class="text-center mb-6 bg-white p-4 rounded-lg">
                            <p class="font-amiri text-2xl leading-relaxed text-gray-900 mb-3" dir="rtl">
                                {verse['clean_ayah_text']}
                            </p>
                            <p class="text-indigo-600 font-medium">
                                Sūrah {verse['surah_number']}, Āyah {verse['ayah_number']} ({verse['verse_key']})
                            </p>
                        </div>
                        
                        <!-- Full Translation -->
                        <div class="mb-4">
                            <h4 class="font-medium text-gray-800 mb-2 flex items-center">
                                <span class="w-2 h-2 bg-indigo-500 rounded-full mr-2"></span>
                                Translation
                            </h4>
                            <p class="text-gray-700 leading-relaxed">{verse['translation_text']}</p>
                        </div>
                        
                        <!-- Action Buttons -->
                        <div class="flex flex-wrap gap-2 mb-4">
                            <button onclick="toggleBookmark('{verse['verse_key']}')" id="bookmark-btn-{verse['verse_key']}" class="bg-gray-100 hover:bg-gray-200 text-gray-700 text-xs font-medium py-1 px-3 rounded border border-gray-300 transition duration-300">
                                <span id="bookmark-icon-{verse['verse_key']}">☆</span> Bookmark
                            </button>
                            <button onclick="copyVerseLink('{verse['verse_key']}')" class="bg-gray-100 hover:bg-gray-200 text-gray-700 text-xs font-medium py-1 px-3 rounded border border-gray-300 transition duration-300">
                                📋 Copy Link
                            </button>
                            <a href="/verse/{verse['verse_key']}" class="bg-indigo-100 hover:bg-indigo-200 text-indigo-700 text-xs font-medium py-1 px-3 rounded border border-indigo-300 transition duration-300">
                                🔗 View Full Page
                            </a>
                        </div>
                        
                        <!-- Tafsir -->
                        {tafsir_section}
                    </div>
                </div>
            </div>
            '''
        
        search_content += '</div>'
    
    elif query:
        search_content += f'''
        <div class="bg-white rounded-xl shadow-lg p-6 text-center">
            <p class="text-gray-600 mb-4">No verses found for "<strong>{query}</strong>"</p>
            <p class="text-sm text-gray-500">Try different keywords or check the spelling</p>
        </div>
        '''
    
    return render_template_string(BASE_TEMPLATE, 
                                title="Search Verses",
                                navigation=nav_with_active,
                                content=search_content)

# API Routes (unchanged)
@app.route('/api/random')
def api_random():
    """API endpoint for random verse."""
    verse = get_random_ayah()
    if not verse:
        return jsonify({"error": "No verses available"}), 500
    return jsonify(verse)

@app.route('/api/verse-of-the-day')
def api_verse_of_the_day():
    """API endpoint for verse of the day."""
    verse = get_verse_of_the_day()
    if not verse:
        return jsonify({"error": "No verses available"}), 500
    return jsonify(verse)

@app.route('/api/search')
def api_search():
    """API endpoint for search."""
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify([])
    
    results = search_verses(query)
    return jsonify(results)

@app.route('/api/theme/<theme_name>')
def api_theme(theme_name):
    """API endpoint for theme search."""
    results = search_by_theme(theme_name)
    return jsonify({"theme": theme_name, "count": len(results), "results": results[:5]})

@app.route('/bookmarks')
def bookmarks_page():
    """Bookmarks page - displays user's saved verses from localStorage."""
    # Add active class to bookmarks navigation
    nav_with_bookmarks = NAVIGATION.replace('href="/bookmarks"', 'href="/bookmarks" class="active-nav"')

    bookmarks_content = '''
    <div class="bg-white rounded-xl shadow-lg p-6 mb-6">
        <h2 class="text-2xl font-semibold text-gray-800 mb-4">📚 My Bookmarked Verses</h2>
        <p class="text-gray-600 mb-4">Your saved verses are stored in your browser's local storage.</p>

        <div id="bookmarks-container" class="space-y-4">
            <!-- Bookmarks will be loaded here by JavaScript -->
            <div class="text-center py-8">
                <div class="animate-spin inline-block w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full"></div>
                <p class="text-gray-500 mt-4">Loading bookmarks...</p>
            </div>
        </div>
    </div>

    <script>
        // Load and display bookmarks
        document.addEventListener('DOMContentLoaded', function() {
            const bookmarks = JSON.parse(localStorage.getItem('ayah-bookmarks') || '[]');
            const container = document.getElementById('bookmarks-container');

            if (bookmarks.length === 0) {
                container.innerHTML = `
                    <div class="text-center py-12">
                        <div class="text-6xl mb-4">📖</div>
                        <h3 class="text-xl font-semibold text-gray-700 mb-2">No Bookmarks Yet</h3>
                        <p class="text-gray-600 mb-6">Start bookmarking verses to save them for later.</p>
                        <a href="/search" class="inline-block bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-2 px-6 rounded-lg transition-colors duration-200">
                            Search Verses
                        </a>
                    </div>
                `;
                return;
            }

            // Fetch all bookmarked verses
            Promise.all(bookmarks.map(verseKey =>
                fetch(`/api/verse/${verseKey}`)
                    .then(r => r.ok ? r.json() : null)
                    .catch(() => null)
            )).then(verses => {
                const validVerses = verses.filter(v => v !== null);

                if (validVerses.length === 0) {
                    container.innerHTML = `
                        <div class="text-center py-8">
                            <p class="text-gray-600">Could not load bookmarked verses. Please check your connection.</p>
                        </div>
                    `;
                    return;
                }

                container.innerHTML = `
                    <div class="mb-4 text-gray-600">
                        <strong>${validVerses.length}</strong> bookmarked ${validVerses.length === 1 ? 'verse' : 'verses'}
                    </div>
                ` + validVerses.map(verse => `
                    <div class="bg-gray-50 rounded-lg p-6 border border-gray-200">
                        <div class="text-center mb-4 bg-white p-4 rounded-lg">
                            <p class="font-amiri text-2xl leading-relaxed text-gray-900 mb-3" dir="rtl">
                                ${verse.clean_ayah_text}
                            </p>
                            <p class="text-indigo-600 font-medium">
                                Sūrah ${verse.surah_number}, Āyah ${verse.ayah_number} (${verse.verse_key})
                            </p>
                        </div>

                        <div class="mb-4">
                            <h4 class="font-medium text-gray-800 mb-2">Translation</h4>
                            <p class="text-gray-700 leading-relaxed">${verse.translation_text}</p>
                        </div>

                        <div class="flex flex-wrap gap-2">
                            <button onclick="toggleBookmark('${verse.verse_key}')" class="bg-yellow-100 hover:bg-yellow-200 text-yellow-800 text-sm font-medium py-2 px-4 rounded border border-yellow-300 transition duration-300">
                                ★ Remove Bookmark
                            </button>
                            <a href="/verse/${verse.verse_key}" class="inline-block bg-indigo-100 hover:bg-indigo-200 text-indigo-700 text-sm font-medium py-2 px-4 rounded border border-indigo-300 transition duration-300">
                                🔗 View Full Page
                            </a>
                            <button onclick="copyVerseLink('${verse.verse_key}')" class="bg-gray-100 hover:bg-gray-200 text-gray-700 text-sm font-medium py-2 px-4 rounded border border-gray-300 transition duration-300">
                                📋 Copy Link
                            </button>
                        </div>
                    </div>
                `).join('');

                // Re-attach bookmark toggle functionality
                window.originalToggleBookmark = window.toggleBookmark;
                window.toggleBookmark = function(verseKey) {
                    originalToggleBookmark(verseKey);
                    // Reload bookmarks page after a short delay
                    setTimeout(() => location.reload(), 500);
                };
            });
        });
    </script>
    '''

    return render_template_string(BASE_TEMPLATE,
                                title="My Bookmarks",
                                navigation=nav_with_bookmarks,
                                content=bookmarks_content)

@app.route('/api/verse/<verse_key>')
def api_verse(verse_key):
    """API endpoint for getting a specific verse."""
    verse = get_verse_data(verse_key)
    if not verse:
        return jsonify({"error": "Verse not found"}), 404
    return jsonify(verse)

@app.route('/verse/<verse_key>')
def verse_permalink(verse_key):
    """Individual verse permalink."""
    if not unified_data:
        return "Error: No data loaded", 500

    # Validate verse_key format (should be surah:ayah like "2:255")
    if not re.match(r'^\d+:\d+$', verse_key):
        return f"Invalid verse format: {verse_key}. Use format like 2:255", 400

    # Use get_verse_data to get properly formatted data
    verse = get_verse_data(verse_key)
    if not verse:
        return f"Verse {verse_key} not found", 404

    # Create verse-specific metadata for social sharing
    verse_title = f"Quran {verse_key} - Sūrah {verse['surah_number']}, Āyah {verse['ayah_number']}"
    verse_description = verse['translation_text'][:200] + '...' if len(verse['translation_text']) > 200 else verse['translation_text']
    verse_url = request.url

    content = render_template_string(VERSE_DISPLAY,
                                   verse=verse,
                                   section_title=f"Sūrah {verse['surah_number']}, Āyah {verse['ayah_number']}",
                                   show_date=False,
                                   show_button=True,
                                   button_link="/random",
                                   button_text="Generate Another Random Ayah")

    return render_template_string(BASE_TEMPLATE,
                                title=verse_title,
                                description=verse_description,
                                og_title=verse_title,
                                og_description=verse_description,
                                og_url=verse_url,
                                navigation=NAVIGATION,
                                content=content)

# Error Handlers
@app.errorhandler(404)
def page_not_found(_e):
    """Custom 404 error page."""
    error_content = '''
    <div class="max-w-2xl mx-auto text-center py-16">
        <div class="bg-white rounded-xl shadow-lg p-8">
            <div class="text-6xl mb-4">🕌</div>
            <h1 class="text-3xl font-bold text-gray-800 mb-4">Page Not Found</h1>
            <p class="text-gray-600 mb-6">The page you're looking for doesn't exist.</p>
            <div class="space-y-3">
                <a href="/" class="inline-block bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-3 px-6 rounded-lg transition-colors duration-200">
                    Go to Home
                </a>
                <br>
                <a href="/search" class="inline-block text-indigo-600 hover:text-indigo-800 font-medium">
                    Search Verses
                </a>
            </div>
        </div>
    </div>
    '''
    return render_template_string(BASE_TEMPLATE,
                                title="Page Not Found",
                                navigation=NAVIGATION,
                                content=error_content), 404

@app.errorhandler(500)
def internal_error(_e):
    """Custom 500 error page."""
    error_content = '''
    <div class="max-w-2xl mx-auto text-center py-16">
        <div class="bg-white rounded-xl shadow-lg p-8">
            <div class="text-6xl mb-4">⚠️</div>
            <h1 class="text-3xl font-bold text-gray-800 mb-4">Something Went Wrong</h1>
            <p class="text-gray-600 mb-6">We encountered an error while processing your request.</p>
            <div class="space-y-3">
                <a href="/" class="inline-block bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-3 px-6 rounded-lg transition-colors duration-200">
                    Go to Home
                </a>
                <br>
                <a href="/random" class="inline-block text-indigo-600 hover:text-indigo-800 font-medium">
                    Try Random Verse
                </a>
            </div>
        </div>
    </div>
    '''
    return render_template_string(BASE_TEMPLATE,
                                title="Error",
                                navigation=NAVIGATION,
                                content=error_content), 500

# Load data when module is imported (for production)
print("Loading Quran data...")
if load_data():
    print(f"✅ Ready! Loaded {len(unified_data)} verses")
    print("💡 Note: Tafsir references are automatically resolved for complete commentary")
else:
    print("❌ Failed to load data. Please check your JSON files in the 'data' directory.")

if __name__ == '__main__':
    print("🌐 Starting development server...")
    print(f"📱 Visit: http://localhost:{config.PORT}")
    print("   📅 Home: Verse of the Day (same for everyone)")
    print("   🎲 /random: Random Ayah Generator")
    print("   🔍 /search: Search Verses")
    print("   ⭐ /bookmarks: View Bookmarked Verses")
    app.run(debug=config.DEBUG_MODE, host=config.HOST, port=config.PORT)