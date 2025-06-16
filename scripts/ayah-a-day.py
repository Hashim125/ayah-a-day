import json
import random
import re
import os
import webbrowser

# Define the base directory where your JSON data files are located
# This assumes your JSON files are in 'ayah-a-day/data/' relative to where you run the script
data_dir = os.path.join(os.getcwd(), 'ayah-a-day', 'data')

# Load your JSON files using standard file operations
try:
    with open(os.path.join(data_dir, 'qpc-hafs.json'), 'r', encoding='utf-8') as f:
        quran_data = json.load(f)
    with open(os.path.join(data_dir, 'en-taqi-usmani-simple.json'), 'r', encoding='utf-8') as f:
        translation_data = json.load(f)
    with open(os.path.join(data_dir, 'en-tafisr-ibn-kathir.json'), 'r', encoding='utf-8') as f:
        tafsir_data = json.load(f)
except FileNotFoundError as e:
    print(f"Error: One or more JSON files not found. Please ensure they are in '{data_dir}'.")
    print(f"Missing file: {e.filename}")
    exit()
except Exception as e:
    print(f"Error loading JSON files: {e}")
    exit()

# Unified data structure for easier access
# The 'quran_data' keys are already 'surah:ayah' (verse_key), which is perfect for direct lookup.
# We'll build a new dictionary that contains all relevant information per verse_key.
unified_data = {}
for verse_key, q_data in quran_data.items():
    # Ensure the verse_key exists in all datasets before trying to access
    if verse_key in translation_data and verse_key in tafsir_data:
        tafsir_entry = tafsir_data[verse_key]
        # Safely get tafsir_text, handling cases where it might be a string or a dict with 'text' key
        if isinstance(tafsir_entry, dict) and 'text' in tafsir_entry:
            current_tafsir_text = tafsir_entry['text']
        elif isinstance(tafsir_entry, str):
            current_tafsir_text = tafsir_entry
        else:
            current_tafsir_text = "" # Default to empty string if unexpected format

        unified_data[verse_key] = {
            "quran_text": q_data["text"],
            "surah": q_data["surah"],
            "ayah": q_data["ayah"],
            "verse_key": verse_key,
            "translation_text": translation_data[verse_key]['t'],
            "tafsir_text": current_tafsir_text
        }

# Function to strip specific HTML tags but keep structural ones (like <p>, <h2>)
def clean_tafsir_html(text):
    # Remove script and style tags completely
    text = re.sub(r'<script.*?>.*?</script>', '', text, flags=re.DOTALL)
    text = re.sub(r'<style.*?>.*?</style>', '', text, flags=re.DOTALL)

    # Remove specific span tags that contain "gray" class or other common non-semantic formatting
    # This regex tries to keep the text inside the span.
    # It specifically targets spans with a 'gray' class or any other class,
    # and replaces them with their inner content.
    text = re.sub(r'<span\s+(?:class="[^"]*?")?[^>]*>(.*?)</span>', r'\1', text, flags=re.DOTALL | re.IGNORECASE)

    # Remove empty p tags or p tags containing only whitespace
    text = re.sub(r'<p[^>]*>\s*</p>', '', text, flags=re.DOTALL)

    # Allow <h2>, <p>, <div>, <em>, strong, <b>, <i>, <br> to remain for formatting
    # Replace other tags with their content or remove if they are empty self-closing tags
    # This regex removes any tags not explicitly allowed (like <a>, etc.) but keeps their content
    text = re.sub(r'<(?!/?(?:p|h2|div|em|strong|b|i|br)\b)[^>]*>', '', text)

    # Remove original newlines, rely on HTML formatting provided by preserved tags
    text = text.replace('\n', '')
    return text

# Pick a random verse key
if not unified_data:
    print("No unified data available. Check JSON files and keys.")
    exit()

random_verse_key = random.choice(list(unified_data.keys()))
selected_ayah_data = unified_data[random_verse_key]

# Clean ayah text from any HTML tags (Tajweed colors, etc.)
clean_ayah_text = re.sub(r'<.*?>', '', selected_ayah_data["quran_text"])
translation_text = selected_ayah_data["translation_text"]

# Clean tafsir HTML content selectively
tafsir_html_content = clean_tafsir_html(selected_ayah_data["tafsir_text"])

surah_number = selected_ayah_data["surah"]
ayah_number = selected_ayah_data["ayah"]
verse_key = selected_ayah_data["verse_key"]


# HTML Template with Tailwind CSS
html_template = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ayah of the Day</title>
    <!-- Tailwind CSS CDN -->
    <script src="https://cdn.tailwindcss.com"></script>
    <!-- Google Fonts -->
    <link href="https://fonts.googleapis.com/css2?family=Amiri:wght@400;700&family=Inter:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
        body {{
            font-family: 'Inter', sans-serif;
        }}
        .font-amiri {{
            font-family: 'Amiri', serif;
        }}
        /* Basic styling for preserved HTML elements within the tafsir section */
        .tafsir p, .tafsir h2, .tafsir div {{
            margin-bottom: 1em; /* Add some spacing between paragraphs/headings within tafsir */
        }}
        .tafsir h2 {{
            font-size: 1.5em; /* Make h2 within tafsir larger */
            font-weight: bold;
            margin-top: 1.5em; /* More space above headings */
            color: #374151; /* Darker text for headings within tafsir */
        }}
        /* Further refinement for 'gray' class within tafsir if it somehow persists or is needed for other elements */
        .tafsir .gray {{
            color: #6b7280; /* A softer gray for specific text if it needs to be less prominent */
        }}
    </style>
</head>
<body class="bg-gradient-to-br from-blue-50 to-indigo-100 min-h-screen flex items-center justify-center p-4">
    <main class="bg-white shadow-2xl rounded-xl p-8 max-w-2xl w-full mx-auto my-8 border border-gray-200">
        <h1 class="text-center text-4xl font-extrabold text-indigo-800 mb-6 drop-shadow-sm">Ayah of the Day</h1>

        <section class="text-center mb-8 bg-gray-50 p-6 rounded-lg shadow-inner">
            <p lang="ar" dir="rtl" class="font-amiri text-4xl leading-relaxed text-gray-900 mb-4 font-bold">
                {clean_ayah_text}
            </p>
            <p class="text-lg text-indigo-600 font-medium">
                Sūrah {surah_number} - Āyah {ayah_number} ({verse_key})
            </p>
        </section>

        <section class="mb-8">
            <h2 class="text-2xl font-semibold text-gray-800 mb-3 border-b-2 border-indigo-200 pb-2">Translation (English)</h2>
            <p class="text-lg text-gray-700 leading-relaxed">
                {translation_text}
            </p>
        </section>

        <section>
            <h2 class="text-2xl font-semibold text-gray-800 mb-3 border-b-2 border-indigo-200 pb-2">Tafsir (English)</h2>
            <div class="tafsir text-base text-gray-600 leading-relaxed space-y-3">
                {tafsir_html_content}
            </div>
        </section>
    </main>
</body>
</html>
"""

# Save HTML file
output_file_path = os.path.join(os.getcwd(), "ayah-a-day/outputs/ayah-of-the-day.html")
with open(output_file_path, "w", encoding="utf-8") as f:
    f.write(html_template)

print("✅ Ayah HTML page generated: ayah-of-the-day.html")

# Open the generated HTML file in the default web browser
webbrowser.open(output_file_path)
