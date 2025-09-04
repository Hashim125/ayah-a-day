"""Command line interface for Ayah App."""

import click
import sys
from pathlib import Path

from config.settings import get_config
from .app import AyahApp
from .data_loader import DataLoader


@click.group()
def main():
    """Ayah App CLI - Daily Quran verses with translations and commentary."""
    pass


@main.command()
@click.option('--host', default='127.0.0.1', help='Host to run the server on')
@click.option('--port', default=5000, help='Port to run the server on')
@click.option('--debug', is_flag=True, help='Run in debug mode')
@click.option('--config', default=None, help='Configuration name (development, production, testing)')
def run(host, port, debug, config):
    """Run the Ayah App web server."""
    try:
        app = AyahApp(config)
        app.run(host=host, port=port, debug=debug)
    except Exception as e:
        click.echo(f"Error starting application: {e}", err=True)
        sys.exit(1)


@main.command()
@click.option('--config', default=None, help='Configuration name')
def validate_data(config):
    """Validate data integrity."""
    try:
        config_obj = get_config(config)
        data_loader = DataLoader(config_obj)
        
        click.echo("Validating data integrity...")
        integrity_info = data_loader.validate_data_integrity()
        
        if 'error' in integrity_info:
            click.echo(f"❌ Validation failed: {integrity_info['error']}", err=True)
            sys.exit(1)
        
        click.echo("✅ Data validation results:")
        click.echo(f"  Total verses: {integrity_info['total_verses']}")
        click.echo(f"  Invalid keys: {len(integrity_info['invalid_keys'])}")
        click.echo(f"  Empty translations: {len(integrity_info['empty_translations'])}")
        click.echo(f"  Empty tafsir: {len(integrity_info['empty_tafsir'])}")
        click.echo(f"  Cache valid: {integrity_info['cache_valid']}")
        
        if integrity_info['invalid_keys']:
            click.echo("❌ Invalid verse keys found:", err=True)
            for key in integrity_info['invalid_keys']:
                click.echo(f"    {key}", err=True)
        
        if integrity_info['empty_translations'] or integrity_info['empty_tafsir']:
            click.echo("⚠️ Some verses have missing content")
        else:
            click.echo("✅ All content validation passed")
            
    except Exception as e:
        click.echo(f"Error during validation: {e}", err=True)
        sys.exit(1)


@main.command()
@click.option('--config', default=None, help='Configuration name')
@click.option('--force', is_flag=True, help='Force reload data from source files')
def load_data(config, force):
    """Load and cache data."""
    try:
        config_obj = get_config(config)
        data_loader = DataLoader(config_obj)
        
        click.echo("Loading data...")
        data = data_loader.load_data(force_reload=force)
        
        click.echo(f"✅ Successfully loaded {len(data)} verses")
        
        # Display some statistics
        surahs = set(v.surah for v in data.values())
        click.echo(f"📖 Covers {len(surahs)} surahs")
        
    except Exception as e:
        click.echo(f"Error loading data: {e}", err=True)
        sys.exit(1)


@main.command()
@click.option('--config', default=None, help='Configuration name')
def clear_cache(config):
    """Clear application cache."""
    try:
        config_obj = get_config(config)
        
        # Remove cache files
        if config_obj.UNIFIED_DATA_CACHE_FILE.exists():
            config_obj.UNIFIED_DATA_CACHE_FILE.unlink()
            click.echo("✅ Cache cleared successfully")
        else:
            click.echo("ℹ️ No cache found to clear")
            
    except Exception as e:
        click.echo(f"Error clearing cache: {e}", err=True)
        sys.exit(1)


@main.command()
@click.option('--config', default=None, help='Configuration name')
@click.argument('verse_key')
def show_verse(config, verse_key):
    """Display a specific verse."""
    try:
        config_obj = get_config(config)
        data_loader = DataLoader(config_obj)
        
        data = data_loader.load_data()
        
        if verse_key not in data:
            click.echo(f"❌ Verse {verse_key} not found", err=True)
            sys.exit(1)
        
        verse = data[verse_key]
        
        click.echo(f"\n🕊️ Verse {verse.verse_key}")
        click.echo("─" * 60)
        click.echo(f"📖 Surah {verse.surah}, Ayah {verse.ayah}")
        click.echo()
        click.echo("Arabic:")
        click.echo(verse.arabic_text)
        click.echo()
        click.echo("Translation:")
        click.echo(verse.translation)
        click.echo()
        if verse.tafsir:
            click.echo("Tafsir (excerpt):")
            # Show first 200 characters of tafsir
            tafsir_excerpt = verse.tafsir[:200] + "..." if len(verse.tafsir) > 200 else verse.tafsir
            # Remove HTML tags for CLI display
            import re
            tafsir_text = re.sub(r'<[^>]+>', '', tafsir_excerpt)
            click.echo(tafsir_text)
        click.echo()
        
    except Exception as e:
        click.echo(f"Error displaying verse: {e}", err=True)
        sys.exit(1)


@main.command()
@click.option('--config', default=None, help='Configuration name')
@click.argument('query')
@click.option('--limit', default=5, help='Maximum number of results')
def search(config, query, limit):
    """Search for verses containing the query text."""
    try:
        config_obj = get_config(config)
        data_loader = DataLoader(config_obj)
        
        from .verse_selector import VerseSelector
        verse_selector = VerseSelector(data_loader)
        
        click.echo(f"🔍 Searching for: '{query}'")
        results = verse_selector.search_verses(query, limit=limit)
        
        if not results:
            click.echo("❌ No verses found matching your query")
            sys.exit(1)
        
        click.echo(f"✅ Found {len(results)} result(s):")
        click.echo()
        
        for i, result in enumerate(results, 1):
            verse = result.verse_data
            click.echo(f"{i}. Verse {verse.verse_key} (Score: {result.relevance_score:.2f})")
            click.echo(f"   Translation: {verse.translation[:100]}...")
            click.echo()
            
    except Exception as e:
        click.echo(f"Error during search: {e}", err=True)
        sys.exit(1)


@main.command()
def version():
    """Show version information."""
    try:
        from . import __version__
        click.echo(f"Ayah App version {__version__}")
    except ImportError:
        click.echo("Ayah App (version unknown)")


if __name__ == '__main__':
    main()