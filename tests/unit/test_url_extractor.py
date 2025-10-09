"""Unit tests for URL recipe extractor."""

import pytest
from unittest.mock import Mock, patch

from recipe_duck.url_extractor import URLRecipeExtractor


@pytest.fixture
def extractor():
    """Create a URLRecipeExtractor instance."""
    return URLRecipeExtractor()


@pytest.fixture
def sample_html_with_recipe():
    """Sample HTML with recipe content."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Recipe Page</title>
        <script>console.log('test')</script>
        <style>.test { color: red; }</style>
    </head>
    <body>
        <nav>Navigation Menu</nav>
        <header>Site Header</header>
        <main>
            <h1>Chocolate Chip Cookies</h1>
            <p>A delicious recipe for classic cookies</p>
            <h2>Ingredients</h2>
            <ul>
                <li>2 1/4 cups all-purpose flour</li>
                <li>1 tsp baking soda</li>
                <li>1 cup butter, softened</li>
                <li>3/4 cup sugar</li>
            </ul>
            <h2>Instructions</h2>
            <ol>
                <li>Preheat oven to 375°F</li>
                <li>Mix flour and baking soda</li>
                <li>Beat butter and sugars</li>
            </ol>
        </main>
        <footer>Site Footer</footer>
        <aside>Sidebar Content</aside>
    </body>
    </html>
    """


def test_extract_content_basic(extractor, sample_html_with_recipe):
    """Test basic content extraction from HTML."""
    content = extractor.extract_content(sample_html_with_recipe)

    # Recipe content should be present
    assert "Chocolate Chip Cookies" in content
    assert "2 1/4 cups all-purpose flour" in content
    assert "Preheat oven to 375°F" in content

    # Unwanted elements should be removed
    assert "console.log" not in content
    assert ".test { color: red; }" not in content
    assert "Navigation Menu" not in content
    assert "Site Header" not in content
    assert "Site Footer" not in content
    assert "Sidebar Content" not in content


def test_extract_content_removes_scripts_and_styles(extractor):
    """Test that scripts and styles are removed."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <script>alert('test')</script>
        <style>.test { color: red; }</style>
    </head>
    <body>
        <main>
            <h1>Recipe Title</h1>
            <p>Recipe content here</p>
        </main>
    </body>
    </html>
    """
    content = extractor.extract_content(html)

    assert "Recipe Title" in content
    assert "Recipe content" in content
    assert "alert('test')" not in content
    assert ".test { color: red; }" not in content


def test_extract_content_prefers_main_tag(extractor):
    """Test that main content is preferred over other tags."""
    html = """
    <!DOCTYPE html>
    <html>
    <body>
        <div>Unwanted content outside main</div>
        <main>
            <h1>Main Recipe Content</h1>
            <p>This should be extracted</p>
        </main>
        <div>More unwanted content</div>
    </body>
    </html>
    """
    content = extractor.extract_content(html)

    assert "Main Recipe Content" in content
    assert "This should be extracted" in content


def test_extract_content_fallback_to_article(extractor):
    """Test fallback to article tag when main is not present."""
    html = """
    <!DOCTYPE html>
    <html>
    <body>
        <div>Unwanted content</div>
        <article>
            <h1>Article Recipe Content</h1>
            <p>This should be extracted</p>
        </article>
    </body>
    </html>
    """
    content = extractor.extract_content(html)

    assert "Article Recipe Content" in content
    assert "This should be extracted" in content


def test_extract_content_fallback_to_body(extractor):
    """Test fallback to body tag when main/article not present."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <h1>Body Recipe Content</h1>
        <p>This should be extracted</p>
    </body>
    </html>
    """
    content = extractor.extract_content(html)

    assert "Body Recipe Content" in content
    assert "This should be extracted" in content


@patch("recipe_duck.url_extractor.requests.get")
def test_fetch_page_success(mock_get, extractor):
    """Test successful page fetching."""
    mock_response = Mock()
    mock_response.text = "<html>Test</html>"
    mock_response.status_code = 200
    mock_get.return_value = mock_response

    html = extractor.fetch_page("https://example.com/recipe")

    assert html == "<html>Test</html>"
    mock_get.assert_called_once()


@patch("recipe_duck.url_extractor.requests.get")
def test_fetch_page_timeout(mock_get, extractor):
    """Test handling of timeout errors."""
    import requests

    mock_get.side_effect = requests.Timeout()

    with pytest.raises(Exception, match="took too long to respond"):
        extractor.fetch_page("https://example.com/recipe")


@patch("recipe_duck.url_extractor.requests.get")
def test_fetch_page_http_error(mock_get, extractor):
    """Test handling of HTTP errors."""
    import requests

    mock_response = Mock()
    mock_response.status_code = 404
    mock_response.raise_for_status.side_effect = requests.HTTPError(response=mock_response)
    mock_get.return_value = mock_response

    with pytest.raises(Exception, match="Website returned error: 404"):
        extractor.fetch_page("https://example.com/recipe")


@patch("recipe_duck.url_extractor.requests.get")
def test_fetch_page_connection_error(mock_get, extractor):
    """Test handling of connection errors."""
    import requests

    mock_get.side_effect = requests.ConnectionError("Connection failed")

    with pytest.raises(Exception, match="Failed to fetch URL"):
        extractor.fetch_page("https://example.com/recipe")
