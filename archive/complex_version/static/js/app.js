/**
 * Ayah App - Frontend JavaScript functionality
 */

class AyahApp {
    constructor() {
        this.currentVerse = null;
        this.favorites = this.loadFavorites();
        this.preferences = this.loadPreferences();
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.applyPreferences();
        this.setupServiceWorker();
    }

    setupEventListeners() {
        // New verse generation
        const generateBtn = document.getElementById('generate-ayah-btn');
        const newVerseBtn = document.getElementById('new-verse-btn');
        
        if (generateBtn) {
            generateBtn.addEventListener('click', () => this.generateNewVerse());
        }
        
        if (newVerseBtn) {
            newVerseBtn.addEventListener('click', () => this.generateNewVerse());
        }

        // Bookmark functionality
        const bookmarkBtn = document.getElementById('bookmark-btn');
        if (bookmarkBtn) {
            bookmarkBtn.addEventListener('click', () => this.toggleBookmark());
        }

        // Share functionality
        const shareBtn = document.querySelector('.share-btn');
        if (shareBtn) {
            shareBtn.addEventListener('click', () => this.shareVerse());
        }

        // Copy functionality
        const copyBtn = document.querySelector('.copy-btn');
        if (copyBtn) {
            copyBtn.addEventListener('click', () => this.copyVerse());
        }

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => this.handleKeyboardShortcuts(e));

