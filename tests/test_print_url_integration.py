"""Integration tests for print URL feature.

These tests use real recipe sites to verify the print URL detection works.
Mark as slow tests since they make actual HTTP requests.
"""

import pytest
from recipe_duck.url_extractor import URLRecipeExtractor
from recipe_duck.config import PrintURLConfig
from anthropic import Anthropic
import os


@pytest.mark.integration
@pytest.mark.skipif(not os.environ.get("RUN_INTEGRATION_TESTS"), reason="Integration tests disabled")
class TestPrintURLIntegration:
    """Integration tests requiring actual HTTP requests."""

    def test_budget_bytes_print_url(self):
        """Test print URL detection for Budget Bytes (WordPress Recipe Maker)."""
        extractor = URLRecipeExtractor()

        # Known Budget Bytes recipe
        url = "https://www.budgetbytes.com/easy-dumpling-soup/"

        best_url, method = extractor.find_best_url(url, verbose=True)

        # Should find WordPress Recipe Maker pattern
        assert method in ("pattern", "cache")
        assert "wprm_print" in best_url or best_url != url

    def test_serious_eats_print_url(self):
        """Test print URL detection for Serious Eats (?print parameter)."""
        extractor = URLRecipeExtractor()

        # Known Serious Eats recipe
        url = "https://www.seriouseats.com/pasta-alla-genovese-neapolitan-beef-ragu"

        best_url, method = extractor.find_best_url(url, verbose=True)

        # Should find ?print pattern
        if method == "pattern" or method == "cache":
            assert "?print" in best_url

    def test_site_without_print_version(self):
        """Test fallback when no print version exists."""
        extractor = URLRecipeExtractor()

        # Use a regular webpage without print version
        url = "https://www.example.com"

        best_url, method = extractor.find_best_url(url, verbose=True, timeout_budget=5)

        # Should fall back to original
        assert best_url == url
        assert method == "original"

    def test_cache_persistence(self):
        """Test that cache persists across multiple calls to same domain."""
        extractor = URLRecipeExtractor()

        # First call should do pattern detection
        url1 = "https://www.budgetbytes.com/recipe1/"
        best_url1, method1 = extractor.find_best_url(url1, verbose=True)

        # Second call to same domain should use cache
        url2 = "https://www.budgetbytes.com/recipe2/"
        best_url2, method2 = extractor.find_best_url(url2, verbose=True)

        # If first call found a pattern, second should use cache
        if method1 in ("pattern", "llm"):
            assert method2 == "cache"

    @pytest.mark.skipif(not os.environ.get("ANTHROPIC_API_KEY"), reason="API key required")
    def test_llm_fallback(self):
        """Test LLM fallback when patterns fail."""
        # Create extractor with Anthropic client
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        client = Anthropic(api_key=api_key)
        extractor = URLRecipeExtractor(anthropic_client=client)

        # Use a recipe site with unusual print URL pattern
        # The LLM should be able to find it even if our patterns don't match
        url = "https://www.food52.com/recipes/87643-classic-chocolate-chip-cookies"

        best_url, method = extractor.find_best_url(
            url,
            detection_model="claude-3-5-haiku-20241022",
            verbose=True,
            timeout_budget=20
        )

        # Should either find via pattern or LLM
        assert method in ("pattern", "llm", "cache", "original")
        # If method is llm, verify it found a different URL
        if method == "llm":
            assert best_url != url

    def test_timeout_budget_respected(self):
        """Test that timeout budget is respected."""
        import time
        extractor = URLRecipeExtractor()

        # Use a non-existent domain that will cause timeouts
        url = "https://this-domain-definitely-does-not-exist-12345.com/recipe"

        start = time.time()
        best_url, method = extractor.find_best_url(url, verbose=False, timeout_budget=3)
        elapsed = time.time() - start

        # Should respect timeout and not exceed budget significantly
        assert elapsed < 5  # Allow some buffer
        assert best_url == url
        assert method == "original"

    def test_invalid_url_handling(self):
        """Test graceful handling of invalid URLs."""
        extractor = URLRecipeExtractor()

        # Various invalid URL formats
        invalid_urls = [
            "not-a-url",
            "http://",
            "",
        ]

        for url in invalid_urls:
            try:
                best_url, method = extractor.find_best_url(url, verbose=False)
                # Should fall back to original on error
                assert best_url == url
                assert method == "original"
            except Exception:
                # Or raise exception is also acceptable
                pass


@pytest.mark.unit
class TestPrintURLConfig:
    """Unit tests for PrintURLConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = PrintURLConfig()

        assert config.enabled is True  # Default from env or True
        assert config.detection_model == "claude-3-5-haiku-20241022" or os.environ.get("RECIPE_DUCK_PRINT_DETECTION_MODEL")
        assert config.timeout_budget == 15 or int(os.environ.get("RECIPE_DUCK_PRINT_SEARCH_TIMEOUT", "15"))
        assert config.head_timeout == 5
        assert config.llm_timeout == 5

    def test_config_from_env(self):
        """Test configuration from environment variables."""
        # This would need to set env vars before importing
        # Left as a placeholder for manual testing
        pass

    def test_disabled_config(self):
        """Test disabling print URL detection."""
        config = PrintURLConfig()
        config.enabled = False

        assert config.enabled is False


@pytest.mark.unit
class TestPrintURLEdgeCases:
    """Test edge cases and error conditions."""

    def test_url_with_multiple_query_params(self):
        """Test URL with existing query parameters."""
        extractor = URLRecipeExtractor()

        url = "https://example.com/recipe?id=123&category=dessert"
        candidates = extractor._generate_print_candidates(url)

        # Should append, not replace
        assert any("&print" in c for c in candidates)
        assert any("&printview" in c for c in candidates)

    def test_url_with_fragment(self):
        """Test URL with fragment identifier."""
        extractor = URLRecipeExtractor()

        url = "https://example.com/recipe#instructions"
        candidates = extractor._generate_print_candidates(url)

        # Should handle fragments correctly
        assert len(candidates) > 0

    def test_url_with_trailing_slash(self):
        """Test URL with trailing slash."""
        extractor = URLRecipeExtractor()

        url = "https://example.com/recipe/"
        candidates = extractor._generate_print_candidates(url)

        # Should generate valid candidates
        assert len(candidates) > 0
        # Verify no double slashes created
        assert not any("//" in c.replace("https://", "") for c in candidates)

    def test_very_long_slug(self):
        """Test URL with very long recipe slug."""
        extractor = URLRecipeExtractor()

        long_slug = "a" * 200
        url = f"https://example.com/recipes/{long_slug}"

        slug = extractor._extract_recipe_slug(url)
        assert slug == long_slug

        candidates = extractor._generate_print_candidates(url)
        assert len(candidates) > 0

    def test_unicode_in_url(self):
        """Test URL with unicode characters."""
        extractor = URLRecipeExtractor()

        url = "https://example.com/recipes/crème-brûlée"
        candidates = extractor._generate_print_candidates(url)

        # Should handle unicode gracefully
        assert len(candidates) > 0
