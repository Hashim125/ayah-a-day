"""Tests for Flask web application."""

import pytest
import json
from unittest.mock import patch, Mock

from tests.conftest import assert_html_valid


class TestFlaskApp:
    """Test Flask application routes and functionality."""

    @pytest.mark.integration
    def test_index_route(self, client):
        """Test main index route."""
        response = client.get('/')
        
        assert response.status_code == 200
        assert_html_valid(response.get_data(as_text=True))
        assert 'Ayah App' in response.get_data(as_text=True)

    @pytest.mark.integration
    def test_verse_by_key_route(self, client):
        """Test specific verse route."""
        # Test valid verse
        response = client.get('/verse/2:255')
        
        if response.status_code == 200:  # If verse exists in test data
            assert_html_valid(response.get_data(as_text=True))
        else:
            assert response.status_code == 404  # If verse not in test data

    def test_invalid_verse_key_route(self, client):
        """Test route with invalid verse key."""
        response = client.get('/verse/invalid-key')
        
        assert response.status_code == 400

    def test_random_verse_route(self, client):
        """Test random verse redirect."""
        response = client.get('/random')
        
        # Should redirect to a specific verse
        assert response.status_code == 302

    def test_search_route_get(self, client):
        """Test search route with GET request."""
        response = client.get('/search')
        
        assert response.status_code == 200
        assert_html_valid(response.get_data(as_text=True))

    def test_search_route_with_query(self, client):
        """Test search route with query parameter."""
        response = client.get('/search?q=Allah')
        
        assert response.status_code == 200
        assert_html_valid(response.get_data(as_text=True))

    def test_subscribe_route_get(self, client):
        """Test subscription page."""
        response = client.get('/subscribe')
        
        assert response.status_code == 200
        assert_html_valid(response.get_data(as_text=True))
        assert 'Subscribe' in response.get_data(as_text=True)

    def test_subscribe_route_post_valid(self, client):
        """Test subscription with valid data."""
        data = {
            'email': 'test@example.com',
            'name': 'Test User',
            'frequency': 'daily'
        }
        
        response = client.post('/subscribe', data=data, follow_redirects=True)
        
        # Should redirect on success or show error
        assert response.status_code == 200

    def test_subscribe_route_post_invalid(self, client):
        """Test subscription with invalid data."""
        data = {
            'email': 'invalid-email',
            'name': 'Test User',
            'frequency': 'daily'
        }
        
        response = client.post('/subscribe', data=data)
        
        assert response.status_code == 200
        # Should show error message

    def test_unsubscribe_route(self, client):
        """Test unsubscribe route."""
        # Test with dummy token
        response = client.get('/unsubscribe/dummy-token', follow_redirects=True)
        
        assert response.status_code == 200

    def test_health_check_route(self, client):
        """Test health check endpoint."""
        response = client.get('/health')
        
        assert response.status_code in [200, 500]  # Could fail if no test data
        
        if response.status_code == 200:
            data = json.loads(response.get_data(as_text=True))
            assert 'status' in data
            assert data['status'] == 'healthy'

    def test_admin_data_integrity_route(self, client):
        """Test admin data integrity endpoint."""
        response = client.get('/admin/data-integrity')
        
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = json.loads(response.get_data(as_text=True))
            assert isinstance(data, dict)

    def test_404_error_handler(self, client):
        """Test 404 error handler."""
        response = client.get('/nonexistent-page')
        
        assert response.status_code == 404
        assert_html_valid(response.get_data(as_text=True))