        // Search functionality
        this.setupSearch();
    }

    async generateNewVerse() {
        try {
            this.showLoading(true);
            
            const response = await fetch('/api/random-verse', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            if (!response.ok) {
                throw new Error('Failed to fetch new verse');
            }

            const verseData = await response.json();
            this.updateVerseDisplay(verseData);
            this.currentVerse = verseData;
            
        } catch (error) {
            console.error('Error generating new verse:', error);
            this.showNotification('Failed to load new verse. Please try again.', 'error');
        } finally {
            this.showLoading(false);
        }
    }

    updateVerseDisplay(verseData) {
        // Update Arabic text
        const arabicElement = document.getElementById('arabic-text');
        if (arabicElement) {
            arabicElement.textContent = verseData.arabic_text;
        }

        // Update translation
        const translationElement = document.getElementById('translation-text');
        if (translationElement) {
            translationElement.textContent = verseData.translation;
        }

        // Update Tafsir
        const tafsirElement = document.getElementById('tafsir-content');
        if (tafsirElement) {
            tafsirElement.innerHTML = verseData.tafsir;
        }

        // Update verse info
        const verseInfoElements = document.querySelectorAll('.verse-info');
        verseInfoElements.forEach(element => {
            element.textContent = `Sūrah ${verseData.surah}, Āyah ${verseData.ayah} (${verseData.verse_key})`;
        });

        // Update page title
        document.title = `Ayah ${verseData.verse_key} - Ayah App`;

        // Update URL without page reload
        const newUrl = `/verse/${verseData.verse_key}`;
        window.history.pushState({ verseKey: verseData.verse_key }, '', newUrl);

        // Update bookmark button state
        this.updateBookmarkButton();
    }

    toggleBookmark() {
        if (!this.currentVerse) return;

        const verseKey = this.currentVerse.verse_key;
        
        if (this.favorites.includes(verseKey)) {
            this.favorites = this.favorites.filter(key => key !== verseKey);
            this.showNotification('Removed from bookmarks', 'info');
        } else {
            this.favorites.push(verseKey);
            this.showNotification('Added to bookmarks', 'success');
        }

        this.saveFavorites();
        this.updateBookmarkButton();
    }

    updateBookmarkButton() {
        const bookmarkBtn = document.getElementById('bookmark-btn');
        if (!bookmarkBtn || !this.currentVerse) return;

        const isBookmarked = this.favorites.includes(this.currentVerse.verse_key);
        bookmarkBtn.textContent = isBookmarked ? 'Remove Bookmark' : 'Bookmark';
        bookmarkBtn.classList.toggle('text-yellow-600', isBookmarked);
        bookmarkBtn.classList.toggle('text-indigo-600', !isBookmarked);
    }

    async shareVerse() {
        if (!this.currentVerse) return;

        const shareData = {
            title: `Ayah ${this.currentVerse.verse_key}`,
            text: `${this.currentVerse.arabic_text}\n\n"${this.currentVerse.translation}"\n\n- Quran ${this.currentVerse.verse_key}`,
            url: window.location.href
        };

        try {
            if (navigator.share) {
                await navigator.share(shareData);
                this.showNotification('Verse shared successfully', 'success');
            } else {
                // Fallback to copying to clipboard
                await navigator.clipboard.writeText(`${shareData.text}\n\n${shareData.url}`);
                this.showNotification('Verse copied to clipboard', 'success');
            }
        } catch (error) {
            console.error('Error sharing verse:', error);
            this.showNotification('Failed to share verse', 'error');
        }
    }

    async copyVerse() {
        if (!this.currentVerse) return;

        const textToCopy = `${this.currentVerse.arabic_text}\n\n"${this.currentVerse.translation}"\n\n- Quran ${this.currentVerse.verse_key}`;

        try {
            await navigator.clipboard.writeText(textToCopy);
            this.showNotification('Verse copied to clipboard', 'success');
        } catch (error) {
            console.error('Error copying verse:', error);
            this.showNotification('Failed to copy verse', 'error');
        }
    }

    handleKeyboardShortcuts(e) {
        // Spacebar or 'n' for new verse
        if ((e.code === 'Space' || e.key === 'n') && !e.target.matches('input, textarea')) {
            e.preventDefault();
            this.generateNewVerse();
        }
        
        // 'b' for bookmark
        if (e.key === 'b' && !e.target.matches('input, textarea')) {
            e.preventDefault();
            this.toggleBookmark();
        }
        
        // 's' for share
        if (e.key === 's' && !e.target.matches('input, textarea')) {
            e.preventDefault();
            this.shareVerse();
        }
    }

    setupSearch() {
        const searchInput = document.getElementById('search-input');
        const searchResults = document.getElementById('search-results');
        
        if (!searchInput) return;

        let searchTimeout;
        
        searchInput.addEventListener('input', (e) => {
            clearTimeout(searchTimeout);
            const query = e.target.value.trim();
            
            if (query.length < 3) {
                if (searchResults) searchResults.innerHTML = '';
                return;
            }
            
            searchTimeout = setTimeout(() => {
                this.performSearch(query);
            }, 300);
        });
    }

    async performSearch(query) {
        try {
            const response = await fetch(`/api/search?q=${encodeURIComponent(query)}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            if (!response.ok) {
                throw new Error('Search failed');
            }

            const results = await response.json();
            this.displaySearchResults(results);
            
        } catch (error) {
            console.error('Search error:', error);
            this.showNotification('Search failed. Please try again.', 'error');
        }
    }

    displaySearchResults(results) {
        const searchResults = document.getElementById('search-results');
        if (!searchResults) return;

        if (results.length === 0) {
            searchResults.innerHTML = '<p class="text-gray-500 text-center py-4">No verses found</p>';
            return;
        }

        const resultsHTML = results.map(result => `
            <div class="search-result-item p-4 border-b hover:bg-gray-50 cursor-pointer" 
                 data-verse-key="${result.verse_data.verse_key}">
                <div class="font-medium text-indigo-600 mb-1">
                    Verse ${result.verse_data.verse_key} 
                    <span class="text-sm text-gray-500">(Relevance: ${(result.relevance_score * 100).toFixed(0)}%)</span>
                </div>
                <div class="text-sm text-gray-700 mb-2">
                    ${result.verse_data.translation.substring(0, 150)}${result.verse_data.translation.length > 150 ? '...' : ''}
                </div>
                <div class="text-xs text-gray-500">
                    Matched: ${result.matched_fields.join(', ')}
                </div>
            </div>
        `).join('');

        searchResults.innerHTML = resultsHTML;

        // Add click handlers for search results
        searchResults.querySelectorAll('.search-result-item').forEach(item => {
            item.addEventListener('click', () => {
                const verseKey = item.dataset.verseKey;
                this.loadSpecificVerse(verseKey);
            });
        });
    }

    async loadSpecificVerse(verseKey) {
        try {
            this.showLoading(true);
            
            const response = await fetch(`/api/verse/${verseKey}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            if (!response.ok) {
                throw new Error('Failed to fetch verse');
            }

            const verseData = await response.json();
            this.updateVerseDisplay(verseData);
            this.currentVerse = verseData;
            
        } catch (error) {
            console.error('Error loading specific verse:', error);
            this.showNotification('Failed to load verse. Please try again.', 'error');
        } finally {
            this.showLoading(false);
        }
    }

    showLoading(show) {
        const generateBtn = document.getElementById('generate-ayah-btn');
        const newVerseBtn = document.getElementById('new-verse-btn');
        
        [generateBtn, newVerseBtn].forEach(btn => {
            if (!btn) return;
            
            if (show) {
                btn.disabled = true;
                btn.innerHTML = '<span class="loading-spinner"></span> Loading...';
                btn.classList.add('opacity-75');
            } else {
                btn.disabled = false;
                btn.innerHTML = btn.id === 'generate-ayah-btn' 
                    ? '<span class="flex items-center"><svg class="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clip-rule="evenodd"></path></svg>Generate New Verse</span>'
                    : 'New Verse';
                btn.classList.remove('opacity-75');
            }
        });
    }

    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification fixed top-4 right-4 px-6 py-3 rounded-lg text-white z-50 transform transition-transform duration-300 translate-x-full`;
        
        // Set color based on type
        switch (type) {
            case 'success':
                notification.classList.add('bg-green-500');
                break;
            case 'error':
                notification.classList.add('bg-red-500');
                break;
            case 'warning':
                notification.classList.add('bg-yellow-500');
                break;
            default:
                notification.classList.add('bg-blue-500');
        }
        
        notification.textContent = message;
        document.body.appendChild(notification);
        
        // Animate in
        setTimeout(() => {
            notification.classList.remove('translate-x-full');
        }, 100);
        
        // Auto remove after 3 seconds
        setTimeout(() => {
            notification.classList.add('translate-x-full');
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }, 3000);
    }

    loadFavorites() {
        try {
            const favorites = localStorage.getItem('ayah_favorites');
            return favorites ? JSON.parse(favorites) : [];
        } catch (error) {
            console.error('Error loading favorites:', error);
            return [];
        }
    }

    saveFavorites() {
        try {
            localStorage.setItem('ayah_favorites', JSON.stringify(this.favorites));
        } catch (error) {
            console.error('Error saving favorites:', error);
        }
    }

    loadPreferences() {
        try {
            const prefs = localStorage.getItem('ayah_preferences');
            return prefs ? JSON.parse(prefs) : {
                theme: 'light',
                fontSize: 'medium',
                arabicFont: 'Amiri'
            };
        } catch (error) {
            console.error('Error loading preferences:', error);
            return { theme: 'light', fontSize: 'medium', arabicFont: 'Amiri' };
        }
    }

    savePreferences() {
        try {
            localStorage.setItem('ayah_preferences', JSON.stringify(this.preferences));
        } catch (error) {
            console.error('Error saving preferences:', error);
        }
    }

    applyPreferences() {
        // Apply theme
        if (this.preferences.theme === 'dark') {
            document.body.classList.add('dark-theme');
        }
        
        // Apply font size
        const arabicElement = document.getElementById('arabic-text');
        if (arabicElement) {
            arabicElement.classList.remove('text-xl', 'text-2xl', 'text-3xl', 'text-4xl', 'text-5xl');
            switch (this.preferences.fontSize) {
                case 'small':
                    arabicElement.classList.add('text-2xl');
                    break;
                case 'large':
                    arabicElement.classList.add('text-5xl');
                    break;
                case 'extra-large':
                    arabicElement.classList.add('text-6xl');
                    break;
                default:
                    arabicElement.classList.add('text-4xl');
            }
        }
    }

    setupServiceWorker() {
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/sw.js')
                .then((registration) => {
                    console.log('ServiceWorker registered:', registration);
                })
                .catch((error) => {
                    console.log('ServiceWorker registration failed:', error);
                });
        }
    }
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.ayahApp = new AyahApp();
});

// Handle browser back/forward buttons
window.addEventListener('popstate', (e) => {
    if (e.state && e.state.verseKey) {
        window.ayahApp.loadSpecificVerse(e.state.verseKey);
    }
});