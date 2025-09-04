"""Main Flask application for Ayah App."""

from flask import Flask, request, jsonify, render_template_string, redirect, url_for, flash
from flask_mail import Mail, Message
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
import atexit
import os
from datetime import datetime, time
from typing import Optional

from config.settings import get_config, Config
from .data_loader import DataLoader, DataValidationError
from .verse_selector import VerseSelector, SearchResult
from .html_generator import HTMLGenerator
from .email_system import EmailSubscriptionManager
from .logger import setup_logging, LoggerMixin, LogOperation


class AyahApp(LoggerMixin):
    """Main Ayah application class."""
    
    def __init__(self, config_name: Optional[str] = None):
        self.config = get_config(config_name)
        self.logger = setup_logging(self.config)
        
        # Initialize Flask app
        self.app = Flask(__name__, 
                        static_folder='../../static',
                        template_folder='../../templates')
        self.app.config.from_object(self.config)
        
        # Initialize extensions
        self.mail = Mail(self.app)
        CORS(self.app)
        
        # Initialize components
        try:
            with LogOperation(self.logger, "initializing data loader"):
                self.data_loader = DataLoader(self.config)
                
            with LogOperation(self.logger, "initializing verse selector"):
                self.verse_selector = VerseSelector(self.data_loader)
                
            self.html_generator = HTMLGenerator(self.config)
            self.email_manager = EmailSubscriptionManager(self.config, self.mail)
            
            # Load initial data
            with LogOperation(self.logger, "loading initial verse data"):
                self.data_loader.load_data()
                
        except Exception as e:
            self.logger.critical(f"Failed to initialize application: {e}")
            raise
        
        # Setup routes
        self._setup_routes()
        
        # Setup scheduler for automated emails
        self._setup_scheduler()
        
        self.logger.info("Ayah App initialized successfully")
    
    def _setup_routes(self):
        """Setup Flask routes."""
        
        @self.app.route('/')
        def index():
            """Main page with random verse."""
            try:
                verse = self.verse_selector.get_daily_verse()
                html_content = self.html_generator.generate_verse_html(
                    verse, template_style="modern"
                )
                return html_content
            except Exception as e:
                self.logger.error(f"Error serving main page: {e}")
                return self._render_error_page("Failed to load verse", 500)
        
        @self.app.route('/verse/<verse_key>')
        def verse_by_key(verse_key: str):
            """Display specific verse by key."""
            try:
                if not self.verse_selector.validate_verse_key_format(verse_key):
                    return self._render_error_page("Invalid verse key format", 400)
                
                verse = self.verse_selector.get_verse_by_key(verse_key)
                if not verse:
                    return self._render_error_page("Verse not found", 404)
                
                # Get context verses
                context = self.verse_selector.get_verse_context(verse_key)
                context_verses = context['before'] + context['after']
                
                html_content = self.html_generator.generate_verse_html(
                    verse, 
                    template_style="modern",
                    include_context=True,
                    context_verses=context_verses
                )
                return html_content
                
            except Exception as e:
                self.logger.error(f"Error serving verse {verse_key}: {e}")
                return self._render_error_page("Failed to load verse", 500)
        
        @self.app.route('/random')
        def random_verse():
            """Redirect to a random verse."""
            try:
                verse = self.verse_selector.get_random_verse()
                return redirect(url_for('verse_by_key', verse_key=verse.verse_key))
            except Exception as e:
                self.logger.error(f"Error generating random verse: {e}")
                return self._render_error_page("Failed to generate random verse", 500)
        
        @self.app.route('/search')
        def search_page():
            """Search page."""
            query = request.args.get('q', '').strip()
            results = []
            
            if query:
                try:
                    search_results = self.verse_selector.search_verses(query, limit=20)
                    results = [r.verse_data for r in search_results]
                except Exception as e:
                    self.logger.error(f"Search error for query '{query}': {e}")
                    flash("Search failed. Please try again.", "error")
            
            # Return search results page (simplified for now)
            return self._render_search_results(query, results)
        
        # API Routes
        @self.app.route('/api/random-verse')
        def api_random_verse():
            """API endpoint for random verse."""
            try:
                verse = self.verse_selector.get_random_verse()
                return jsonify({
                    'verse_key': verse.verse_key,
                    'surah': verse.surah,
                    'ayah': verse.ayah,
                    'arabic_text': verse.arabic_text,
                    'translation': verse.translation,
                    'tafsir': self.html_generator.html_cleaner.clean_tafsir_html(verse.tafsir)
                })
            except Exception as e:
                self.logger.error(f"API error generating random verse: {e}")
                return jsonify({'error': 'Failed to generate verse'}), 500
        
        @self.app.route('/api/verse/<verse_key>')
        def api_verse_by_key(verse_key: str):
            """API endpoint for specific verse."""
            try:
                if not self.verse_selector.validate_verse_key_format(verse_key):
                    return jsonify({'error': 'Invalid verse key format'}), 400
                
                verse = self.verse_selector.get_verse_by_key(verse_key)
                if not verse:
                    return jsonify({'error': 'Verse not found'}), 404
                
                return jsonify({
                    'verse_key': verse.verse_key,
                    'surah': verse.surah,
                    'ayah': verse.ayah,
                    'arabic_text': verse.arabic_text,
                    'translation': verse.translation,
                    'tafsir': self.html_generator.html_cleaner.clean_tafsir_html(verse.tafsir)
                })
                
            except Exception as e:
                self.logger.error(f"API error serving verse {verse_key}: {e}")
                return jsonify({'error': 'Failed to load verse'}), 500
        
        @self.app.route('/api/search')
        def api_search():
            """API endpoint for verse search."""
            query = request.args.get('q', '').strip()
            limit = min(int(request.args.get('limit', 20)), 100)  # Max 100 results
            
            if not query:
                return jsonify([])
            
            try:
                results = self.verse_selector.search_verses(query, limit=limit)
                return jsonify([{
                    'verse_data': {
                        'verse_key': r.verse_data.verse_key,
                        'surah': r.verse_data.surah,
                        'ayah': r.verse_data.ayah,
                        'arabic_text': r.verse_data.arabic_text,
                        'translation': r.verse_data.translation,
                        'tafsir': self.html_generator.html_cleaner.clean_tafsir_html(r.verse_data.tafsir)
                    },
                    'relevance_score': r.relevance_score,
                    'matched_fields': r.matched_fields
                } for r in results])
                
            except Exception as e:
                self.logger.error(f"API search error for query '{query}': {e}")
                return jsonify({'error': 'Search failed'}), 500
        
        # Email subscription routes
        @self.app.route('/subscribe', methods=['GET', 'POST'])
        def subscribe():
            """Email subscription page."""
            if request.method == 'POST':
                return self._handle_subscription()
            return self._render_subscription_page()
        
        @self.app.route('/unsubscribe/<token>')
        def unsubscribe(token: str):
            """Unsubscribe from emails."""
            try:
                if self.email_manager.unsubscribe_user(token):
                    flash("Successfully unsubscribed from daily emails.", "success")
                else:
                    flash("Invalid unsubscribe link.", "error")
            except Exception as e:
                self.logger.error(f"Unsubscribe error: {e}")
                flash("Error processing unsubscribe request.", "error")
            
            return redirect(url_for('index'))
        
        # Health check and admin routes
        @self.app.route('/health')
        def health_check():
            """Health check endpoint."""
            try:
                # Basic health checks
                verse_count = len(self.data_loader.load_data())
                integrity_info = self.data_loader.validate_data_integrity()
                
                return jsonify({
                    'status': 'healthy',
                    'verse_count': verse_count,
                    'cache_valid': integrity_info.get('cache_valid', False),
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as e:
                self.logger.error(f"Health check failed: {e}")
                return jsonify({
                    'status': 'unhealthy',
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }), 500
        
        @self.app.route('/admin/data-integrity')
        def admin_data_integrity():
            """Admin endpoint for data integrity check."""
            try:
                integrity_info = self.data_loader.validate_data_integrity()
                return jsonify(integrity_info)
            except Exception as e:
                self.logger.error(f"Data integrity check failed: {e}")
                return jsonify({'error': str(e)}), 500
        
        # Error handlers
        @self.app.errorhandler(404)
        def not_found(error):
            return self._render_error_page("Page not found", 404)
        
        @self.app.errorhandler(500)
        def internal_error(error):
            return self._render_error_page("Internal server error", 500)
    
    def _handle_subscription(self):
        """Handle email subscription form submission."""
        email = request.form.get('email', '').strip().lower()
        name = request.form.get('name', '').strip()
        frequency = request.form.get('frequency', 'daily')
        
        if not email:
            flash("Email address is required.", "error")
            return self._render_subscription_page()
        
        try:
            success, message = self.email_manager.subscribe_user(email, name, frequency)
            if success:
                flash(message, "success")
                return redirect(url_for('index'))
            else:
                flash(message, "error")
                return self._render_subscription_page()
                
        except Exception as e:
            self.logger.error(f"Subscription error: {e}")
            flash("Error processing subscription. Please try again.", "error")
            return self._render_subscription_page()
    
    def _setup_scheduler(self):
        """Setup background scheduler for automated emails."""
        if self.config.DEBUG:
            self.logger.info("Skipping scheduler setup in debug mode")
            return
        
        try:
            scheduler = BackgroundScheduler()
            
            # Parse email time
            hour, minute = map(int, self.config.DAILY_EMAIL_TIME.split(':'))
            
            # Daily emails
            scheduler.add_job(
                func=self._send_daily_emails,
                trigger="cron",
                hour=hour,
                minute=minute,
                id='daily_emails'
            )
            
            # Weekly emails (every Friday)
            scheduler.add_job(
                func=self._send_weekly_emails,
                trigger="cron",
                day_of_week=self.config.WEEKLY_EMAIL_DAY,
                hour=hour,
                minute=minute,
                id='weekly_emails'
            )
            
            scheduler.start()
            atexit.register(lambda: scheduler.shutdown())
            
            self.logger.info("Email scheduler started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to setup scheduler: {e}")
    
    def _send_daily_emails(self):
        """Send daily emails to subscribers."""
        try:
            with LogOperation(self.logger, "sending daily emails"):
                verse = self.verse_selector.get_daily_verse()
                self.email_manager.send_daily_email(verse)
        except Exception as e:
            self.logger.error(f"Failed to send daily emails: {e}")
    
    def _send_weekly_emails(self):
        """Send weekly emails to subscribers."""
        try:
            with LogOperation(self.logger, "sending weekly emails"):
                verse = self.verse_selector.get_daily_verse()
                self.email_manager.send_weekly_email(verse)
        except Exception as e:
            self.logger.error(f"Failed to send weekly emails: {e}")
    
    def _render_error_page(self, message: str, status_code: int) -> tuple:
        """Render error page."""
        html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Error - Ayah App</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100 flex items-center justify-center min-h-screen">
    <div class="text-center">
        <h1 class="text-6xl font-bold text-gray-400">{status_code}</h1>
        <p class="text-xl text-gray-600 mt-4">{message}</p>
        <a href="/" class="inline-block mt-6 bg-indigo-600 text-white px-6 py-3 rounded-lg hover:bg-indigo-700 transition duration-200">
            Return Home
        </a>
    </div>
</body>
</html>'''
        return html, status_code
    
    def _render_subscription_page(self) -> str:
        """Render email subscription page."""
        return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Subscribe - Ayah App</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gradient-to-br from-blue-50 to-indigo-100 min-h-screen flex items-center justify-center p-4">
    <div class="bg-white rounded-2xl shadow-xl p-8 max-w-md w-full">
        <h1 class="text-3xl font-bold text-indigo-800 mb-6 text-center">Subscribe to Daily Ayahs</h1>
        <p class="text-gray-600 mb-6 text-center">Receive beautiful Quran verses with translations and commentary directly in your inbox.</p>
        
        <form method="POST" class="space-y-4">
            <div>
                <label for="email" class="block text-sm font-medium text-gray-700 mb-1">Email Address *</label>
                <input type="email" id="email" name="email" required 
                       class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent">
            </div>
            
            <div>
                <label for="name" class="block text-sm font-medium text-gray-700 mb-1">Name (Optional)</label>
                <input type="text" id="name" name="name" 
                       class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent">
            </div>
            
            <div>
                <label for="frequency" class="block text-sm font-medium text-gray-700 mb-1">Frequency</label>
                <select id="frequency" name="frequency" 
                        class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent">
                    <option value="daily">Daily</option>
                    <option value="weekly">Weekly (Fridays)</option>
                </select>
            </div>
            
            <button type="submit" 
                    class="w-full bg-indigo-600 text-white py-3 px-4 rounded-lg hover:bg-indigo-700 transition duration-200 font-medium">
                Subscribe
            </button>
        </form>
        
        <p class="text-xs text-gray-500 mt-4 text-center">
            You can unsubscribe at any time using the link in our emails.
        </p>
        
        <div class="text-center mt-6">
            <a href="/" class="text-indigo-600 hover:text-indigo-800">← Back to Ayah App</a>
        </div>
    </div>
</body>
</html>'''
    
    def _render_search_results(self, query: str, results: list) -> str:
        """Render search results page (simplified)."""
        results_html = ""
        if results:
            results_html = "\\n".join([
                f'''<div class="bg-white rounded-lg p-6 mb-4 shadow">
                    <div class="text-indigo-600 font-medium mb-2">Verse {r.verse_key}</div>
                    <div class="text-gray-700 mb-3">{r.translation[:200]}...</div>
                    <a href="/verse/{r.verse_key}" class="text-indigo-600 hover:underline">Read full verse</a>
                </div>'''
                for r in results[:10]  # Limit results
            ])
        elif query:
            results_html = '<p class="text-gray-500">No verses found for your search.</p>'
        
        return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Search - Ayah App</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100 min-h-screen">
    <div class="max-w-4xl mx-auto py-8 px-4">
        <h1 class="text-3xl font-bold text-gray-800 mb-6">Search Verses</h1>
        
        <form method="GET" class="mb-8">
            <div class="flex">
                <input type="text" name="q" value="{query}" placeholder="Search verses..." 
                       class="flex-1 px-4 py-2 border border-gray-300 rounded-l-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent">
                <button type="submit" class="bg-indigo-600 text-white px-6 py-2 rounded-r-lg hover:bg-indigo-700">
                    Search
                </button>
            </div>
        </form>
        
        <div class="results">
            {results_html}
        </div>
        
        <div class="text-center mt-8">
            <a href="/" class="text-indigo-600 hover:text-indigo-800">← Back to Ayah App</a>
        </div>
    </div>
</body>
</html>'''
    
    def run(self, host='127.0.0.1', port=5000, debug=None):
        """Run the Flask application."""
        if debug is None:
            debug = self.config.DEBUG
        
        self.logger.info(f"Starting Ayah App on {host}:{port} (debug={debug})")
        self.app.run(host=host, port=port, debug=debug)


def create_app(config_name: Optional[str] = None) -> Flask:
    """Application factory function."""
    ayah_app = AyahApp(config_name)
    return ayah_app.app


if __name__ == '__main__':
    app = AyahApp()
    app.run()