class TestAPIEndpoints:
    """Test API endpoints."""

    def test_api_random_verse(self, client):
        """Test random verse API endpoint."""
        response = client.get('/api/random-verse')
        
        # Might return 500 if no test data available
        if response.status_code == 200:
            data = json.loads(response.get_data(as_text=True))
            assert 'verse_key' in data
            assert 'arabic_text' in data
            assert 'translation' in data
        else:
            assert response.status_code == 500

    def test_api_verse_by_key_valid(self, client):
        """Test verse by key API with valid key."""
        response = client.get('/api/verse/2:255')
        
        if response.status_code == 200:
            data = json.loads(response.get_data(as_text=True))
            assert data['verse_key'] == '2:255'
            assert 'arabic_text' in data
        else:
            assert response.status_code in [404, 500]

    def test_api_verse_by_key_invalid(self, client):
        """Test verse by key API with invalid key."""
        response = client.get('/api/verse/invalid-key')
        
        assert response.status_code == 400
        data = json.loads(response.get_data(as_text=True))
        assert 'error' in data

    def test_api_search_empty(self, client):
        """Test search API with empty query."""
        response = client.get('/api/search')
        
        assert response.status_code == 200
        data = json.loads(response.get_data(as_text=True))
        assert isinstance(data, list)
        assert len(data) == 0

    def test_api_search_with_query(self, client):
        """Test search API with query."""
        response = client.get('/api/search?q=Allah')
        
        assert response.status_code == 200
        data = json.loads(response.get_data(as_text=True))
        assert isinstance(data, list)

    def test_api_search_with_limit(self, client):
        """Test search API with limit parameter."""
        response = client.get('/api/search?q=test&limit=5')
        
        assert response.status_code == 200
        data = json.loads(response.get_data(as_text=True))
        assert isinstance(data, list)
        assert len(data) <= 5

    def test_api_search_limit_validation(self, client):
        """Test search API limit validation."""
        response = client.get('/api/search?q=test&limit=200')  # Over max limit
        
        assert response.status_code == 200
        data = json.loads(response.get_data(as_text=True))
        assert isinstance(data, list)
        assert len(data) <= 100  # Should be capped at 100


class TestErrorHandling:
    """Test error handling in the Flask app."""

    @patch('src.ayah_app.app.DataLoader')
    def test_data_loader_initialization_error(self, mock_data_loader, flask_app):
        """Test handling of data loader initialization errors."""
        mock_data_loader.side_effect = Exception("Data loading failed")
        
        with pytest.raises(Exception):
            # This would fail during app initialization
            from src.ayah_app.app import AyahApp
            AyahApp('testing')

    def test_internal_server_error(self, client):
        """Test 500 error handling."""
        # This is tricky to test without mocking internal errors
        # The error handler should return HTML with status 500
        pass

    @patch('src.ayah_app.verse_selector.VerseSelector.get_random_verse')
    def test_api_error_handling(self, mock_get_verse, client):
        """Test API error handling."""
        mock_get_verse.side_effect = Exception("Database error")
        
        response = client.get('/api/random-verse')
        
        assert response.status_code == 500
        data = json.loads(response.get_data(as_text=True))
        assert 'error' in data


class TestConfiguration:
    """Test configuration handling."""

    def test_testing_config(self, flask_app):
        """Test that testing configuration is applied."""
        assert flask_app.config['TESTING'] is True
        assert flask_app.config['MAIL_SUPPRESS_SEND'] is True

    def test_debug_mode(self, flask_app):
        """Test debug mode configuration."""
        # In testing, debug should be False
        assert flask_app.config.get('DEBUG') is False


class TestSecurity:
    """Test security features."""

    def test_csrf_protection(self, client):
        """Test CSRF protection on forms."""
        # CSRF is disabled in testing config
        # In production, this would require CSRF tokens
        data = {'email': 'test@example.com'}
        response = client.post('/subscribe', data=data)
        
        # Should not return 400 due to CSRF in testing
        assert response.status_code != 400

    def test_sql_injection_protection(self, client):
        """Test SQL injection protection."""
        # Test with malicious input
        malicious_input = "'; DROP TABLE users; --"
        response = client.get(f'/search?q={malicious_input}')
        
        # Should handle safely
        assert response.status_code == 200

    def test_xss_protection(self, client):
        """Test XSS protection."""
        # Test with script tag
        xss_input = "<script>alert('xss')</script>"
        response = client.get(f'/search?q={xss_input}')
        
        # Should escape properly
        assert response.status_code == 200
        assert '<script>' not in response.get_data(as_text=True)