"""Simple Ayah App - A web version with Verse of the Day, Random Generator, and Search."""

import json
import random
import re
import os
import datetime
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# Global data storage (loaded once at startup)
unified_data = {}
tafsir_cache = {}  # Cache for resolved tafsir references

def load_data():
    """Load and unify JSON data files with proper tafsir reference resolution."""
    global unified_data, tafsir_cache
    
    # Define data file paths
    data_dir = 'data'
    
    # Check if data directory exists
    if not os.path.exists(data_dir):
        print(f"❌ Error: Data directory '{data_dir}' not found")
        return False
    
    # Check if all required files exist
    required_files = [
        'qpc-hafs.json',
        'en-taqi-usmani-simple.json', 
        'en-tafisr-ibn-kathir.json'
    ]
    
    for filename in required_files:
        filepath = os.path.join(data_dir, filename)
        if not os.path.exists(filepath):
            print(f"❌ Error: Required file '{filename}' not found in data directory")
            print(f"   Expected path: {os.path.abspath(filepath)}")
            return False
    
    try:
        # Load JSON files with better error handling
        print("📚 Loading Arabic text...")
        with open(os.path.join(data_dir, 'qpc-hafs.json'), 'r', encoding='utf-8') as f:
            quran_data = json.load(f)
            
        print("🔤 Loading translations...")
        with open(os.path.join(data_dir, 'en-taqi-usmani-simple.json'), 'r', encoding='utf-8') as f:
            translation_data = json.load(f)
            
        print("📖 Loading tafsir...")
        with open(os.path.join(data_dir, 'en-tafisr-ibn-kathir.json'), 'r', encoding='utf-8') as f:
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

def resolve_tafsir_reference(verse_key, tafsir_data, max_depth=3, depth=0):
    """Resolve tafsir references by following the chain."""
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

def search_verses(query, max_results=20):
    """Simple search function."""
    if not query or not unified_data:
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
        <div class="flex justify-between items-center">
            <h1 class="text-2xl font-bold text-indigo-800">
                <a href="/" class="hover:text-indigo-600">🌙 Ayah App</a>
            </h1>
            <div class="flex space-x-6">
                <a href="/" class="text-gray-700 hover:text-indigo-600 font-medium">Verse of the Day</a>
                <a href="/random" class="text-gray-700 hover:text-indigo-600 font-medium">Random Ayah</a>
                <a href="/search" class="text-gray-700 hover:text-indigo-600 font-medium">Search</a>
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
            <p>Translation: Taqi Usmani | Commentary: Ibn Kathir</p>
            <p class="mt-1 text-xs">Tafsir references are automatically resolved for complete commentary</p>
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
        <button onclick="toggleBookmark('{{ verse.verse_key }}')" id="bookmark-btn-{{ verse.verse_key }}" class="bg-gray-100 hover:bg-gray-200 text-gray-700 font-medium py-2 px-4 rounded-lg border border-gray-300 transition duration-300 text-sm">
            <span id="bookmark-icon-{{ verse.verse_key }}">☆</span> Bookmark
        </button>
        
        <button onclick="copyVerseLink('{{ verse.verse_key }}')" class="bg-gray-100 hover:bg-gray-200 text-gray-700 font-medium py-2 px-4 rounded-lg border border-gray-300 transition duration-300 text-sm">
            📋 Copy Link
        </button>
        
        <button onclick="shareWhatsApp('{{ verse.verse_key }}', '{{ verse.clean_ayah_text|replace("'", "\\'")|replace('"', '\\"') }}', '{{ verse.translation_text|replace("'", "\\'")|replace('"', '\\"') }}')" class="bg-green-500 hover:bg-green-600 text-white font-medium py-2 px-4 rounded-lg transition duration-300 text-sm">
            📱 WhatsApp
        </button>
        
        <button onclick="shareTwitter('{{ verse.verse_key }}', '{{ verse.translation_text|replace("'", "\\'")|replace('"', '\\"') }}')" class="bg-blue-400 hover:bg-blue-500 text-white font-medium py-2 px-4 rounded-lg transition duration-300 text-sm">
            🐦 Tweet
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
                                content=content)

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
    """Search page."""
    query = request.args.get('q', '').strip()
    search_results = []
    
    if query:
        search_results = search_verses(query)
    
    # Add active class to navigation
    nav_with_active = NAVIGATION.replace('href="/search"', 'href="/search" class="active-nav"')
    
    # Search page content
    search_content = f'''
    <div class="bg-white rounded-xl shadow-lg p-6 mb-6">
        <h2 class="text-2xl font-semibold text-gray-800 mb-4">Search Verses</h2>
        <form method="GET" class="flex gap-2 mb-4">
            <input type="text" name="q" value="{query}" placeholder="Search by text or verse reference (e.g., 2:255, prayer, guidance)" 
                   class="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent text-lg">
            <button type="submit" class="bg-indigo-600 hover:bg-indigo-700 text-white px-8 py-3 rounded-lg font-medium">
                Search
            </button>
        </form>
        <p class="text-sm text-gray-600">
            💡 <strong>Tips:</strong> Search by verse reference (2:255), topic (prayer, forgiveness), or any word
        </p>
    </div>
    '''
    
    if search_results:
        search_content += f'<div class="space-y-6"><h3 class="text-xl font-bold text-gray-800">Search Results ({len(search_results)} found)</h3>'
        
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
            <div class="bg-white rounded-xl shadow-lg p-6">
                <div class="text-center mb-4">
                    <p class="font-amiri text-2xl leading-relaxed text-gray-900 mb-2" dir="rtl">
                        {verse['clean_ayah_text']}
                    </p>
                    <p class="text-indigo-600 font-medium">
                        Sūrah {verse['surah_number']}, Āyah {verse['ayah_number']} ({verse['verse_key']})
                    </p>
                </div>
                
                <div class="mb-3">
                    <h4 class="font-medium text-gray-800 mb-2">Translation</h4>
                    <p class="text-gray-700">{verse['translation_text']}</p>
                </div>
                
                {tafsir_section}
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

@app.route('/verse/<verse_key>')
def verse_permalink(verse_key):
    """Individual verse permalink."""
    if not unified_data:
        return "Error: No data loaded", 500
    
    verse = unified_data.get(verse_key)
    if not verse:
        return f"Verse {verse_key} not found", 404
    
    content = render_template_string(VERSE_DISPLAY, 
                                   verse=verse,
                                   section_title=f"Sūrah {verse['surah']}, Āyah {verse['ayah']}",
                                   show_date=False,
                                   show_button=True,
                                   button_link="/random",
                                   button_text="Generate Another Random Ayah")
    
    return render_template_string(BASE_TEMPLATE, 
                                title=f"Quran {verse_key}",
                                navigation=NAVIGATION,
                                content=content)

# Load data when module is imported (for production)
print("Loading Quran data...")
if load_data():
    print(f"✅ Ready! Loaded {len(unified_data)} verses")
    print("💡 Note: Tafsir references are automatically resolved for complete commentary")
else:
    print("❌ Failed to load data. Please check your JSON files in the 'data' directory.")

if __name__ == '__main__':
    print("🌐 Starting development server...")
    print("📱 Visit: http://localhost:5000")
    print("   📅 Home: Verse of the Day (same for everyone)")
    print("   🎲 /random: Random Ayah Generator")  
    print("   🔍 /search: Search Verses")
    app.run(debug=True, host='0.0.0.0')