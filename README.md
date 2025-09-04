# 🌙 Ayah App - Simple Web Version

A clean, simple web application that displays random Quran verses with translations and commentary, plus basic search functionality.

## 🚀 Quick Start (2 minutes)

1. **Install Flask**
   ```bash
   pip install Flask
   ```

2. **Run the app**
   ```bash
   python simple_app.py
   ```

3. **Open your browser**
   Go to: http://localhost:5000

That's it! 🎉

## ✨ Features

- **Random verses** - Beautiful display of Quran verses with Arabic text, translation, and Tafsir
- **Search functionality** - Find verses containing specific words or phrases
- **Responsive design** - Works great on desktop and mobile
- **No database needed** - Uses your existing JSON files
- **API endpoints** - Simple JSON API for integration

## 📁 File Structure

```
ayah-a-day/
├── simple_app.py          # Main application (everything in one file!)
├── requirements.txt       # Just Flask
├── data/                  # Your Quran data files
│   ├── qpc-hafs.json
│   ├── en-taqi-usmani-simple.json
│   └── en-tafisr-ibn-kathir.json
└── archive/               # Previous versions stored here
```

## 🔍 How It Works

The app loads all 6,236 verses into memory at startup for fast access:
- **Home page** (`/`) - Shows a random verse
- **Search page** (`/search?q=query`) - Find verses containing your search terms
- **API endpoints** - `/api/random` and `/api/search` for programmatic access

## 🌐 Making It Live

### Option 1: PythonAnywhere (Free & Easy)
1. Sign up at [pythonanywhere.com](https://www.pythonanywhere.com)
2. Upload your files
3. Create a Flask app
4. Get a URL like `yourusername.pythonanywhere.com`

### Option 2: Any Web Hosting
- Upload files to any server that supports Python
- Run `python simple_app.py` 
- Your app will be available to anyone!

### Option 3: Heroku
```bash
# Create a Procfile with: web: python simple_app.py
echo "web: python simple_app.py" > Procfile
git add . && git commit -m "Simple app"
heroku create your-app-name
git push heroku main
```

## 🎨 Customization

Want to modify the look or add features? Everything is in `simple_app.py`:

- **Lines 15-65**: Data loading (your original logic)
- **Lines 90-200**: HTML template (easy to modify styling)
- **Lines 200-230**: Web routes (add new pages here)

## 📱 API Usage

Get random verse:
```javascript
fetch('/api/random')
  .then(response => response.json())
  .then(verse => console.log(verse.translation_text));
```

Search verses:
```javascript
fetch('/api/search?q=prayer')
  .then(response => response.json())
  .then(results => console.log(`Found ${results.length} verses`));
```

## 🔧 Technical Details

- **Flask** web framework (lightweight and simple)
- **In-memory data** for fast verse lookup
- **No database required** - uses your existing JSON files
- **Responsive design** with Tailwind CSS
- **Arabic font support** with Amiri font

## 📝 What Changed from Original

✅ **Kept everything you loved:**
- Same random verse generation logic
- Same HTML cleaning for Tafsir
- Same beautiful Arabic text display
- Uses your existing JSON files

➕ **Added useful features:**
- Web interface accessible from anywhere
- Search functionality
- Mobile-friendly responsive design
- API for potential integrations

❌ **Removed complexity:**
- No database setup required
- No complex configuration files
- No user accounts or authentication
- No email systems (can add later if needed)

## 🤝 What's Archived

I moved the complex version to `archive/complex_version/` in case you want the enterprise features later:
- Full database integration
- Email subscription system
- Docker deployment
- Comprehensive test suite
- Advanced caching and logging

Your original script is in `archive/original/` for reference.

## 🛠 Potential Enhancements

Simple additions we could make:
- **Bookmark favorites** (using browser localStorage)
- **Daily verse permalink** (same verse for everyone each day)
- **Share buttons** (WhatsApp, Twitter, etc.)
- **Simple email signup** (store emails in text file)
- **Verse of the day widget** (embeddable HTML)
- **Print-friendly view**
- **Dark mode toggle**

---

*May this simple app bring guidance and peace to all who use it. Barakallahu feek!* 🤲