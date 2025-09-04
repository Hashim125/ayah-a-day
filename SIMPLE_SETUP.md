# Simple Ayah App Setup

This is a **much simpler** version that keeps the essence of your original script but adds web functionality and search.

## What You Get

✅ **Same core functionality** - Random Quran verses with translation and tafsir  
✅ **Web interface** - Access from any browser  
✅ **Basic search** - Find verses by text  
✅ **No database needed** - Uses your existing JSON files  
✅ **No complex setup** - Just run one Python file  

## Quick Setup (3 minutes)

### 1. Install Flask
```bash
pip install Flask
```

### 2. Run the App
```bash
python simple_app.py
```

### 3. Open Your Browser
Go to: **http://localhost:5000**

That's it! 🎉

## File Structure

You just need:
```
ayah-a-day/
├── simple_app.py          # The main app (one file!)
├── requirements.txt       # Just Flask
└── data/                  # Your existing JSON files
    ├── qpc-hafs.json
    ├── en-taqi-usmani-simple.json
    └── en-tafisr-ibn-kathir.json
```

## Features

- **Home page**: Shows random verse (like your original script)
- **"Generate New Ayah" button**: Gets another random verse
- **Search box**: Find verses containing specific words
- **Clean, responsive design**: Works on phone and desktop
- **API endpoints**: `/api/random` and `/api/search` if you want to integrate

## Making It Live on the Internet

If you want people to access it online, here are the **simplest** options:

### Option 1: PythonAnywhere (Free & Easy)
1. Sign up at [pythonanywhere.com](https://www.pythonanywhere.com) (free tier available)
2. Upload your files
3. Set it up as a Flask app
4. Get a URL like `yourusername.pythonanywhere.com`

### Option 2: Heroku (Free Tier Available)
1. Install Heroku CLI
2. Create a `Procfile` with: `web: python simple_app.py`
3. Deploy with: `git push heroku main`

### Option 3: Your Own Server
- Any VPS (DigitalOcean, Linode, etc.)
- Just run `python simple_app.py` on the server
- Set up a domain name if you want

## Differences from Complex Version

**What I removed:**
- ❌ Database (PostgreSQL, SQLite)
- ❌ Email subscription system  
- ❌ User accounts
- ❌ Complex caching
- ❌ Docker containers
- ❌ Background tasks
- ❌ 50+ files and configurations

**What I kept:**
- ✅ Your original data loading logic
- ✅ Your HTML cleaning functions
- ✅ Random verse generation
- ✅ Beautiful web interface
- ✅ Search functionality
- ✅ All your existing JSON files work as-is

## Customization

Want to modify it? The entire app is in one file (`simple_app.py`) with clear sections:

- **Data loading**: Lines 12-60 (your original logic)
- **HTML template**: Lines 90-200 (easy to modify)
- **Web routes**: Lines 202-230 (add new pages here)

## Adding Email Later (Optional)

If you decide you want email subscriptions later, we can add a simple version:
- Add a signup form
- Store emails in a text file or simple database
- Add a daily script that emails everyone

But for now, this gives you everything you need without complexity!

---

**This is basically your original script, but:**
- Accessible via web browser
- Has search functionality  
- Can be shared with others
- No complicated setup required