"""Unit tests for URL extractor functionality."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from recipe_duck.url_extractor import URLRecipeExtractor


class TestURLRecipeExtractor:
    """Tests for URLRecipeExtractor class."""

    def test_get_domain(self):
        """Test domain extraction from URLs."""
        extractor = URLRecipeExtractor()

        assert extractor._get_domain("https://www.example.com/recipe/cookies") == "www.example.com"
        assert extractor._get_domain("http://budgetbytes.com/recipes/banana-bread/") == "budgetbytes.com"
        assert extractor._get_domain("https://seriouseats.com/pasta?id=123") == "seriouseats.com"

    def test_extract_recipe_slug(self):
        """Test recipe slug extraction from various URL formats."""
        extractor = URLRecipeExtractor()

        # WordPress-style URLs
        assert extractor._extract_recipe_slug(
            "https://example.com/recipes/chocolate-chip-cookies/"
        ) == "chocolate-chip-cookies"

        # Date-based URLs
        assert extractor._extract_recipe_slug(
            "https://example.com/2024/01/my-recipe/"
        ) == "my-recipe"

        # With trailing extension
        assert extractor._extract_recipe_slug(
            "https://example.com/recipes/pasta.html"
        ) == "pasta"

        # Numeric IDs should be skipped
        assert extractor._extract_recipe_slug(
            "https://example.com/recipes/12345/chocolate-cake"
        ) == "chocolate-cake"

        # Short slugs should be skipped (< 3 chars)
        assert extractor._extract_recipe_slug(
            "https://example.com/r/ab/actual-recipe-name"
        ) == "actual-recipe-name"

    def test_generate_print_candidates(self):
        """Test print URL candidate generation."""
        extractor = URLRecipeExtractor()

        # Test with simple URL
        candidates = extractor._generate_print_candidates("https://example.com/recipes/cookies")
        assert "https://example.com/recipes/cookies?print" in candidates
        assert "https://example.com/recipes/cookies?printview" in candidates
        assert "https://example.com/wprm_print/cookies" in candidates
        assert "https://example.com/recipes/cookies/print/" in candidates
        assert "https://example.com/recipes/cookies/print" in candidates

        # Test with URL that already has query params
        candidates = extractor._generate_print_candidates("https://example.com/recipe?id=123")
        assert "https://example.com/recipe?id=123&print" in candidates
        assert "https://example.com/recipe?id=123&printview" in candidates

    def test_identify_pattern(self):
        """Test pattern identification from successful URLs."""
        extractor = URLRecipeExtractor()

        assert extractor._identify_pattern(
            "https://example.com/recipe?print",
            "https://example.com/recipe"
        ) == "query_print"

        assert extractor._identify_pattern(
            "https://example.com/recipe?printview",
            "https://example.com/recipe"
        ) == "query_printview"

        assert extractor._identify_pattern(
            "https://example.com/wprm_print/cookies",
            "https://example.com/recipes/cookies"
        ) == "wprm_print"

        assert extractor._identify_pattern(
            "https://example.com/recipe/print/",
            "https://example.com/recipe"
        ) == "suffix_print_slash"

        assert extractor._identify_pattern(
            "https://example.com/recipe/print",
            "https://example.com/recipe"
        ) == "suffix_print"

    def test_apply_pattern(self):
        """Test applying cached patterns to URLs."""
        extractor = URLRecipeExtractor()

        url = "https://example.com/recipes/pasta"

        # Test query_print pattern
        result = extractor._apply_pattern(url, "query_print")
        assert result == "https://example.com/recipes/pasta?print"

        # Test query_printview pattern
        result = extractor._apply_pattern(url, "query_printview")
        assert result == "https://example.com/recipes/pasta?printview"

        # Test wprm_print pattern
        result = extractor._apply_pattern(url, "wprm_print")
        assert result == "https://example.com/wprm_print/pasta"

        # Test suffix patterns
        result = extractor._apply_pattern(url, "suffix_print_slash")
        assert result == "https://example.com/recipes/pasta/print/"

        result = extractor._apply_pattern(url, "suffix_print")
        assert result == "https://example.com/recipes/pasta/print"

        # Test with URL that has query params
        url_with_query = "https://example.com/recipe?id=123"
        result = extractor._apply_pattern(url_with_query, "query_print")
        assert result == "https://example.com/recipe?id=123&print"

    @patch('recipe_duck.url_extractor.requests.head')
    def test_validate_print_url_success(self, mock_head):
        """Test successful URL validation."""
        extractor = URLRecipeExtractor()

        # Mock successful response with content-length header
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-length": "50000"}
        mock_head.return_value = mock_response

        is_valid, content_len = extractor._validate_print_url("https://example.com/print")

        assert is_valid is True
        assert content_len == 50000
        mock_head.assert_called_once()

    @patch('recipe_duck.url_extractor.requests.get')
    @patch('recipe_duck.url_extractor.requests.head')
    def test_validate_print_url_no_content_length(self, mock_head, mock_get):
        """Test URL validation when content-length header is missing."""
        extractor = URLRecipeExtractor()

        # Mock HEAD response without content-length
        mock_head_response = Mock()
        mock_head_response.status_code = 200
        mock_head_response.headers = {}
        mock_head.return_value = mock_head_response

        # Mock GET response with content
        mock_get_response = Mock()
        mock_get_response.content = b"x" * 10000  # 10KB of content
        mock_get.return_value = mock_get_response

        is_valid, content_len = extractor._validate_print_url("https://example.com/print")

        assert is_valid is True
        assert content_len == 10000
        mock_head.assert_called_once()
        mock_get.assert_called_once()

    @patch('recipe_duck.url_extractor.requests.head')
    def test_validate_print_url_too_small(self, mock_head):
        """Test URL validation with content too small."""
        extractor = URLRecipeExtractor()

        # Mock response with content too small
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-length": "500"}  # Only 500 bytes
        mock_head.return_value = mock_response

        is_valid, content_len = extractor._validate_print_url("https://example.com/print")

        assert is_valid is False
        assert content_len == 0

    @patch('recipe_duck.url_extractor.requests.head')
    def test_validate_print_url_404(self, mock_head):
        """Test URL validation with 404 response."""
        extractor = URLRecipeExtractor()

        # Mock 404 response
        mock_response = Mock()
        mock_response.status_code = 404
        mock_head.return_value = mock_response

        is_valid, content_len = extractor._validate_print_url("https://example.com/print")

        assert is_valid is False
        assert content_len == 0

    @patch('recipe_duck.url_extractor.time.sleep')
    @patch('recipe_duck.url_extractor.requests.head')
    def test_validate_print_url_retry_on_timeout(self, mock_head, mock_sleep):
        """Test retry logic on timeout."""
        extractor = URLRecipeExtractor()

        # Mock timeout on first attempt, success on second
        import requests
        mock_head.side_effect = [
            requests.Timeout("Connection timeout"),
            Mock(status_code=200, headers={"content-length": "50000"})
        ]

        is_valid, content_len = extractor._validate_print_url("https://example.com/print", retry=True)

        assert is_valid is True
        assert content_len == 50000
        assert mock_head.call_count == 2
        mock_sleep.assert_called_once_with(1)  # Should sleep before retry

    @patch('recipe_duck.url_extractor.time.sleep')
    @patch('recipe_duck.url_extractor.requests.head')
    def test_validate_print_url_retry_on_rate_limit(self, mock_head, mock_sleep):
        """Test retry logic on rate limiting."""
        extractor = URLRecipeExtractor()

        # Mock 429 on first attempt, success on second
        mock_head.side_effect = [
            Mock(status_code=429),
            Mock(status_code=200, headers={"content-length": "50000"})
        ]

        is_valid, content_len = extractor._validate_print_url("https://example.com/print", retry=True)

        assert is_valid is True
        assert content_len == 50000
        assert mock_head.call_count == 2
        mock_sleep.assert_called_once_with(1)  # Exponential backoff: 2^0 = 1

    def test_cache_functionality(self):
        """Test that cache stores and retrieves patterns correctly."""
        extractor = URLRecipeExtractor()

        # Initially empty
        assert len(extractor._print_url_cache) == 0

        # Add to cache
        extractor._print_url_cache["example.com"] = "query_print"

        # Verify it's stored
        assert "example.com" in extractor._print_url_cache
        assert extractor._print_url_cache["example.com"] == "query_print"

    @patch('recipe_duck.url_extractor.URLRecipeExtractor._validate_print_url')
    @patch('recipe_duck.url_extractor.URLRecipeExtractor._generate_print_candidates')
    def test_find_best_url_pattern_success(self, mock_candidates, mock_validate):
        """Test find_best_url with successful pattern match."""
        extractor = URLRecipeExtractor()

        # Mock candidate generation
        mock_candidates.return_value = [
            "https://example.com/recipe?print",
            "https://example.com/recipe?printview",
        ]

        # Mock validation - first fails, second succeeds
        mock_validate.side_effect = [(False, 0), (True, 50000)]

        best_url, method = extractor.find_best_url("https://example.com/recipe", verbose=False)

        assert best_url == "https://example.com/recipe?printview"
        assert method == "pattern"
        # Verify pattern was cached
        assert "example.com" in extractor._print_url_cache

    @patch('recipe_duck.url_extractor.URLRecipeExtractor._validate_print_url')
    @patch('recipe_duck.url_extractor.URLRecipeExtractor._generate_print_candidates')
    def test_find_best_url_no_pattern_found(self, mock_candidates, mock_validate):
        """Test find_best_url when no patterns work."""
        extractor = URLRecipeExtractor()

        # Mock candidate generation
        mock_candidates.return_value = [
            "https://example.com/recipe?print",
            "https://example.com/recipe?printview",
        ]

        # Mock validation - all fail
        mock_validate.return_value = (False, 0)

        best_url, method = extractor.find_best_url("https://example.com/recipe", verbose=False)

        assert best_url == "https://example.com/recipe"
        assert method == "original"

    @patch('recipe_duck.url_extractor.URLRecipeExtractor._apply_pattern')
    @patch('recipe_duck.url_extractor.URLRecipeExtractor._validate_print_url')
    def test_find_best_url_cache_hit(self, mock_validate, mock_apply):
        """Test find_best_url with cache hit."""
        extractor = URLRecipeExtractor()

        # Pre-populate cache
        extractor._print_url_cache["example.com"] = "query_print"

        # Mock pattern application
        mock_apply.return_value = "https://example.com/recipe?print"

        # Mock validation - succeeds
        mock_validate.return_value = (True, 50000)

        best_url, method = extractor.find_best_url("https://example.com/recipe", verbose=False)

        assert best_url == "https://example.com/recipe?print"
        assert method == "cache"
        mock_apply.assert_called_once_with("https://example.com/recipe", "query_print")
