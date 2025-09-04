# Claude.md - Maximizing Claude Usage for Ayah-a-Day

This guide helps you work efficiently with Claude on the Ayah-a-Day project by providing context, common tasks, and optimization strategies.

## Project Overview

**Ayah-a-Day** is a Python-based Quran verse generator that creates beautiful HTML pages displaying random verses with translations and Tafsir commentary.

### Architecture
```
ayah-a-day/
├── scripts/
│   └── ayah-a-day.py          # Main Python script (217 lines)
├── data/                       # JSON datasets (~25MB total)
│   ├── qpc-hafs.json          # Arabic Quran text
│   ├── en-taqi-usmani-simple.json # English translation
│   ├── en-tafisr-ibn-kathir.json  # Tafsir commentary
│   ├── qpc-hafs-tajweed.json  # Tajweed rules
│   └── qpc-hafs-word-by-word.json # Word-by-word breakdown
├── outputs/
│   └── ayah-of-the-day.html   # Generated HTML page
└── README.md
```

### Key Components
- **Data Processing**: Unifies 3 JSON datasets into a single structure
- **HTML Generation**: Creates responsive webpage with Tailwind CSS
- **Client-side Interactivity**: JavaScript for dynamic verse regeneration
- **Text Cleaning**: Regex-based HTML sanitization for Tafsir content

## Working with Claude on This Project

### 1. Understanding the Codebase

When asking Claude to analyze or modify code:

```bash
# Always provide context about which part you're working on
"Can you help me optimize the data loading in scripts/ayah-a-day.py lines 12-26?"

# Be specific about the JSON structure
"The qpc-hafs.json contains verses in format '1:1': {'id': 1, 'verse_key': '1:1', 'surah': 1, 'ayah': 1, 'text': '...'}"
```

### 2. Common Development Tasks

#### Code Refactoring
```bash
# Request modular improvements
"Break down the monolithic ayah-a-day.py into separate modules for data loading, HTML generation, and verse selection"

# Ask for specific patterns
"Convert the HTML template string to use a template engine like Jinja2"
```

#### Performance Optimization
```bash
# Focus on specific bottlenecks
"The generated HTML is 25MB. How can we reduce size while maintaining functionality?"

# Request caching solutions
"Add caching for the unified_data to avoid reprocessing on each run"
```

#### Data Management
```bash
# Be specific about JSON structure
"Add validation for the verse_key format (surah:ayah) in all JSON files"

# Request error handling
"Add comprehensive error handling for missing or corrupted JSON files"
```

### 3. Testing and Validation

#### Unit Testing
```bash
# Request specific test cases
"Create unit tests for the clean_tafsir_html function covering edge cases with nested HTML tags"

# Ask for integration tests
"Write tests that verify the unified_data structure matches expected format for random sampling"
```

#### Data Integrity
```bash
# Request validation scripts
"Create a script to validate that all verse_keys exist across all three JSON datasets"

# Ask for consistency checks
"Check that surah and ayah numbers match between Arabic text and translations"
```

### 4. Feature Development

#### New Functionality
```bash
# Be specific about requirements
"Add a search feature that finds verses by surah number and ayah range (e.g., 2:1-10)"

# Request UI enhancements
"Add a bookmark feature that saves favorite verses to localStorage"
```

#### Configuration
```bash
# Request externalization
"Move hardcoded file paths and styling options to a config.json file"

# Ask for environment handling
"Add support for development vs production configurations"
```

### 5. Deployment and Distribution

#### Packaging
```bash
# Request proper Python packaging
"Create a pyproject.toml with dependencies and build configuration"

# Ask for distribution options
"Convert to a web app using Flask/FastAPI for server-side verse generation"
```

#### Docker/Containerization
```bash
# Request containerization
"Create a Dockerfile that includes Python dependencies and serves the HTML output"
```

## Optimization Strategies

### 1. Performance Improvements
- **Data Caching**: Serialize unified_data to avoid JSON reprocessing
- **Lazy Loading**: Load translations/tafsir only when requested
- **HTML Optimization**: Separate JavaScript data from HTML template

### 2. Code Quality
- **Type Hints**: Add Python type annotations throughout
- **Documentation**: Use docstrings for all functions
- **Linting**: Configure with ruff/black/mypy

### 3. User Experience
- **Progressive Enhancement**: Start with basic HTML, enhance with JavaScript
- **Accessibility**: Add ARIA labels and semantic HTML
- **Internationalization**: Support multiple translation sources

## Common Claude Prompts

### Code Analysis
```bash
"Analyze the regex pattern in clean_tafsir_html() and suggest improvements for better HTML sanitization"

"Review the JavaScript embedded in the HTML template and recommend modern ES6+ improvements"
```

### Architecture Questions
```bash
"Should we split the 25MB JSON data into smaller chunks for better loading performance?"

"What's the best way to handle state management for user preferences (bookmarks, font size, etc.)?"
```

### Implementation Requests
```bash
"Implement a CLI interface using argparse to specify custom data directories and output locations"

"Add support for multiple translation sources with a dropdown selector in the UI"
```

## File-Specific Context

### scripts/ayah-a-day.py
- **Lines 1-26**: Data loading and error handling
- **Lines 27-50**: Unified data structure creation
- **Lines 52-74**: HTML cleaning functions
- **Lines 76-95**: Random verse selection logic
- **Lines 105-206**: HTML template with embedded CSS/JS
- **Lines 208-217**: File output and browser launch

### Data Files Structure
- **verse_key format**: "surah:ayah" (e.g., "1:1", "114:6")
- **Arabic text**: Contains Unicode diacritics and verse numbers
- **Translation**: Plain English text
- **Tafsir**: HTML content requiring sanitization

## Dependencies and Tools

### Current Dependencies
- Python standard library only (json, random, re, os, webbrowser)
- External: Tailwind CSS CDN, Google Fonts

### Recommended Additions
- **Jinja2**: Template engine
- **Click**: CLI interface
- **Pytest**: Testing framework
- **Ruff**: Linting and formatting
- **Rich**: Terminal output formatting

## Best Practices for Claude Collaboration

1. **Be Specific**: Always mention file names, line numbers, and function names
2. **Provide Context**: Explain the Islamic/Quranic context when relevant
3. **Request Explanations**: Ask Claude to explain Arabic text handling or Islamic terminology
4. **Iterate**: Start with small changes and build up to larger refactoring
5. **Test Thoroughly**: Always request test cases for new functionality

This project handles religious text, so accuracy and respect for the content is paramount. Always verify that changes maintain the integrity of the Quranic text and translations.